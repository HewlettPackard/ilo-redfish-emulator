# BSD 3-Clause License
#
# Copyright 2023 Hewlett Packard Enterprise Development LP
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its
# contributors may be used to endorse or promote products derived from this
# software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import logging
import os

from hvac import Client
from hvac.api.auth_methods import Kubernetes
from hvac.exceptions import InvalidPath

class VaultAdapter:
    def __init__(self, vault_client: Client, base_path: str, default_password_source: str):
        self.vault_client = vault_client
        self.base_path = base_path
        self.default_password_source = default_password_source

    def retrieve_credentials(self, xname: str):
        # Search for BMC specific creds
        bmc_specific_key_path = os.path.join(self.base_path, "hms-creds", xname)
        try:
            result = self.vault_client.secrets.kv.v1.read_secret(bmc_specific_key_path)
            logging.info(f'Using BMC Specific creds at {bmc_specific_key_path}')

            return result["data"]["Username"], result["data"]["Password"]
        except InvalidPath as e:
            logging.warning(f"Vault does not contain a BMC specific credentials at {bmc_specific_key_path}")

        # Fall back to either River or Mountain default creds
        if self.default_password_source == "Mountain":
            default_mountain_creds = os.path.join(self.base_path, "meds-cred", "global", "ipmi")
            try:
                result = self.vault_client.secrets.kv.v1.read_secret(default_mountain_creds)
                logging.info(f'Using Mountain Default Creds at {default_mountain_creds}')

                return result["data"]["Username"], result["data"]["Password"]
            except InvalidPath as e:
                logging.warning(f"Vault does not default creds for mountain hardware at {default_mountain_creds}")

        elif self.default_password_source == "River":
            default_river_creds = os.path.join(self.base_path, "reds-creds", "global", "defaults")
            try:
                result = self.vault_client.secrets.kv.v1.read_secret(default_river_creds)
                logging.info(f'Using River Default Creds at {default_river_creds}')

                if "Cray" not in result["data"]:
                    raise RuntimeError("Default river credentials missing 'Cray' key")

                return result["data"]["Cray"]["Username"], result["data"]["Cray"]["Password"]

            except InvalidPath as e:
                logging.warning(f"Vault does not default creds for river hardware at {default_river_creds}")
        else:
            raise RuntimeError(f"Invalid default password source provided: {self.default_password_source}")


def create_adapter() -> VaultAdapter:
    if "VAULT_ADDR" not in os.environ:
        raise RuntimeError(f"unable to create vault client environment variable VAULT_ADDR not set")
    if "VAULT_BASE_KEYPATH" not in os.environ:
        raise RuntimeError(f"unable to create vault client environment variable VAULT_BASE_KEYPATH not set")
    if "VAULT_DEFAULT_PASSWORD_SOURCE" not in os.environ:
        raise RuntimeError(f"unable to create vault client environment variable VAULT_DEFAULT_PASSWORD_SOURCE not set")

    client = Client(url=os.environ["VAULT_ADDR"])
    auth_type = os.getenv("VAULT_AUTH_TYPE", '')
    default_password_source = os.getenv("VAULT_DEFAULT_PASSWORD_SOURCE", '')
    if auth_type == "token":
        if "VAULT_TOKEN" not in os.environ:
            raise RuntimeError(f"unable to create vault client environment variable VAULT_TOKEN not set")

        client.token = os.environ["VAULT_TOKEN"]
    elif auth_type == "kubernetes":
        jwt = None
        with open('/var/run/secrets/kubernetes.io/serviceaccount/token', 'r') as file:
            jwt = file.read()

        role = None
        with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as file:
            role = file.read()

        Kubernetes(client.adapter).login(
            jwt=jwt,
            role=role
        )
    else:
        raise RuntimeError(f"invalid vault auth_type provided: {auth_type}")

    return VaultAdapter(client, os.environ["VAULT_BASE_KEYPATH"], default_password_source)
