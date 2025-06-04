# BSD 3-Clause License
#
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

# HPE Cray EX Certificate Service API File

"""
Dynamic resources:
 - Certificate Service
    GET  /redfish/v1/Managers/BMC/NetworkProtocol/HTTPS/Certificates/{cert_id}
    POST /redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from .redfish_auth import auth, Privilege
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

members = {}

required_post_fields = [
    'CertificateString',
    'CertificateType',
    'CertificateUri'
]
cert_types = [
    'PEM',
    'PEMChain',
    'PKCS7'
]
key_usage = [
    'DigitalSignature',
    'NonRepudiation',
    'KeyEncipherment',
    'DataEncipherment',
    'KeyAgreement',
    'KeyCertSign',
    'CRLSigning',
    'EncipherOnly',
    'DecipherOnly',
    'ServerAuthentication',
    'ClientAuthentication',
    'CodeSigning',
    'EmailProtection',
    'Timestamping',
    'OCSPSigning'
]
type_map = {
    'CertificateString': str,
    'CertificateType': str,
    'Description': str,
    'Id': str,
    'KeyUsage': str,
    'Name': str,
    'CertificateUri': dict,
    'CertificateUriType': str
}


# CertificateAPI
#
# This services GET requests for certificates.
#
class CertificateAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'GET'
        self.apiName = 'CertificateAPI'

    # HTTP GET
    def get(self, ident):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if ident in members:
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ident):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# ReplaceCertificateAPI
#
# This services POST requests for certificate service ReplaceCertificate actions.
#
class ReplaceCertificateAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'POST'
        self.apiName = 'ReplaceCertificateAPI'

    # HTTP GET
    def get(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})

    # HTTP PUT
    def put(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})

    # HTTP POST
    def post(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        try:
            for field in required_post_fields:
                if field not in raw_dict:
                    return simple_error_response('Missing required paramter for POST, %s' % field, 400)
            if raw_dict['CertificateType'] not in cert_types:
                return simple_error_response('Invalid certificate type, %s' % raw_dict['CertificateType'], 400)
            parts = raw_dict['CertificateUri']['@odata.id'].split('/')
            cert_id = parts[len(parts) - 1]
            if cert_id not in members:
                return simple_error_response('Invalid CertificateUri, %s' % raw_dict['CertificateUri']['@odata.id'], 400)
            newCert = members[cert_id].copy()
            for field in raw_dict:
                if field in type_map:
                    if not isinstance(raw_dict[field], type_map[field]):
                        return simple_error_response('Invalid type for field %s' % field, 400)
                    if type_map[field] == dict and '{}Type'.format(field) in type_map:
                        for sub_field in raw_dict[field]:
                            if not isinstance(raw_dict[field][sub_field], type_map['{}Type'.format(field)]):
                                return simple_error_response('Invalid type for field %s.%s' % (field, sub_field), 400)
                    if field == 'CertificateString':
                        newCert['Certificate'] = raw_dict[field]
                    elif field == 'CertificateType':
                        # Only used for checking the type
                        pass
                    elif field == 'KeyUsage':
                        if raw_dict[field] not in key_usage:
                            return simple_error_response('Invalid KeyUsage, %s' % raw_dict[field], 400)
                    else:
                        newCert[field] = raw_dict[field]
            for field in newCert:
                members[cert_id][field] = newCert[field]
            resp = success_response('POST Successful', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})

    # HTTP DELETE
    def delete(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})

# def CreateCertService(cert_loc_config, cert_collection):
    # logging.info('CreateCertService called')
    # try:
        # global locations
        # global collection
        # logging.debug('added config for CertificateService')
        # locations = cert_loc_config
        # collection = cert_collection
    # except Exception:
        # traceback.print_exc()

# CreateCert
#
# Called internally to create instances of a certificate.
# These resources are affected by ReplaceCertificateAPI()
#
def CreateCert(cert_id, cert_config):
    logging.info('CreateCert called')
    try:
        logging.debug('added config for %s' % cert_config['@odata.id'])
        members[cert_id] = cert_config
    except Exception:
        traceback.print_exc()
