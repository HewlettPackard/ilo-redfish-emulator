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

# Network Device Function API

"""
Dynamic resources:
 - NetworkDeviceFunction instance
    GET/PATCH /redfish/v1/Chassis/{chassis_id}/NetworkAdapters/{adapter_id}/NetworkDeviceFunctions/{func_id}
"""

import sys
import traceback
import logging
import json_merge_patch
from flask import request
from flask_restful import Resource

from .redfish_auth import auth, Privilege
from .response import simple_error_response, error_404_response, error_not_allowed_response

# members keyed by "<chassis_id>_<adapter_id>_<func_id>"
members = {}


class NetworkDeviceFunctionAPI(Resource):
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'GET', 'PATCH'
        self.apiName = 'NetworkDeviceFunctionAPI'

    def get(self, chassis_id, adapter_id, func_id):
        logging.info('%s GET called' % self.apiName)
        try:
            ident = _ident(chassis_id, adapter_id, func_id)
            if ident not in members:
                return error_404_response(request.path)
            return members[ident], 200
        except Exception:
            traceback.print_exc()
            return simple_error_response('Server encountered an unexpected Error', 500)

    def patch(self, chassis_id, adapter_id, func_id):
        logging.info('%s PATCH called' % self.apiName)
        raw_dict = request.get_json(force=True)
        try:
            ident = _ident(chassis_id, adapter_id, func_id)
            if ident not in members:
                return error_404_response(request.path)
            members[ident] = json_merge_patch.merge(members[ident], raw_dict)
            return members[ident], 200
        except Exception:
            traceback.print_exc()
            return simple_error_response('Server encountered an unexpected Error', 500)

    def put(self, chassis_id, adapter_id, func_id):
        logging.info('%s PUT called' % self.apiName)
        try:
            ident = _ident(chassis_id, adapter_id, func_id)
            if ident not in members:
                return error_404_response(request.path)
            return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            return simple_error_response('Server encountered an unexpected Error', 500)

    def post(self, chassis_id, adapter_id, func_id):
        logging.info('%s POST called' % self.apiName)
        try:
            ident = _ident(chassis_id, adapter_id, func_id)
            if ident not in members:
                return error_404_response(request.path)
            return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            return simple_error_response('Server encountered an unexpected Error', 500)

    def delete(self, chassis_id, adapter_id, func_id):
        logging.info('%s DELETE called' % self.apiName)
        try:
            ident = _ident(chassis_id, adapter_id, func_id)
            if ident not in members:
                return error_404_response(request.path)
            return error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            return simple_error_response('Server encountered an unexpected Error', 500)


def InitNetworkDeviceFunction(chassis_id, adapter_id, func_id, config):
    logging.info('InitNetworkDeviceFunction called for %s/%s/%s' % (chassis_id, adapter_id, func_id))
    try:
        members[_ident(chassis_id, adapter_id, func_id)] = config
        return config, 200
    except Exception:
        traceback.print_exc()
        return simple_error_response('Server encountered an unexpected Error', 500)


def _ident(chassis_id, adapter_id, func_id):
    return '%s_%s_%s' % (chassis_id, adapter_id, func_id)
