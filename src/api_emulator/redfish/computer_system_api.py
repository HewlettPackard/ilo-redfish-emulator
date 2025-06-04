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

# ComputerSystem API File

"""
Dynamic resources:
 - System Power Actions
    GET/PATCH /redfish/v1/Systems/{sys_id}
    GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
"""

import sys, traceback
import logging
import json_merge_patch
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from threading import Thread
from time import sleep

import g
from .redfish_auth import auth, Privilege
from .event_generator import GenEvent, GenEventRecord
from .event_service_api import send_event
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

members = {}
members_actions = {}
members_reset_thread = {}

reboot_actions = ['GracefulRestart', 'ForceRestart', 'PushPowerButton']
off_actions = ['Off', 'ForceOff', 'GracefulShutdown', 'Nmi']
on_actions = ['On', 'ForceOn']

default_actions = ['ForceOff', 'On', 'Off']

def isPowerOn(system_id):
    """
    Check if the system is powered on.
    Returns True if PowerState is 'On', otherwise False.
    """
    if system_id in members:
        return members[system_id]['PowerState'] == 'On'
    return False

# ResetWorker
#
# Worker thread for performing emulated asynchronous computer system power resets.
#
class ResetWorker(Thread):
    def __init__(self, sys_id):
        super(ResetWorker, self).__init__()
        self.sys_id = sys_id

    def run(self):
        members[self.sys_id]['PowerState'] = 'Off'
        members[self.sys_id]['Status']['State'] = 'Disabled'
        send_power_event(self.sys_id, 'Off')
        sleep(g.async_sleep)
        members[self.sys_id]['PowerState'] = 'PoweringOn'
        members[self.sys_id]['Status']['State'] = 'Starting'
        send_power_event(self.sys_id, 'On')
        sleep(g.async_sleep)
        members[self.sys_id]['PowerState'] = 'On'
        members[self.sys_id]['Status']['State'] = 'Enabled'

# PowerOnWorker
#
# Worker thread for performing emulated asynchronous computer system power on actions.
#
class PowerOnWorker(Thread):
    def __init__(self, sys_id):
        super(PowerOnWorker, self).__init__()
        self.sys_id = sys_id

    def run(self):
        members[self.sys_id]['PowerState'] = 'PoweringOn'
        members[self.sys_id]['Status']['State'] = 'Starting'
        send_power_event(self.sys_id, 'On')
        sleep(g.async_sleep)
        members[self.sys_id]['PowerState'] = 'On'
        members[self.sys_id]['Status']['State'] = 'Enabled'

def send_power_event(id, power_state):
    ooc = members[id]['@odata.id']
    er = GenEventRecord('Power', powerState=power_state, OriginOfCondition=ooc)
    e = GenEvent([er])
    send_event(e, 'Alert')

# ComputerSystemAPI
#
# This services GET requests for computer systems. These are affected by
# POST requests to ResetAction_API()
#
class ComputerSystemAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('ComputerSystemAPI init called')
        self.allow = 'GET', 'PATCH'
        try:
            global wildcards
            wildcards = kwargs
        except Exception:
            traceback.print_exc()

    # HTTP GET
    def get(self, ident):
        logging.info('ComputerSystemAPI GET called')
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
        logging.info('ComputerSystemAPI PUT called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ident):
        logging.info('ComputerSystemAPI POST called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        logging.info('ComputerSystemAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                members[ident] = json_merge_patch.merge(members[ident], raw_dict)
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info('ComputerSystemAPI DELETE called')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateComputerSystem
#
# Called internally to create instances of a ComputerSystem. These
# resources are affected by ResetAction_API()
#
def CreateComputerSystem(ident, config, rst_actions):
    logging.info('CreateComputerSystem called')
    try:
        logging.debug('added config for Systems/%s' % ident)
        members[ident] = config
        if len(rst_actions) == 0:
            members_actions[ident] = default_actions
        else:
            members_actions[ident] = rst_actions
        members_reset_thread[ident] = None

        resp = config, 200
    except Exception:
        traceback.print_exc()
        resp = INTERNAL_ERROR
    return resp

# ResetAction_API
#
# This services ResetAction POST requests to emulate computer system power actions.
# POST requests that result in PowerState changes will generate Redfish events for
# subscribers to the EventService.
#
class ResetAction_API(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        self.allow = 'POST'
    
    # HTTP POST
    def post(self, ident):
        logging.info('ResetAction_API POST called')
        raw_dict = request.get_json(force=True)
        logging.info(raw_dict)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                if 'ResetType' in raw_dict:
                    value = raw_dict['ResetType']
                    if value in members_actions[ident]:
                        state = members[ident]['PowerState']
                        
                        if members_reset_thread[ident] is not None and members_reset_thread[ident].is_alive():
                            # Ignore other power actions if we have a pending thread.
                            logging.info('Thread is running. Ignoring request')
                        elif value in reboot_actions:
                            if state == 'On':
                                logging.info('Starting reset thread')
                                members_reset_thread[ident] = ResetWorker(ident)
                                members_reset_thread[ident].start()
                            else:
                                logging.info('Reset action with current PowerState Off. Starting reset thread')
                                members_reset_thread[ident] = PowerOnWorker(ident)
                                members_reset_thread[ident].start()
                        elif value in off_actions:
                            logging.info('Powering Off')
                            members[ident]['PowerState'] = 'Off'
                            members[ident]['Status']['State'] = 'Disabled'
                            send_power_event(ident, 'Off')
                        elif value in on_actions:
                            logging.info('Starting reset thread')
                            members_reset_thread[ident] = PowerOnWorker(ident)
                            members_reset_thread[ident].start()
                        resp = members[ident], 200
                    else:
                        resp = simple_error_response('Invalid ResetType', 400)
                else:
                    resp = simple_error_response('Invalid setting for POST', 400)
        except Exception:
            traceback.print_exc()
            resp = INTERNAL_ERROR
        return resp

    # HTTP GET
    def get(self, ident):
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
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
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
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp