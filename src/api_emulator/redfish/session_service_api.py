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

# Session Service API File

"""
Dynamic resources:
 - Session Service
    GET/POST   /redfish/v1/SessionService/Sessions
    GET/DELETE /redfish/v1/SessionService/Sessions/{id}
This modifies the emulator's authorized tokens
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from .redfish_auth import auth, Privilege, Session
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

collection_config = {}
members = {}

# SessionCollectionAPI
#
# This services GET and POST requests for Session Service.
#
class SessionCollectionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.Login})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureUsers})]}

    def __init__(self, **kwargs):
        logging.info('SessionCollectionAPI init called')
        self.allow = 'GET, POST'
        self.apiName = 'SessionCollectionAPI'

    # HTTP GET
    def get(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return collection_config, 200

    # HTTP PUT
    def put(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})

    # HTTP POST
    def post(self):
        logging.info('%s %s called' % (self.apiName, request.method))
        required_fields = ['Password', 'UserName']
        raw_dict = request.get_json(force=True)
        try:
            for field in required_fields:
                if field not in raw_dict:
                    return simple_error_response('Missing required field, %s' % field, 400)
            current_user = auth.get_current_user()
            username = raw_dict['UserName']
            if username != current_user.username or raw_dict['Password'] != current_user.password:
                return simple_error_response('Invalid credentials', 400)
            description = ''
            if 'Description' in raw_dict:
                description = raw_dict['Description']
            name = '{} Session'.format(username)
            if 'Name' in raw_dict:
                name = raw_dict['Name']
            session = Session(username)
            new_session_config = {
                '@odata.id': '/redfish/v1/SessionService/Sessions/{}'.format(session.sessionId),
                '@odata.type': '#Session.v1_1_0.Session',
                'Description': '{}'.format(description),
                'Id': '{}'.format(session.sessionId),
                'Name': '{}'.format(name),
                'UserName': '{}'.format(username)
            }
            new_session_link = {
                '@odata.id': '{}'.format(new_session_config['@odata.id'])
            }
            auth.start_session(session)
            collection_config['Members'].append(new_session_link)
            collection_config['Members@odata.count'] += 1
            members[new_session_config['Id']] = new_session_config
            resp = success_response(new_session_config['@odata.id'], 201, {'X-Auth-Token': session.token})
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

# SessionAPI
#
# This services GET and DELETE requests for Session Service.
#
class SessionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureSelf})]}

    def __init__(self, **kwargs):
        logging.info('SessionAPI init called')
        self.allow = 'GET, DELETE'
        self.apiName = 'SessionAPI'

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
                current_user = auth.get_current_user()
                if members[ident]['UserName'] != current_user.username:
                    # Check for additional privileges needed for modifying someone else's session.
                    if not current_user.privileges[Privilege.ConfigureUsers.name]:
                        return auth.auth_error('Basic')
                for i in range(len(collection_config['Members'])):
                    if collection_config['Members'][i]['@odata.id'] == members[ident]['@odata.id']:
                        del collection_config['Members'][i]
                        collection_config['Members@odata.count'] -= 1
                        auth.stop_session(ident)
                        del members[ident]
                        resp = success_response('Resource deleted', 200)
                        break
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateSessionService
#
# Called internally to initialize the API for the SessionService Sessions collection.
# This resource is affected by SessionCollectionAPI() and SessionAPI().
#
def CreateSessionService(config):
    global collection_config

    logging.debug('added config for SessionService')
    collection_config = config

# CreateSession
#
# Called internally to create instances of a Session in the SessionService.
# These resources are affected by SessionCollectionAPI() and SessionAPI()
#
def CreateSession(id, config):
    global members

    logging.debug('added config for SessionService/%s - %s' % (id, config['UserName']))
    members[id] = config

