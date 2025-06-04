# System Storage Volume API File

"""
Dynamic resources:
 - System Volume API
    #     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}
    #     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes
    #     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes/{volume_id}
    #     POST /redfish/v1/Systems/{system_id}/Storage/{storage_id}
    #     DELETE /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes
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

members = {} # [storage_id] -> volumes
vol_res = {} # [storage_id][volume_id] -> volume resource

# Called internally to create an instance of the Volume resource.
# This resource is affected by VolumeActionsAPI()
class StorageVolumeCollectionAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('StorageVolumeCollections init called')
        self.allow = 'GET, POST'
        self.apiName = 'VolumesAPI'

    # HTTP GET
    # TODO: Add support for system_id
    def get(self, system_id, storage_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if storage_id in members:
                # If the power is off, return empty collection
                if not isPowerOn(system_id):
                    resp = error_404_response(request.path)
                else:
                    resp = members[storage_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP POST
    # TODO: Add support for system_id
    def post(self, system_id, storage_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            # Find the entry with the correct value for Id
            resp = error_404_response(request.path)
            if storage_id in members:
                raw_dict = request.get_json(force=True)
                logging.info(raw_dict)
                displayName = raw_dict['DisplayName']
                raid_type = raw_dict['RAIDType']
                drives = raw_dict['Links']['Drives']
                vol1 = {
                    '@odata.id': '/redfish/v1/Systems/1/Storage/{}/Volumes/1'.format(storage_id),
                    '@odata.type': "#Volume.v1_9_0.Volume",
                    'Id': '1',
                    'Name': '{}'.format(displayName),
                    'Status': {
                        'Health': 'OK',
                        'State': 'Enabled',
                    },
                    'Identifiers': [
                        {
                            'DurableName': '600508B1001CEF52B2316FD14DD0D135',
                            'DurableNameFormat': 'NAA'
                        }
                    ],
                    'Encrypted': False,
                    'CapacityBytes': 480070426624,
                    'BlockSizeBytes': 512,
                    'OptimumIOSizeBytes': 262144,
                    'StripSizeBytes': 262144,
                    'DisplayName': '{}'.format(displayName),
                    'RAIDType': '{}'.format(raid_type),
                    'VolumeUsage': 'Data',
                    'LogicalUnitNumber': 1,
                    'Links': {
                        'Drives@odata.count': len(drives),
                        'Drives': drives,
                    },
                    '@odata.etag': '\"7B474861\"'
                }

                # Set the Volume resource
                vol_res[storage_id] = {'1' : vol1}

                # update the Volumes Members
                # this replaces all members with the new volume
                members[storage_id]['Members'] = [{'@odata.id': '/redfish/v1/Systems/1/Storage/{}/Volumes/1'.format(storage_id)}]

                # remove Actions from /redfish/v1/Systems/1/Chassis/<chassis_id>/Drives/<drive_id>
                # this is needed so this drive is not allowed to run secure erase.
                chassisMemberDrives = getChassisMemberDrives()
                for drive in drives:
                    drive_id = drive['@odata.id'].replace('/redfish/v1/Chassis/{}/Drives/'.format(storage_id), '')
                    # remove the actions from the drive
                    ident = storage_id + "_" + drive_id
                    chassisMemberDrives[ident]['Actions'] = {}

            return members[storage_id], 200

        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP PUT
    # TODO: Add support for system_id
    def put(self, system_id, storage_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if storage_id in members:
                resp = error_not_allowed_response(request.path, request.method, {'Allow': self.allow})
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

# InitVolumes
# Called internally to init Volumes.  These resources are affected by VolumeActionsAPI()
#
# TODO: Add support for system_id
def InitVolumes(storage_id, volumes):
    logging.info('CreateVolumes called')
    try:
        # Create a new Volumes resource
        members[storage_id] = volumes

        return members[storage_id], 200
    except Exception:
        traceback.print_exc()
        return simple_error_response('Server encountered an unexpected Error', 500)

class StorageVolumeAPI(Resource):
    # Set authorization levels here. You can either list all of the
    # privileges needed for access or just the highest one.
    method_decorators = {'get':    [auth.auth_required(priv={Privilege.Login})],
                         'post':   [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'put':    [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'patch':  [auth.auth_required(priv={Privilege.ConfigureComponents})],
                         'delete': [auth.auth_required(priv={Privilege.ConfigureComponents})]}
    def __init__(self, **kwargs):
        logging.info('VolumeAPI init called')
        self.allow = 'GET', 'DELETE'
        self.apiName = 'VolumeAPI'

    # HTTP GET
    # TODO: Add support for system_id
    def get(self, system_id, storage_id, volume_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if storage_id in vol_res and volume_id in vol_res[storage_id]:
               resp = vol_res[storage_id][volume_id], 200
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp

    # HTTP DELETE
    # TODO: Add support for system_id
    def delete(self, system_id, storage_id, volume_id):
        logging.info('%s %s called' % (self.apiName, request.method))
        try:
            resp = error_404_response(request.path)
            if storage_id in vol_res and volume_id in vol_res[storage_id]:
                # Remove the Volume from the Volumes collection
                vol_id = vol_res[storage_id][volume_id]['@odata.id']
                # members['Members'] are of the form
                # "Members": [ { "@odata.id": '/redfish/v1/Systems/1/Storage/1/Volumes/1' } ]
                for i in range(len(members[storage_id]['Members'])):
                    if vol_id == members[storage_id]['Members'][i]['@odata.id']:
                        del members[storage_id]['Members'][i]
                        members[storage_id]['Members@odata.count'] -= 1
                        break

                # restore the actions to the drives
                chassisMemberDrives = getChassisMemberDrives()
                for drive in vol_res[storage_id][volume_id]['Links']['Drives']:
                    drive_id = drive['@odata.id'].replace('/redfish/v1/Chassis/{}/Drives/'.format(storage_id), '')
                    # restore the actions
                    ident = storage_id + "_" + drive_id
                    chassisMemberDrives[ident]['Actions'] = {
                        "#Drive.SecureErase": {
                            "target": "/redfish/v1/Chassis/{}/Drives/{}/Actions/Drive.SecureErase".format(storage_id, drive_id)
                        }
                    }

                # Remove the Volume from the internal Storage collection
                del vol_res[storage_id][volume_id]

                resp = success_response('Volume deleted successfully', 200)
            else:
                resp = error_404_response(request.path)
        except Exception:
            traceback.print_exc()
            resp = simple_error_response('Server encountered an unexpected Error', 500)
        return resp
