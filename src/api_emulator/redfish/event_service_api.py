# BSD 3-Clause License
#
# Copyright 2022-2024 Hewlett Packard Enterprise Development LP
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

# EventService API File

"""
Dynamic resources:
 - Event Service
    GET/PATCH        /redfish/v1/EventService
    GET/POST         /redfish/v1/EventService/Subscriptions
    GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/{id}
Resources that sent events:
 - computer_systems_api.ResetAction_API
"""

import g

import sys, traceback
import logging
import copy
import json
import urllib.request
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource

from .redfish_auth import auth, Privilege
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

from threading import Thread

e_config = {}
s_config = {}
s_generator = None
members = {}
required = {'Destination'}  # Fields required for POST subscription
eventTemplates = {}
id = 1

NOT_FOUND_ERROR = {"Status": 404, "Message": "Attribute Does Not Exist"}
INTERNAL_ERROR = 500

# EventWorker
#
# EventWorker threads are spawned per subscription per event for sending
# redfish events to subscribers to the EventService.
class EventWorker(Thread):
    """
    Worker class for sending event messages to clients
    """
    def __init__(self, dest_uri, event):
        super(EventWorker, self).__init__()
        self.dest_uri = dest_uri
        self.event = event

    def run(self):
        try:
            logging.debug('Sending event')
            logging.debug(self.event)
            request = urllib.request.Request(self.dest_uri)
            request.add_header('Content-Type', 'application/json')
            urllib.request.urlopen(request, json.dumps(self.event).encode('utf-8'), 15)
            logging.debug('Send succeeded')
        except Exception:
            traceback.print_exc()
            logging.debug('Send failed')
            pass

# send_event
#
# Spawns threads per subscription per event for sending
# redfish events to subscribers of the EventService.
# This function adds the Context field to the event and
# its event records (if specified by the template).
def send_event(event, type):
    for name, sub in members.items():
        e = event.copy()
        event_types = sub['EventTypes']
        dest_uri = sub['Destination']
        ctx = ""
        if 'Context' in sub:
            ctx = sub['Context']

        e['Context'] = ctx
        for er in e['Events']:
            # Adds Context but only if our event template allows us to
            er['Context'] = er['Context'].format(Context = ctx)
        if type in event_types:
            EventWorker(dest_uri, e).start()

# EventServiceAPI
#
# Services GET and PATCH requests for the EventService resource.
class EventServiceAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('EventServiceAPI init called')
        self.allow = 'GET, PATCH'

    # HTTP GET
    def get(self):
        logging.info('EventServiceAPI GET called')
        try:
            resp = e_config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self):
        logging.info('EventServiceAPI PUT called')
        return error_not_allowed_response(e_config['@odata.id'], 'PUT', {'Allow': self.allow})

    # HTTP POST
    def post(self):
        logging.info('EventServiceAPI POST called')
        return error_not_allowed_response(e_config['@odata.id'], 'POST', {'Allow': self.allow})

    # HTTP PATCH
    def patch(self):
        logging.info('EventServiceAPI PATCH called')
        raw_dict = request.get_json(force=True)
        try:
            resp = success_response('PATCH request successful', 200)
            for key, value in raw_dict.items():
                if key in {'DeliveryRetryAttempts', 'DeliveryRetryIntervalSeconds'}:
                    e_config[key] = value
                else:
                    resp = simple_error_response('Invalid setting for PATCH', 400)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self):
        logging.info('EventServiceAPI DELETE called')
        return error_not_allowed_response(e_config['@odata.id'], 'DELETE', {'Allow': self.allow})

# SubscriptionCollectionAPI
#
# Services GET and POST requests for the subscriptions collection.
# POST requests will add new subscriptions.
class SubscriptionCollectionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('SubscriptionCollectionAPI init called')
        self.allow = 'GET, POST'

    # HTTP GET
    def get(self):
        logging.info('SubscriptionCollectionAPI GET called')
        try:
            resp = s_config, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self):
        logging.info('SubscriptionCollectionAPI PUT called')
        return error_not_allowed_response(s_config['@odata.id'], 'PUT', {'Allow': self.allow})

    # HTTP POST
    def post(self):
        global id
        logging.info('SubscriptionCollectionAPI POST called')
        raw_dict = request.get_json(force=True)
        for field in required:
            if field not in raw_dict:
                return simple_error_response('%s is required' % (field) , 400)
        ident = '%d' % id
        
        destination = raw_dict.get('Destination', '')
        event_types = raw_dict.get('EventTypes', '')
        if 'EventTypesForSubscription' in e_config:  # XD224 Paradise does not have this field
            for evType in event_types:
                if evType not in e_config['EventTypesForSubscription']:
                    return 'Invalid EventType %s' % evType, 400

        if 'Context' in raw_dict:
            context = raw_dict['Context']
        else:
            context = None
        if 'RegistryPrefixes' in raw_dict:
            registry_prefixes = raw_dict['RegistryPrefixes']
        else:
            registry_prefixes = None
        CreateSubscription(ident, destination, event_types, context, registry_prefixes)
        id += 1
        return success_response('/redfish/v1/EventService/Subscriptions/%s' % ident, 201)

    # HTTP PATCH
    def patch(self):
        logging.info('SubscriptionCollectionAPI PATCH called')
        return error_not_allowed_response(s_config['@odata.id'], 'PATCH', {'Allow': self.allow})

    # HTTP DELETE
    def delete(self):
        logging.info('SubscriptionCollectionAPI DELETE called')
        return error_not_allowed_response(s_config['@odata.id'], 'DELETE', {'Allow': self.allow})

# SubscriptionAPI
#
# Services GET, PATCH, and DELETE requests for managing Redfish event subscriptions.
# DELETE requests will remove the subscription from the subscription collection.
class SubscriptionAPI(Resource):
# Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('SubscriptionAPI init called')
        self.allow = 'GET, PATCH, DELETE'

    # HTTP GET
    def get(self, ident):
        logging.info(f'SubscriptionAPI GET called: {ident}')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = members[ident], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, ident):
        logging.info(f'SubscriptionAPI PUT called: {ident}')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], 'PUT', {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, ident):
        logging.info(f'SubscriptionAPI POST called: {ident}')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                resp = error_not_allowed_response(members[ident]['@odata.id'], 'POST', {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PATCH
    def patch(self, ident):
        logging.info(f'SubscriptionAPI PATCH called: {ident}')
        raw_dict = request.get_json(force=True)
        try:
            resp = error_404_response(request.path)
            if ident in members:
                for field, value in raw_dict.items():
                    if field not in {'RegistryPrefixes', 'Destination', 'Context'}:
                        return 'Field %s is not patchable' % field, 400
                    else:
                        if field == 'RegistryPrefixes' and value != []:
                            if 'EventTypesForSubscription' in e_config:  # XD224 Paradise does not have this field
                                for evType in value:
                                    if evType not in e_config['EventTypesForSubscription']:
                                        return 'Invalid EventType %s' % evType, 400
                        members[ident][field] = value
                resp = success_response('PATCH request successful', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    def delete(self, ident):
        logging.info(f'SubscriptionAPI DELETE called: {ident}')
        try:
            resp = error_404_response(request.path)
            if ident in members:
                data_id = members[ident]['@odata.id']
                # s_config['Members'] are of the form
                # "Members": [
                #   { "@odata.id": "/redfish/v1/EventService/Subscriptions/1" },
                #   { "@odata.id": "/redfish/v1/EventService/Subscriptions/2" } ]
                for i in range(len(s_config['Members'])):
                    if data_id == s_config['Members'][i]['@odata.id']:
                        del s_config['Members'][i]
                        del members[ident]
                        s_config['Members@odata.count'] -= 1
                        resp = success_response('Resource deleted', 200)
                        break
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateEventService
#
# Called internally to create an instance of the EventService and initialize its subresources. This
# adds '/redfish/v1/EventService', '/redfish/v1/EventService/Subscriptions', and
# '/redfish/v1/EventService/Subscriptions/<string:ident>' resources to flask. These resources are
# affected by EventServiceAPI(), SubscriptionCollectionAPI(), and SubscriptionAPI()
def CreateEventService(event_config, sub_config, sub_generator):
    logging.info('CreateEventService put called')
    try:
        global e_config
        global s_config
        global s_generator
        e_config = event_config
        s_config = sub_config
        s_generator = sub_generator
        g.api.add_resource(EventServiceAPI,             '/redfish/v1/EventService')
        g.api.add_resource(SubscriptionCollectionAPI,   '/redfish/v1/EventService/Subscriptions')
        g.api.add_resource(SubscriptionAPI,             '/redfish/v1/EventService/Subscriptions/<string:ident>')
        resp = e_config, 200
    except Exception:
        traceback.print_exc()
        resp = simple_error_response('Server encountered an unexpected Error', 500)
    return resp

# CreateSubscription
#
# Called internally to create an instance of an event subscription resource for the EventService.
# This resource is affected by SubscriptionCollectionAPI() and SubscriptionAPI().
def CreateSubscription(ident, destination, event_types, context=None, registry_prefixes=None):
    logging.info('CreateSubscription called')
    wildcards = {}
    try:
        wildcards['id'] = ident
        config = s_generator(wildcards)
        config['Destination'] = destination
        config['EventTypes'] = event_types
        if context is not None:
            config['Context'] = context
        if registry_prefixes is not None:
            config['RegistryPrefixes'] = registry_prefixes
        members[ident] = config
        s_config['Members'].append({'@odata.id': config['@odata.id']})
        s_config['Members@odata.count'] += 1
        resp = config, 200
    except Exception:
        traceback.print_exc()
        resp = simple_error_response('Server encountered an unexpected Error', 500)
    return resp
