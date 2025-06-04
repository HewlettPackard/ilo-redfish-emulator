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

# Manager Network Protocol API File

"""
Dynamic resources:
 - Manager Network Protocol
    GET/PATCH /redfish/v1/Managers/{manager_id}/NetworkProtocol
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

typeMap = {
    'Oem': {
        'Syslog': {
            'ProtocolEnabled': bool,
            'SyslogServers':   list,
            'SyslogServersType': str,
            'Transport':       str,
            'Port':            int
        },
        'SSHAdmin': {
            'AuthorizedKeys': str,
        },
        'SSHConsole': {
            'AuthorizedKeys': str,
        }
    },
    'NTP': {
        'NTPServers': list,
        'NTPServersType': str,
        'Port': int,
        'ProtocolEnabled': bool
    }
}

# ManagerNetworkProtocolAPI
#
# This services GET and PATCH requests for manager network protocol.
#
class ManagerNetworkProtocolAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'GET, PATCH'
        self.apiName = 'ManagerNetworkProtocolAPI'

    # HTTP GET
    def get(self, m_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if m_id in members:
                resp = members[m_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, m_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if m_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, m_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if m_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, m_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if m_id in members:
                config = members[m_id]
                newOem = config['Oem'].copy()
                newNTP = config['NTP'].copy()
                if 'Oem' in raw_dict:
                    for group in ['Syslog', 'SSHAdmin', 'SSHConsole']:
                        if group in raw_dict['Oem']:
                            for field in raw_dict['Oem'][group]:
                                if field in typeMap['Oem'][group] and not isinstance(raw_dict['Oem'][group][field], typeMap['Oem'][group][field]):
                                    return simple_error_response('Invalid type for field Oem.%s.%s' % (group, field), 400)
                                if typeMap['Oem'][group][field] == list and '{}Type'.format(field) in typeMap['Oem'][group]:
                                    for item in raw_dict['Oem'][group][field]:
                                        if not isinstance(item, typeMap['Oem'][group]['{}Type'.format(field)]):
                                            return simple_error_response('Invalid type for field Oem.%s.%s' % (group, field), 400)
                                newOem[group][field] = raw_dict['Oem'][group][field]
                if 'NTP' in raw_dict:
                    for field in raw_dict['NTP']:
                        if field in typeMap['NTP'] and not isinstance(raw_dict['NTP'][field], typeMap['NTP'][field]):
                            return simple_error_response('Invalid type for field NTP.%s' % field, 400)
                        if typeMap['NTP'][field] == list and '{}Type'.format(field) in typeMap['NTP']:
                            for item in raw_dict['NTP'][field]:
                                if not isinstance(item, typeMap['NTP']['{}Type'.format(field)]):
                                    return simple_error_response('Invalid type for field NTP.%s' % field, 400)
                        newNTP[field] = raw_dict['NTP'][field]
                config['Oem'] = newOem
                config['NTP'] = newNTP
                resp = success_response('Patch Successful', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, m_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if m_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp



# CreateNetworkProtocol
#
# Called internally to create instances of a manager network protocol.
# These resources are affected by ManagerNetworkProtocolAPI()
#
def CreateNetworkProtocol(m_id, config):
    logging.info('CreateNetworkProtocol called')
    try:
        logging.debug('added config for %s/NetworkProtocol' % m_id)
        members[m_id] = config
    except Exception:
        traceback.print_exc()
