# System Storage API for Redfish

"""
Dynamic resources:
 - System Storage API
    #     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}
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
from .response import (success_response, simple_error_response, error_404_response, error_400_response,
                       error_not_allowed_response)

members = {} # [system_id + "_" + storage_id] -> storage instance data

class SystemStorageInstanceAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('System Storage Instance init called')
        self.allow = 'GET'
        self.apiName = 'SystemStorageInstanceAPI'

    def get(self, system_id, storage_id):
        ident = system_id + "_" + storage_id
        if ident not in members:
            return error_404_response('System storage not found', 404)

        # If the power is off, return ResourceNotReady error
        if not isPowerOn(system_id):
            return error_400_response()
        return members[ident], 200

# Init method to load storage data
def InitSystemStorageInstance(system_id, storage_id, storage):
    """
    Initialize storage data for the specified system storage.
    This method should be called to populate the storage information.
    """
    # Load storage data from a source (e.g., database, file, etc.)
    ident = system_id + "_" + storage_id
    members[ident] = storage
    logging.info(f'Storage data initialized for system {system_id}, storage {storage_id}')



