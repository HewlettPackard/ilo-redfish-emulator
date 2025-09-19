# System Storage API for Redfish

"""
Dynamic resources:
 - System Storage API
    #     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}
 - System Storage Drive Secure Erase
    GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Drives/{drive_id}
    POST /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Drives/{drive_id}/Actions/Drive.SecureErase
"""
from threading import Thread

import g
import time
import sys, traceback
import logging
import copy
from flask import Flask, request, make_response, render_template
from flask_restful import reqparse, Api, Resource
from .redfish_auth import auth, Privilege
from .computer_system_api import isPowerOn
from .response import (success_response, simple_error_response, error_404_response, error_400_response,
                       error_not_allowed_response)

members = {} # [system_id + "_" + storage_id] -> storage instance data

members_drives = {} # [<system_id>_<storage_id>_<drive_id>] -> drive
members_se_thread = {} # [<system_id>_<storage_id>_<drive_id>] -> secure erase thread

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
def InitSystemStorageInstance(resource_dict, system_id, storage_id, storage):
    """
    Initialize storage data for the specified system storage.
    This method should be called to populate the storage information.
    """
    # Load storage data from a source (e.g., database, file, etc.)
    ident = system_id + "_" + storage_id
    members[ident] = storage
    logging.info(f'Storage data initialized for system {system_id}, storage {storage_id}')

    if 'Drives' in storage:
        for drive_odata in storage['Drives']:
            drive_id = drive_odata['@odata.id'].split('/')[-1]
            drive = resource_dict.get_resource('/redfish/v1/Systems/{0}/Storage/{1}/Drives/{2}'.format(system_id, storage_id, drive_id))
            #resource_dict['/redfish/v1/Systems/{0}/Storage/{1}/Drives/{2}/Actions/Drive.SecureErase'.format(system_id, storage_id, drive_id)] = 'api_emulator.redfish.system_storage_instance_api.DriveSecureEraseActionAPI'
            InitSystemStorageDrive(system_id, storage_id, drive_id, drive)

# StorageSecureEraseWorker
#
# Worker thread for performing emulated asynchronous secure erase operations.
#
class StorageSecureEraseWorker(Thread):
    def __init__(self, system_id, storage_id, drive_id):
        super(StorageSecureEraseWorker, self).__init__()
        self.system_id = system_id
        self.storage_id = storage_id
        self.drive_id = drive_id

    def run(self):
        ident = self.system_id + "_" + self.storage_id + "_" + self.drive_id
        members_drives[ident]['Status']['State'] = 'INPROGRESS'
        members_drives[ident]['Operations'] = [
            {
                'Name': 'Sanitize',
                'PercentageComplete': 10,
            }
        ]
        # Simulate a long-running secure erase operation
        # In a real implementation, this would involve actual hardware operations.
        time.sleep(g.async_sleep)  # Simulate a async secure erase operation
        members_drives[ident]['Status']['State'] = 'COMPLETE'
        members_drives[ident]['Operations'] = [
            {
                'Name': 'Sanitize',
                'PercentageComplete': 100,
            }
        ]

class StorageDriveSecureEraseActionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('SecureEraseActionAPI init called')
        self.allow = 'POST'
        self.apiName = 'SecureEraseActionAPI'

    # HTTP GET
    def get(self, system_id, storage_id, drive_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            ident = system_id + "_" + storage_id + "_" + drive_id
            if ident in members_drives:
                member = members_drives[ident]
                resp = member, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    def post(self, system_id, storage_id, drive_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            ident = system_id + "_" + storage_id + "_" + drive_id
            if ident in members_drives:
                if members_se_thread[ident] is not None and members_se_thread[ident].is_alive():
                    # Ignore other power actions if we have a pending thread.
                    logging.info('Thread is running. Ignoring request')
                else:
                    # Create a new thread for the secure erase operation
                    members_se_thread[ident] = StorageSecureEraseWorker(system_id, storage_id, drive_id)
                    members_se_thread[ident].run()
                    resp = success_response('Secure Erase operation started successfully', 200)
            else:
                resp = error_404_response(request.path)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

class SystemStorageDriveAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}

    def __init__(self, **kwargs):
        logging.info('SystemStorageDriveAPI init called')
        self.allow = 'GET'
        self.apiName = 'SystemStorageDriveAPI'

    # HTTP GET
    def get(self, system_id, storage_id, drive_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            ident = system_id + "_" + storage_id + "_" + drive_id
            if ident in members_drives:
                member = members_drives[ident]
                resp = member, 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# InitSystemStorageDrive
# Called internally to init System Storage Drive.  These resources are affected by SecureEraseActionAPI()
def InitSystemStorageDrive(system_id, storage_id, drive_id, drive):
    logging.info('InitSystemStorageDrive called')
    try:
        # Create a new System Storge Drive resource
        ident = system_id + "_" + storage_id + "_" + drive_id
        members_drives[ident] = drive
        members_se_thread[ident] = None  # Initialize the thread to None

        return members_drives[ident], 200
    except Exception:
        traceback.print_exc()
        return simple_error_response('Server encountered an unexpected Error', 500)

