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
# INTERRUPTION) HOWEVER CAUSED OF AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

# BIOS Settings API File

"""
Dynamic resources:
 - BIOS Pending Settings
    GET/PATCH /redfish/v1/Systems/{sys_id}/bios/settings
"""

import sys, traceback
import logging
import json_merge_patch
from flask import request
from flask_restful import Resource

from .redfish_auth import auth, Privilege
from .response import simple_error_response, error_404_response, error_not_allowed_response

members = {}


class BiosSettingsAPI(Resource):
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'GET', 'PATCH'

    def get(self, sys_id):
        logging.info('BiosSettingsAPI GET called')
        try:
            resp = error_404_response(request.path)
            if sys_id in members:
                resp = members[sys_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    def patch(self, sys_id):
        logging.info('BiosSettingsAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if sys_id in members:
                members[sys_id] = json_merge_patch.merge(members[sys_id], raw_dict)
                resp = members[sys_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    def put(self, sys_id):
        logging.info('BiosSettingsAPI PUT called')
        try:
            resp = error_404_response(request.path)
            if sys_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    def post(self, sys_id):
        logging.info('BiosSettingsAPI POST called')
        try:
            resp = error_404_response(request.path)
            if sys_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    def delete(self, sys_id):
        logging.info('BiosSettingsAPI DELETE called')
        try:
            resp = error_404_response(request.path)
            if sys_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp


def CreateBiosSettings(sys_id, config):
    logging.info('CreateBiosSettings called')
    try:
        members[sys_id] = config
        resp = config, 200
    except Exception:
        traceback.print_exc()
        resp = simple_error_response('Server encountered an unexpected Error', 500)
    return resp
