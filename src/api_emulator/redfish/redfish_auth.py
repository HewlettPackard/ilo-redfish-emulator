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

import enum
import copy
import logging
import json
import strgen
from functools import wraps

from flask import request

from .response import error_unauthorized_response
from ..static_loader import Member

class AuthConfigError(Exception):
    pass

# This set of Default roles and privileges are defined by DMTF:
# http://redfish.dmtf.org/schemas/DSP0266_1.11.0.html#privilege-model
class Privilege(enum.Enum):
    Login = 1
    ConfigureManager = 2
    ConfigureUsers =  3
    ConfigureSelf =  4
    ConfigureComponents =  5

class User:
    def __init__(self, username, password, role, privileges):
        self.username = username
        self.password = password
        self.role = role
        self.privileges = {}
        for priv in Privilege:
            if priv.name in privileges:
                self.privileges[priv.name] = privileges[priv.name]
            else:
                self.privileges[priv.name] = False

ADMIN_USER = User('root',
                  'root_password',
                  'Administrator',
                  {
                      Privilege.Login.name:               True,
                      Privilege.ConfigureManager.name:    True,
                      Privilege.ConfigureUsers.name:      True,
                      Privilege.ConfigureSelf.name:       True,
                      Privilege.ConfigureComponents.name: True
                  })

OPERATOR_USER = User('operator',
                     'operator_password',
                     'Operator',
                     {
                         Privilege.Login.name:               True,
                         Privilege.ConfigureManager.name:    False,
                         Privilege.ConfigureUsers.name:      False,
                         Privilege.ConfigureSelf.name:       True,
                         Privilege.ConfigureComponents.name: True
                     })

GUEST_USER = User('guest',
                  'guest_password',
                  'ReadOnly',
                  {
                      Privilege.Login.name:               True,
                      Privilege.ConfigureManager.name:    False,
                      Privilege.ConfigureUsers.name:      False,
                      Privilege.ConfigureSelf.name:       True,
                      Privilege.ConfigureComponents.name: False
                  })

DEFAULT_USERS = {
                    ADMIN_USER.username: ADMIN_USER,
                    OPERATOR_USER.username: OPERATOR_USER,
                    GUEST_USER.username: GUEST_USER
                }

ROLES = {'Administrator': ADMIN_USER.privileges, 'Operator': OPERATOR_USER.privileges, 'ReadOnly': GUEST_USER.privileges}

class Session:
    def __init__(self, username):
        self.username = username
        self.sessionId = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
        self.token = '{}SESSION{}'.format(self.sessionId, username)

# this is the Base HTTP Auth class that is used to derive the Redfish "Basic or Token Auth" class
class RedfishAuth(object):
    def __init__(self):
        self.realm = "CSM_Redfish_Emulator"
        self.users = DEFAULT_USERS.copy()
        self.sessions = {}

    def auth_error(self, scheme):
        headers = {'WWW-Authenticate': '{0} realm="{1}"'.format(scheme, self.realm)}
        return error_unauthorized_response(request.path, headers)

    def verify_privileges(self, user_privileges, required_privileges):
        for req_priv in required_privileges:
            if not user_privileges[req_priv.name]:
                return False
        return True

    # define basic auth decorator used by flask
    # for basic auth, we only support user=catfish, passwd=hunter
    def verify_basic(self, req_username, req_password, required_privileges):
        if req_username in self.users:
            user = self.users[req_username]
            if user.password == req_password:
                return self.verify_privileges(user.privileges, required_privileges)
        return False

    # define Redfish Token/Session auth decorator used by flask
    # for session token auth, only support toden: 123456CATFISHauthcode
    def verify_token(self, auth_token, required_privileges):
        fields = auth_token.split('SESSION', 1)
        if fields[0] in self.sessions:
            username = self.sessions[fields[0]].username
            if fields[1] == username and username in self.users:
                user = self.users[username]
                return self.verify_privileges(user.privileges, required_privileges)
        return False

    # for redfish, we need to hook this to check if its token auth before trying basic auth
    def auth_required(self, priv={Privilege.Login}):
        def decorator(f):
            @wraps(f)
            def inner(*args, **kwargs):
                req_auth = request.authorization
                # logging.info('auth_required required privileges = %s' % priv)
                # logging.info('headers: {}'.format(request.headers))
                scheme = 'Basic'
                # req_auth is None if the Basic auth header didn't come in the request
                if req_auth is None:
                    # check if we have a redfish auth token
                    auth_token = request.headers.get('X-Auth-Token')
                    if auth_token is not None:
                        scheme = 'X-Auth-Token'
                        # We found an auth token in the headers
                        if self.verify_token(auth_token, priv):
                            # We had an auth token, but it didn't validate
                            return f(*args, **kwargs)
                else:
                    # Do Basic Auth validation
                    if self.verify_basic(req_auth.username, req_auth.password, priv):
                        return f(*args, **kwargs)

                return self.auth_error(scheme)
            return inner
        return decorator

    def set_users(self, users):
        logging.debug('set_users called')
        self.users = users

    def set_auth_from_env(self, auth_config):
        logging.debug('set_auth_from_env called')
        users = self.env_to_users(auth_config)
        self.set_users(users)

    def add_user(self, user):
        self.users[user.username] = user

    def delete_user(self, username):
        del self.users[username]

    def get_users(self):
        return self.users

    def get_user(self, username):
        return self.users[username]

    def get_current_user(self):
        username = ''
        req_auth = request.authorization
        if req_auth is None:
            # check if we have a redfish auth token
            auth_token = request.headers.get('X-Auth-Token')
            fields = auth_token.split('SESSION', 1)
            username = fields[1]
        else:
            username = req_auth.username
        return self.users[username]

    @staticmethod
    def env_to_users(auth_config):
        new_users = {}
        user_strings = []
        user_strings = auth_config.split(';')
        for user_str in user_strings:
            user_fields = user_str.split(':')
            if len(user_fields) < 3:
                msg = 'Not enough fields for user (username:password:role)'
                logging.debug(msg)
                raise AuthConfigError(msg)
            name = user_fields[0]
            pw = user_fields[1]
            role = user_fields[2]
            # Default to Admin privileges
            privileges = ADMIN_USER.privileges
            if role in ROLES:
                privileges = ROLES[role]
            else:
                msg = 'Invalid role %s. Must be one of %s' % (role, ROLES.keys())
                logging.debug(msg)
                raise AuthConfigError(msg)
            new_users[name] = User(name, pw, role, privileges)
        return new_users

    # Add any auth users to the mockup if they don't exist.
    # In the future maybe also create auth users for any accounts in the mockup?
    def sync_with_account_service(self, resource_dictionary):
        accounts = {}
        account_schema = '#ManagerAccount.v1_0_0.ManagerAccount'
        accounts_config = resource_dictionary.get_object('AccountService/Accounts')
        # Get all of the accounts defined in the mockup
        for member in accounts_config.configuration['Members']:
            url = member['@odata.id']
            url = url.replace('/redfish/v1/', '')
            account_config = resource_dictionary.get_resource(url)
            accounts[account_config['UserName']] = account_config
            account_schema = account_config['@odata.type']
        for name in self.users:
            # Create an account in the mockup for any user that doesn't exist.
            if name not in accounts:
                accounts_config.configuration['Members@odata.count'] += 1
                id = accounts_config.configuration['Members@odata.count']
                new_account_config = {
                    '@odata.id': '/redfish/v1/AccountService/Accounts/{}'.format(id),
                    '@odata.type': '{}'.format(account_schema),
                    'Description': '',
                    'Enabled': True,
                    'Id': '{}'.format(id),
                    'Links': {
                        'Role': {
                            '@odata.id': '/redfish/v1/AccountService/Roles/{}'.format(self.users[name].role)
                        }
                    },
                    'Locked': False,
                    'Name': '{}'.format(self.users[name].username),
                    'RoleId': '{}'.format(self.users[name].role),
                    'UserName': '{}'.format(name)
                }
                new_account_link = {
                    '@odata.id': '{}'.format(new_account_config['@odata.id'])
                }
                accounts_config.configuration['Members'].append(new_account_link)
                url = new_account_config['@odata.id'].replace('/redfish/v1/','')
                resource_dictionary.add_resource(url, Member(new_account_config))

    def start_session(self, session):
        self.sessions[session.sessionId] = session

    def stop_session(self, sessionId):
        del self.sessions[sessionId]

auth = RedfishAuth()
