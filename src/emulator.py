#!/usr/bin/env python2
#
# Copyright Notice:
# Copyright 2016-2021 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Interface-Emulator/blob/master/LICENSE.md
#
# The original DMTF contents of this file have been modified to support
# The CSM Redfish Interface Emulator. These modifications are subject to the following:
# Copyright 2022 Hewlett Packard Enterprise Development LP
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

# Redfish Interface Emulator - main
#   python emulator.py

import os
import json
import argparse
import traceback
import xml.etree.ElementTree as ET
import logging
import copy

from OpenSSL import crypto, SSL
from socket import gethostname

logging.basicConfig(level=logging.DEBUG)

import g

# Flask Imports
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

# Emulator Imports
from api_emulator.version import __version__
from api_emulator.resource_manager import ResourceManager
from api_emulator.redfish.response import simple_error_response
from api_emulator.redfish.redfish_auth import auth, User, ADMIN_USER
from api_emulator import vault_adapter

SPEC = 'Redfish'
MODE = 'Local'
CONFIG = 'emulator-config.json'
CONFIG_DATA = {}

# Base URL of the RESTful interface
REST_BASE = '/redfish/v1/'
g.rest_base = REST_BASE

# Creating the ResourceManager
resource_manager = None

# Parse REST request for Action
parser = reqparse.RequestParser()
parser.add_argument('Action', type=str, required=True)

CERT_FILE = "server.crt"
KEY_FILE = "server.key"

def generate_certs():

    # create a key pair
    k = crypto.PKey()
    k.generate_key(crypto.TYPE_RSA, 2048)

    # create a self-signed cert
    cert = crypto.X509()
    cert.get_subject().C = "US"
    cert.get_subject().O = "Hewlett Packard Enterprise Development LP"
    cert.get_subject().CN = gethostname()
    cert.set_serial_number(1000)
    cert.gmtime_adj_notBefore(0)
    cert.gmtime_adj_notAfter(10*365*24*60*60)
    cert.set_issuer(cert.get_subject())
    cert.set_pubkey(k)
    cert.sign(k, 'sha1')

    with open(CERT_FILE, "wt") as f:
        f.write(crypto.dump_certificate(crypto.FILETYPE_PEM, cert).decode("utf-8"))
    with open(KEY_FILE, "wt") as f:
        f.write(crypto.dump_privatekey(crypto.FILETYPE_PEM, k).decode("utf-8"))

# Execution starts a main(), at end of file

def init_resource_manager():
    """
    Initializes the resource manager
    """
    global resource_manager
    global REST_BASE
    global SPEC

    resource_manager = ResourceManager(REST_BASE, SPEC, MODE, CONFIG_DATA)

class PathError(Exception):
    pass

@g.api.representation('application/json')
def output_json(data, code, headers=None):
    """
    Overriding how JSON is returned by the server so that it looks nice
    """
    resp = make_response(json.dumps(data, indent=4), code)
    resp.headers.extend(headers or {})
    return resp

#
# If DELETE /redfish/v1/reset, then reset the resource manager
#
# TODO: Get this working to reload resources. Doesn't work right
#       now because of the way routes are added.
# @g.app.route('/redfish/v1/reset/', methods=['DELETE'])
# def reset():
    # try:
        # init_resource_manager(True)
        # data = {'Message': 'Emulator reset successfully'}
        # resp = json.dumps(data, indent=4), 200
    # except Exception:
        # traceback.print_exc()
        # resp = simple_error_response('Internal Server Error', 500)
    # return resp

#
#
def startup():

    init_resource_manager()

#
# Main method
#
# Determines execution configuration by reading the configuration file and interogating the command line options
#   TRAYS = Specifies the directory from which the resource pools are created. (Unused)
#   MODE =  Specifies whether the emulator is running locally as a standalone or remotely on a Cloud Foundry instance.
#   HTTPS = Specifies whether the emulator supports "http" or "https"
#   SPEC =  The emulator may support multiple specifications or revisions of a specification.
#           This flag specifies the specification/version to which to conform
#   MOCKUPFOLDERS = This parameter will supercede SPEC.  Specifies a list of
#           folder which contain mockup files in ./static.  For example, if the
#           list contains ["Redfish", "Swordfish"], the files in
#           ./Redfish/static and ./Swordfish/static will be used.  This
#           parameter allows multiple mockup folders to co-exist, and the user
#           can set this parameter to determine which mockups are actually
#           loaded into the emulator.
#   ASYNC_SLEEP = This parameter specifies the amount of time in seconds to sleep between.
#
# Passes control to startup()
#
def main():
    global MODE
    global SPEC

    mockupfolder = os.getenv('MOCKUPFOLDER', 'public-rackmount1')
    g.async_sleep = float(os.getenv('ASYNC_SLEEP', 0))

    HTTPS = os.getenv('HTTPS', 'Enable')
    assert HTTPS.lower() in ['enable', 'disable'], 'Unknown HTTPS setting:' + HTTPS

    MODE = os.getenv('MODE', MODE)
    assert MODE.lower() in ['local', 'cloud'], 'Unknown mode: ' + MODE

    port = int(os.getenv('PORT', 5000))

    CONFIG_DATA['xname'] = os.getenv('XNAME')
    CONFIG_DATA['mac_schema'] = os.getenv('MAC_SCHEMA')

    auth_config = os.getenv('AUTH_CONFIG', '')
    if auth_config == "from_vault":
        vault_client = vault_adapter.create_adapter()
        username, password = vault_client.retrieve_credentials(CONFIG_DATA['xname'])

        auth.set_users({
            username: User(username, password, ADMIN_USER.role, ADMIN_USER.privileges)
        })
    else:
        try:
            # Setup initial set of authorization accounts. The format is <username>:<password>:<role>.
            # The default accounts are defined in ./api_emulator/redfish/redfish_auth.py and are the
            # equivalent to specifying:
            #   'root:root_password:Administrator;operator:operator_password:Operator;guest:guest_password:ReadOnly'
            logging.info('AUTH_CONFIG=%s' % auth_config)
            if len(auth_config) > 0:
                auth.set_auth_from_env(auth_config)
                logging.debug('Using accounts from env')
        except:
            traceback.print_exc()
            logging.debug('Using default accounts')

    argparser = argparse.ArgumentParser(description='CSM Redfish Interface Emulator - Version: ' + __version__)

    argparser.add_argument('-port', type=int, default=port, help='Port to run the emulator on. Port defined by the PORT environment variable (5000 if unset)')
    if(MODE=='Local'):
        print (' * Redfish endpoint at localhost:{}'.format(port))

    argparser.add_argument('-mockupfolder', type=str, default=mockupfolder, help='Mockup directory to use for the emulators static resources')

    argparser.add_argument('-debug', action='store_true', default=False,
                           help='Run the emulator in debug mode. Note that if you'
                                ' run in debug mode, then the emulator will only'
                                'be ran locally.')
    args = argparser.parse_args()

    logging.info('Mockup folder: %s', args.mockupfolder)
    logging.info('ASYNC_SLEEP: %ss', g.async_sleep)
    g.staticfolder = copy.copy(args.mockupfolder)
    print (g.staticfolder)
    startup()
    if (HTTPS == 'Enable'):
        print (' * Use HTTPS')
        generate_certs()
        context = (CERT_FILE, KEY_FILE)
        kwargs = {'debug': args.debug, 'port': args.port, 'ssl_context' : context}
    else:
        print (' * Use HTTP')
        kwargs = {'debug': args.debug, 'port': args.port}

    if not args.debug:
        kwargs['host'] = '0.0.0.0'

    print (' * Running in', SPEC, 'mode')
    g.app.run(**kwargs)

if __name__ == '__main__':

    main()
else:
    startup()
