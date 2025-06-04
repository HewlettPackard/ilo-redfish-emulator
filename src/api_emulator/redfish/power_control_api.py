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

# Generic Power Control API File

"""
Dynamic resources:
 - Power Capping
    GET/PATCH /redfish/v1/Chassis/{sys_id}/Power
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

# applyPatch
#
# Applies the 'LimitInWatts' setting.
# 'LimitInWatts' must be a value between the Control's 'Min' and 'Max'.
# If 'LimitInWatts' is not specified in the PATCH, nothing will happen.
def applyPatch(raw_dict, ch_id):
    newLimits = []
    # Update specific portions of the identified object
    for i in range(len(members[ch_id]['PowerControl'])):
        control = members[ch_id]['PowerControl'][i]
        newLimitInWatts = 0
        min = 0
        max = 0
        if 'PowerLimit' in control and 'LimitInWatts' in control['PowerLimit']:
            newLimitInWatts = control['PowerLimit']['LimitInWatts']
        if 'PowerCapacityWatts' in control:
            max = control['PowerCapacityWatts']
        if 'OEM' in control:
            if 'Cray' in control['OEM']:
                mfr = 'Cray'
            elif 'HPE' in control['OEM']:
                mfr = 'HPE'
            else:
                return simple_error_response('Unsupported OEM controls', 400)
            if 'PowerLimit' in control['OEM'][mfr]:
                if 'Min' in control['OEM'][mfr]['PowerLimit']:
                    min = control['OEM'][mfr]['PowerLimit']['Min']
                if 'Max' in control['OEM'][mfr]['PowerLimit']:
                    max = control['OEM'][mfr]['PowerLimit']['Max']
        if 'PowerLimit' in raw_dict[i] and 'LimitInWatts' in raw_dict[i]['PowerLimit']:
            limit = raw_dict[i]['PowerLimit']['LimitInWatts']
            if ((limit <= max or max == 0) and limit >= min) or limit == 0:
                newLimitInWatts = limit
            else:
                return simple_error_response('LimitInWatts out of bounds for %s' % control['@odata.id'], 400)
        newLimits.append(newLimitInWatts)
    for i in range(len(newLimits)):
        control = members[ch_id][i]
        if 'PowerLimit' in control and 'LimitInWatts' in control['PowerLimit']:
            control['PowerLimit']['LimitInWatts'] = newLimits[i]
        elif newLimits[i] != 0:
            if 'PowerLimit' not in control:
                control['PowerLimit'] = {'LimitInWatts': newLimits[i]}
            else:
                control['PowerLimit']['LimitInWatts'] = newLimits[i]
    return success_response('Patch Successful', 200)

# PowerAPI
#
# This services GET and PATCH requests for computer system power controls.
#
class PowerAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('PowerAPI init called')
        self.allow = 'GET, PATCH'
        self.apiName = 'PowerAPI'

    # HTTP GET
    def get(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = members[ch_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    #
    # Apply power limit to the specified Control
    def patch(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                if 'PowerControl' in raw_dict and 'PowerControl' in members[ch_id] and \
                   raw_dict['PowerControl'] == len(members[ch_id]['PowerControl']):
                    resp = applyPatch(raw_dict['PowerControl'], ch_id)
                else:
                    resp = simple_error_response('Invalid paramters for PATCH', 400)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreatePower
#
# Called internally to create instances of a ComputerSystem power control.
# These resources are affected by PowerAPI()
#
def CreatePower(ch_id, config):
    logging.info('CreatePower put called')
    try:
        logging.debug('added config for %s/Power' % ch_id)
        members[ch_id] = config
    except Exception:
        traceback.print_exc()
