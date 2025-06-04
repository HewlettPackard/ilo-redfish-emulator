#! /usr/bin/env python3

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

import argparse
import requests
import http
import json
import sys


def upsert_sls_hardware(sls_url: str, hardware: dict):
    if 'Xname' not in hardware:
        print(f'Error hardware object is missing its Xname: {hardware}')
        return False
    xname = hardware["Xname"]
    url = f'{sls_url}/hardware/{xname}'

    print(f'Performing PUT {url} with: {json.dumps(hardware)}')
    r = requests.put(url, json=hardware)

    # 200 Ok is returned when the objet is updated
    # 201 Created is returned when the object is created
    if r.status_code not in (http.HTTPStatus.OK, http.HTTPStatus.CREATED):
        print(f'Error failed to create {hardware["Xname"]}, unexpected status code {r.status_code}')
        return False

    return True


if __name__ == "__main__":
    # Parse arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("metadata", help="Metadata file to load SLS with")
    parser.add_argument("--url-sls", type=str, required=False, default="http://cray-sls/v1")

    args = parser.parse_args()

    # Load metadata file containing the SLS hardware objects for the emulated hardware
    print(f"Loading metadata from {args.metadata}")
    metadata = None
    with open(args.metadata, 'r') as f:
        metadata = json.load(f)

    # Push the SLS hardware objects into SLS for the emulated hardware
    error_encountered = False
    for hardware in metadata["Hardware"]:
        if not upsert_sls_hardware(args.url_sls, hardware):
            error_encountered = True

    if error_encountered:
        print("There was an error encountered creating or updating a SLS hardware object")
        sys.exit(1)
    else:
        print("Successfully updated SLS with RIE emulated hardware")

