# System Storage API for Redfish

"""
Dynamic resources:
 - System Storage API
    #     GET /redfish/v1/Systems/{system_id}/Storage
"""

import g
import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource
from .redfish_auth import auth, Privilege
from .chassis_api import getChassisMemberDrives
from .computer_system_api import isPowerOn
from .response import success_response, simple_error_response, error_404_response, error_not_allowed_response

members = {} # Dictionary to hold system storage members


class SystemStorageAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('System Storage init called')
        self.allow = 'GET'
        self.apiName = 'SystemStorageAPI'

    def get(self, system_id):
        if system_id not in members:
            return error_404_response('System not found', 404)

        # If the power is off, return empty collection
        if not isPowerOn(system_id):
            empty_members = {
                '@odata.context': '/redfish/v1/$metadata#StorageCollection.StorageCollection',
                '@odata.id': '/redfish/v1/Systems/'+system_id+'/Storage',
                '@odata.type': '#StorageCollection.StorageCollection',
                'Name': 'Storage',
                'Description': 'Storage subsystems known to this system',
                'Members': [],
                'Members@odata.count': 0
            }
            storage_info = empty_members
        else:
            storage_info = members[system_id]

        return storage_info, 200

# Init method to load storage data
def InitStorage(system_id, storage):
    """
    Initialize storage data for the specified system.
    This method should be called to populate the storage information.
    """
    # Load storage data from a source (e.g., database, file, etc.)
    members[system_id] = storage
    logging.info(f'Storage data initialized for system {system_id}')



