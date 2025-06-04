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

# Proliant iLO Power Control API File

"""
Dynamic resources:
 - Power Capping
    GET  /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit
    POST /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit/Actions/HpeServerAccPowerLimit.ConfigurePowerLimit
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

# applylimit
#
# Applies the 'PowerLimitInWatts' setting to the AccPowerService.
# 'PowerLimitInWatts' must be a value between the Control's 'Min' and 'Max'.
def applyLimit(raw_dict, member):
    newLimits = []
    # Update specific portions of the identified object
    for req_control in raw_dict:
        for i in range(len(member['PowerLimits'])):
            control = member['PowerLimits'][i]
            ranges = member['PowerLimitRanges'][i]
            if req_control['ZoneNumber'] != control['ZoneNumber']:
                continue
            newLimitInWatts = control['PowerLimitInWatts']
            min = ranges['MinimumPowerLimit']
            max = ranges['MaximumPowerLimit']
            limit = raw_dict[i]['PowerLimit']['LimitInWatts']
            if ((limit <= max or max == 0) and limit >= min) or limit == 0:
                newLimitInWatts = limit
            else:
                return simple_error_response('PowerLimitInWatts out of bounds for zone %s' % req_control['ZoneNumber'], 400)
            newLimits.append({'idx': i, 'limit': newLimitInWatts})
    for limit in range(len(newLimits)):
        member['PowerLimits'][limit['idx']]['PowerLimitInWatts'] = limit['limit']
    return success_response('Patch Successful', 200)

# AccPowerServiceAPI
#
# This services GET requests for AccPowerServiceAPI.
#
class AccPowerServiceAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('AccPowerServiceAPI init called')
        self.allow = 'GET'
        self.apiName = 'AccPowerServiceAPI'

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
    def patch(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
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

# ActionAPI
#
# This services POST requests for computer system power controls.
#
class ActionAPI(Resource):
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
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
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
    #
    # Apply power limit to the specified Control
    def post(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                if 'PowerLimits' in raw_dict:
                    for req_control in raw_dict['PowerLimits']:
                        found = False
                        for control in members[ch_id]['PowerLimits']:
                            if 'ZoneNumber' not in req_control or 'PowerLimitInWatts' not in req_control:
                                return simple_error_response('Invalid paramters for POST', 400)
                            if req_control['ZoneNumber'] == control['ZoneNumber']:
                                found = True
                                break
                        if not found:
                            return simple_error_response('Invalid ZoneNumber {}'.format(req_control['ZoneNumber']), 400)
                    resp = applyLimit(raw_dict['PowerLimits'], members[ch_id])
                else:
                    resp = simple_error_response('Invalid paramters for POST', 400)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ch_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if ch_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
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
# These resources are affected by ActionAPI()
#
def CreatePower(ch_id, config):
    logging.info('CreatePower called')
    try:
        logging.debug('added config for %s/Power/AccPowerService/PowerLimit' % ch_id)
        members[ch_id] = config
    except Exception:
        traceback.print_exc()
