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

# Account Service API File

"""
Dynamic resources:
 - Account Service
    GET/POST         /redfish/v1/AccountService/Accounts
    GET/PATCH/DELETE /redfish/v1/AccountService/Accounts/{id}
This modifies the emulator's authorized users
"""

import g

import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from .redfish_auth import auth, Privilege, ROLES, User
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

collection_config = {}
members = {}
account_schema = '#ManagerAccount.v1_0_0.ManagerAccount'

# AccountCollectionAPI
#
# This services GET and POST requests for Account Service.
#
class AccountCollectionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureUsers})]}

    def __init__(self, **kwargs):
        logging.info('AccountCollectionAPI init called')
        self.allow = 'GET, POST'
        self.apiName = 'AccountCollectionAPI'

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
        required_fields = ['Password', 'UserName', 'RoleId']
        raw_dict = request.get_json(force=True)
        try:
            for field in required_fields:
                if field not in raw_dict:
                    return simple_error_response('Missing required field, %s' % field, 400)
            for id, member in members.items():
                if raw_dict['UserName'] == member['UserName']:
                    return simple_error_response('Duplicate username', 400)
            if raw_dict['RoleId'] not in ROLES:
                return simple_error_response('Invalid RoleId', 400)
            username = raw_dict['UserName']
            role = raw_dict['RoleId']
            privileges = ROLES[role]
            password = raw_dict['Password']
            description = ''
            if 'Description' in raw_dict:
                description = raw_dict['Description']
            name = raw_dict['UserName']
            if 'Name' in raw_dict:
                name = raw_dict['Name']
            id = collection_config['Members@odata.count'] + 1
            new_account_config = {
                '@odata.id': '/redfish/v1/AccountService/Accounts/{}'.format(id),
                '@odata.type': '{}'.format(account_schema),
                'Description': '{}'.format(description),
                'Enabled': True,
                'Id': '{}'.format(id),
                'Links': {
                    'Role': {
                        '@odata.id': '/redfish/v1/AccountService/Roles/{}'.format(role)
                    }
                },
                'Locked': False,
                'Name': '{}'.format(name),
                'RoleId': '{}'.format(role),
                'UserName': '{}'.format(username)
            }
            new_account_link = {
                '@odata.id': '{}'.format(new_account_config['@odata.id'])
            }
            newUser = User(username, password, role, privileges)
            auth.add_user(newUser)
            collection_config['Members'].append(new_account_link)
            collection_config['Members@odata.count'] += 1
            members[new_account_config['Id']] = new_account_config
            resp = success_response(new_account_config['@odata.id'], 201)
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

# AccountAPI
#
# This services GET PATCH and DELETE requests for Account Service.
#
class AccountAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureUsers})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureSelf})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureUsers})]}

    def __init__(self, **kwargs):
        logging.info('AccountAPI init called')
        self.allow = 'GET, PATCH, DELETE'
        self.apiName = 'AccountAPI'

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
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                current_user = auth.get_current_user()
                if members[ident]['UserName'] != current_user.username or 'RoleId' in raw_dict:
                    # Check for additional privileges needed for modifying someone else's account.
                    if not current_user.privileges[Privilege.ConfigureUsers.name]:
                        return auth.auth_error('Basic')
                user = auth.get_user(members[ident]['UserName'])
                newUsername = user.username
                newPassword = user.password
                newRole = user.role
                newPrivileges = user.privileges
                newRoleLink = members[ident]['Links']['Role']['@odata.id']
                if 'Password' in raw_dict:
                    newPassword = raw_dict['Password']
                if 'RoleId' in raw_dict and raw_dict['RoleId'] != members[ident]['RoleId']:
                    if raw_dict['RoleId'] not in ROLES:
                        return simple_error_response('Invalid RoleId', 400)
                    newRole = raw_dict['RoleId']
                    newPrivileges = ROLES[newRole]
                    newRoleLink = newRoleLink.replace(user.role, newRole)
                if 'UserName' in raw_dict and raw_dict['UserName'] != members[ident]['UserName']:
                    # Username change will create a new user and delete the old user
                    for id, member in members.items():
                        if raw_dict['UserName'] == member['UserName']:
                            return simple_error_response('Duplicate username', 400)
                    newUsername = raw_dict['UserName']
                    newUser = User(newUsername, newPassword, newRole, newPrivileges)
                    auth.add_user(newUser)
                    auth.delete_user(members[ident]['UserName'])
                else:
                    # Non-username change just modifies user fields
                    user.password = newPassword
                    user.role = newRole
                    user.privileges = newPrivileges
                members[ident]['UserName'] = newUsername
                members[ident]['RoleId'] = newRole
                members[ident]['Links']['Role']['@odata.id'] = newRoleLink
                resp = success_response('Resource patched', 200)
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
                for i in range(len(collection_config['Members'])):
                    if collection_config['Members'][i]['@odata.id'] == members[ident]['@odata.id']:
                        del collection_config['Members'][i]
                        collection_config['Members@odata.count'] -= 1
                        auth.delete_user(members[ident]['UserName'])
                        del members[ident]
                        resp = success_response('Resource deleted', 200)
                        break
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateAccountService
#
# Called internally to initialize the API for the AccountService Accounts collection.
# This will not add users to the emulator's authorization handler.
# This resource is affected by AccountCollectionAPI() and AccountAPI().
#
def CreateAccountService(config, acc_schema):
    global collection_config
    global account_schema

    logging.debug('added config for AccountService')
    collection_config = config
    account_schema = acc_schema

# CreateAccount
#
# Called internally to create instances of an Account in the AccountService.
# This will not add users to the emulator's authorization handler.
# These resources are affected by AccountCollectionAPI() and AccountAPI()
#
def CreateAccount(id, config):
    global members

    logging.debug('added config for AccountService/%s - %s' % (id, config['UserName']))
    members[id] = config

