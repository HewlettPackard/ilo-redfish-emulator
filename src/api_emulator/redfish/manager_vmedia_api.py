# Manager Virtual Media API File

"""
Dynamic resources:
 - Manager Virtual Media
 #     GET /redfish/v1/Managers/{manager_id}/VirtualMedia
 #     POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.InsertMedia
 #     POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.EjectMedia
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

# VirtualMedia
#
# This is the Virtual Media resource. It is used to manage the virtual media
# for a manager. It is used to mount and unmount virtual media.
class VirtualMediaAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('VirtualMediaAPI init called')
        self.allow = 'GET, POST'
        self.apiName = 'VirtualMediaAPI'

    # HTTP GET
    def get(self, vmedia_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if vmedia_id in members:
                member = members[vmedia_id]
                resp = member, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, vmedia_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if vmedia_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    def put(self, vmedia_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if vmedia_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# CreateVirtualMedia
# Called internally to create an instance of a VirtualMedia.  These resources are affected by VirtualMediaAvtionAPI()
#
def CreateVirtualMedia(vmedia_id, vmedia):
    logging.info('CreateVirtualMedia called')
    try:
        # Create a new VirtualMedia resource
        members[vmedia_id] = vmedia

        return members[vmedia_id], 200
    except Exception:
        traceback.print_exc()
        return simple_error_response('Server encountered an unexpected Error', 500)

# VirtualMediaEject
#
# This services POST requests for ejecting media from a virtual media device.
#
class VirtualMediaEjectAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'post': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('VirtualMediaEjectMediaAPI init called')
        self.allow = 'POST'
        self.apiName = 'VirtualMediaEjectMediaAPI'

    # HTTP POST
    def post(self, vmedia_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if vmedia_id in members:
                # Eject the media
                members[vmedia_id]['Inserted'] = False
                members[vmedia_id]['Image'] = ""
                resp = success_response('Media ejected successfully', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# VirtualMediaInsert
#
# This services POST requests for inserting media into a virtual media device.
#
class VirtualMediaInsertAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'post': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('VirtualMediaInsertMediaAPI init called')
        self.allow = 'POST'
        self.apiName = 'VirtualMediaInsertMediaAPI'

    # HTTP POST
    def post(self, vmedia_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        raw_dict = request.get_json(force=True)
        iso = raw_dict.get('Image', None)
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if vmedia_id in members:
                # Insert the media
                members[vmedia_id]['Inserted'] = True
                members[vmedia_id]['Image'] = iso
                resp = success_response('Media inserted successfully', 200)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp
