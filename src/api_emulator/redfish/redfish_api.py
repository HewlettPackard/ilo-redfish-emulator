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

# Redfish Base API File

"""
Dynamic resources:
 - Redfish Static Resources
    GET /redfish/v1
    GET /redfish/v1/
    GET /redfish/v1/<path> - w/ auth
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
resourceManager = None

class PathError(Exception):
    pass

class RedfishBaseAPI(Resource):
    def __init__(self):
        #super(RedfishBaseAPI, self).__init__()
        pass

    def get(self):

        try:
            # Fetch ServiceRoot
            config = resourceManager.configuration
            resp = config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Internal Server Error', 500)
        return resp

# The following code provides a mechanism for the Redfish client to either
#    - Emulator Service Root
#    - Control the emulator
#    - Test code fragments
#
# To control the emulator:
#    - Issuing a DELETE /redfish/v1/reset to reset the emulator
#
# To test code fragments
#    - Issuing a POST with an Action to /redfish/v1/Chassis/{id} or /redfish/v1/Systems/{id} to perform action.
#       - Assumes {id} is an integer.
#       - Action may be ApplySettings, Reset, Subscribe
#    - Issuing a GET
#    - Issuing a DELETE /redfish/v1/xxx/{id} to remove a pooled node (need to add checks)
#
class RedfishAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self):
        # Dictionary of actions and their method
        # self.actions = {
            # 'CreateGenericComputerSystem': self.create_system,
            # 'ApplySettings':self.update_system,
            # 'Reset': self.create_system,
            # 'Subscribe': self.subscribe_events }

        # if resource_manager.spec == 'Redfish':
            # self.system_path = 'Systems'
            # self.chassis_path = 'Chassis'
            # self.actions['ApplySettings']=self.update_system
            # self.actions['Reset']=self.create_system
            # self.actions['Subscribe']=self.subscribe_events

        # super(RedfishAPI, self).__init__()
        pass

    """
    Let resource manager handle
    """
    def get(self, path):

        try:
            config = self.get_configuration(resourceManager, path)
            resp = config, 200
        except PathError:
            resp = error_404_response(request.path)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Internal Server Error', 500)
        return resp

    @staticmethod
    def get_configuration(obj, path):
        """
        Helper function to follow the given path starting with the given object

        Arguments:
            obj  - Beginning object to start searching down.  obj should have a get_resource()
            path - Path of object to get

        """

        try:
            config = obj.get_resource(path)
        except (IndexError, AttributeError, TypeError, AssertionError, KeyError) as e:
            raise PathError("Resource not found: {}".format(e))
        return config

def CreateRedfishBase(resource_manager):
    global resourceManager
    resourceManager = resource_manager