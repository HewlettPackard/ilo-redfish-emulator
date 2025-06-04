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

# Generic Static Mockup and Dynamic Resource Loader

import g
import logging
import re
import strgen
import random

# Resource and SubResource imports
from .redfish.computer_system_api import ComputerSystemAPI, CreateComputerSystem, ResetAction_API
from .redfish.chassis_api import (ChassisAPI, InitChassis, ChassisResetActionAPI, InitChassisDrive,
                                  DriveSecureEraseActionAPI, ChassisDriveAPI)
from .redfish.manager_api import ManagerAPI, CreateManager, ManagerResetActionAPI
from .redfish.update_service_api import UpdateServiceAPI, CreateFirmwareTarget, SimpleUpdateAPI, UpdateServiceConfigAPI
from .redfish.templates.subscriptions import get_subscription_instance
from .redfish.event_generator import EventGenerator
from .redfish.event_service_api import CreateEventService
from .redfish.account_service_api import CreateAccountService, CreateAccount, AccountCollectionAPI, AccountAPI
from .redfish.session_service_api import CreateSessionService, SessionCollectionAPI, SessionAPI
from .redfish.manager_network_protocol_api import ManagerNetworkProtocolAPI, CreateNetworkProtocol
from .redfish.manager_vmedia_api import (VirtualMediaAPI, VirtualMediaEjectAPI, VirtualMediaInsertAPI,
                                         CreateVirtualMedia)
from .redfish.system_storage_api import (SystemStorageAPI, InitStorage)
from .redfish.system_storage_instance_api import (SystemStorageInstanceAPI, InitSystemStorageInstance)
from .redfish.system_storage_volume_api import (StorageVolumeCollectionAPI, InitVolumes, StorageVolumeAPI)

import api_emulator.redfish.power_control_api as generic_power
import api_emulator.redfish.hpe_cray_ex_power_control_api as hpe_cray_ex_power
import api_emulator.redfish.proliant_ilo_power_control_api as ilo_power
import api_emulator.redfish.hpe_cray_ex_certificate_service_api as hpe_cray_ex_cert
# import api_emulator.redfish.proliant_ilo_certificate_service_api as ilo_cert
import api_emulator.redfish.templates.events as generic_events
import api_emulator.redfish.templates.hpe_cray_ex_events as hpe_cray_ex_events
import api_emulator.redfish.templates.proliant_ilo_events as ilo_events
import api_emulator.redfish.templates.gigabyte_events as gb_events
import api_emulator.redfish.templates.intel_events as intel_events

# GenericCustom
#
# Called to build the static resources to emulate a custom redfish device.
#
# - The custom static files live in api_emulator/redfish/static/<MyBMC>
# - Dynamic recource files live in api_emulator/redfish/<dynamic_resource>_api.py
# - Templates for event schemas live in api_emulator/redfish/templates/<schema>_events.py
#
# Dynamic resources:
# - Power Capping
#     GET/PATCH /redfish/v1/Chassis/{sys_id}/Power - Generic Power Limit Schema
#
#     GET/PATCH /redfish/v1/Chassis/{sys_id}/Controls/{control_id} - HPE Cray EX Power Limit Schema
#     PATCH     /redfish/v1/Chassis/{sys_id}/Controls.Deep - HPE Cray EX Power Limit Schema
#
#     GET  /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit - Apollo 6500 Power Limit Schema
#     POST /redfish/v1/Chassis/{sys_id}/Power/AccPowerService/PowerLimit/Actions/HpeServerAccPowerLimit.ConfigurePowerLimit
# - System Power Actions
#     GET /redfish/v1/Systems/{system_id}
#     GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
# - Chassis Power Actions
#     GET      /redfish/v1/Chassis/{chassis_id}
#     GET/POST /redfish/v1/Chassis/{chassis_id}/Actions/Chassis.Reset
# - Manager Power Actions
#     GET      /redfish/v1/Managers/{manager_id}
#     GET/POST /redfish/v1/Managers/{manager_id}/Actions/Manager.Reset
# - Firmware Update
#     GET       /redfish/v1/UpdateService/FirmwareInventory/{target_id}
#     POST      /redfish/v1/UpdateService/SimpleUpdate
#     GET/PATCH /redfish/v1/UpdateService/FirmwareInventory/Config
# - Event Service
#     GET/PATCH        /redfish/v1/EventService
#     GET/POST         /redfish/v1/EventService/Subscriptions
#     GET/PATCH/DELETE /redfish/v1/EventService/Subscriptions/{sub_id}
# - Account Service
#     GET/POST         /redfish/v1/AccountService/Accounts
#     GET/PATCH/DELETE /redfish/v1/AccountService/Accounts/{id}
# - Session Service
#     GET/POST   /redfish/v1/SessionService/Sessions
#     GET/DELETE /redfish/v1/AccountService/Sessions/{id}
# - Certificate Service
#     POST /redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate
# - Manager Network Protocol
#     GET/PATCH /redfish/v1/Managers/{manager_id}/NetworkProtocol
#
# ------ newly added in BMI Redfish Interface Emulator ------
# - System Actions
#     GET/PATCH /redfish/v1/Systems/{system_id}
# - Manager Virtual Media
#     GET /redfish/v1/Managers/{manager_id}/VirtualMedia
#     POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.InsertMedia
#     POST /redfish/v1/Managers/{manager_id}/VirtualMedia/{vmedia_id}/Actions/VirtualMedia.EjectMedia
# - Chassis Drive Secure Erase
#     GET /redfish/v1/Chassis/{chassis_id}/Drives/{drive_id}
#     POST /redfish/v1/Chassis/{chassis_id}/Drives/{drive_id}/Actions/Drive.SecureErase
# - System Volume API
#     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}
#     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes
#     GET /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes/{volume_id}
#     POST /redfish/v1/Systems/{system_id}/Storage/{storage_id}
#     DELETE /redfish/v1/Systems/{system_id}/Storage/{storage_id}/Volumes
class Loader:

    def __init__(self, resource_dictionary, config_data, bmcType='Generic'):
        logging.info('Generic init called for type, %s' % bmcType)
        self.BMC_Type = bmcType
        self.resource_dictionary = resource_dictionary

        if 'xname' in config_data:
            self.xname = config_data['xname']
            self.fru_random_seed = self.xname
        else:
            self.xname = 'x0c0s0b0'
            self.fru_random_seed = None

        if 'mac_schema' in config_data:
            self.mac_schema = config_data['mac_schema']
        else:
            self.mac_schema = 'Random'

        self.randomize()

        # Add dynamic resources here. This will override any previously loaded static URL
        self.init_power_limit()
        self.init_system()
        self.init_chassis()
        self.init_manager_reset()
        self.init_update_service()
        self.init_event_service()
        self.init_account_service()
        self.init_session_service()
        self.init_cert_service()
        self.init_manager_network_protocol()
        self.init_manager_virtual_media()
        self.init_system_storage()
        self.init_chassis_drive()

    def init_power_limit(self):
        try:
            chassisCollection = self.resource_dictionary.get_resource('Chassis')
            if len(chassisCollection['Members']) == 0:
                # Found chassis collection with no members. Don't create a dynamic resource.
                return
        except:
            return
        #
        # Power Capping
        #
        # Try to detect the power limit schema.
        is_hpe_cray_ex_power = False
        is_hpe_ilo_power = False
        is_generic_power = False
        power_limit_schema = ''
        for chassis in chassisCollection['Members']:
            ch_id = chassis['@odata.id'].replace('/redfish/v1/Chassis/', '')
            ch_config = self.resource_dictionary.get_resource('Chassis/%s' % ch_id)
            if 'Controls' in ch_config:
                is_hpe_cray_ex_power = True
                pwrControls = self.resource_dictionary.get_resource('Chassis/%s/Controls' % ch_id)
                for pwrControl in pwrControls['Members']:
                    control_id = pwrControl['@odata.id'].replace('/redfish/v1/Chassis/%s/Controls/' % ch_id, '')
                    config = self.resource_dictionary.get_resource('Chassis/%s/Controls/%s' % (ch_id, control_id))
                    hpe_cray_ex_power.CreatePower(ch_id, control_id, config)
            elif 'Power' in ch_config:
                power = self.resource_dictionary.get_resource('Chassis/%s/Power' % ch_id)
                if 'PowerControl' in power and len(power['PowerControl']) > 0:
                    try:
                        power_config = self.resource_dictionary.get_resource('Chassis/%s/Power/AccPowerService/PowerLimit' % ch_id)
                        is_hpe_ilo_power = True
                        ilo_power.CreatePower(ch_id, power_config)
                    except:
                        is_generic_power = True
                        generic_power.CreatePower(ch_id, power)
        # Add the callbacks
        if is_generic_power:
            logging.info('Detected power limit schema is Generic')
            g.api.add_resource(generic_power.PowerAPI, '/redfish/v1/Chassis/<string:ch_id>/Power')
        elif is_hpe_cray_ex_power:
            logging.info('Detected power limit schema is HPE Cray EX')
            g.api.add_resource(hpe_cray_ex_power.PowerAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls/<string:ident>')
            g.api.add_resource(hpe_cray_ex_power.ControlsDeepAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls.Deep')
        elif is_hpe_ilo_power:
            logging.info('Detected power limit schema is HPE iLO')
            g.api.add_resource(ilo_power.AccPowerServiceAPI, '/redfish/v1/Chassis/<string:ch_id>/Power/AccPowerService/PowerLimit')
            g.api.add_resource(ilo_power.ActionAPI, '/redfish/v1/Chassis/<string:ch_id>/Power/AccPowerService/PowerLimit/Actions/HpeServerAccPowerLimit.ConfigurePowerLimit')

    def init_system(self):
        try:
            systems = self.resource_dictionary.get_resource('Systems')
            if len(systems['Members']) == 0:
                # Found systems collection with no members. Don't create a dynamic resource.
                return
        except:
            return
        #
        # System Reset Actions
        #
        found_system = False
        found_reset = False
        for system in systems['Members']:
            found_system = True
            sys_id = system['@odata.id'].replace('/redfish/v1/Systems/', '')
            config = self.resource_dictionary.get_resource('Systems/' + sys_id)
            if 'Actions' in config and '#ComputerSystem.Reset' in config['Actions']:
                rst_actions = []
                if 'ResetType@Redfish.AllowableValues' in config['Actions']['#ComputerSystem.Reset']:
                    rst_actions = config['Actions']['#ComputerSystem.Reset']['ResetType@Redfish.AllowableValues']
                else:
                    try:
                        actionInfo = self.resource_dictionary.get_resource('Systems/%s/ResetActionInfo' % sys_id)
                        rst_actions = actionInfo['Parameters'][0]['AllowableValues']
                    except:
                        logging.info('Using default reset actions for Systems/%s' % sys_id)
                CreateComputerSystem(sys_id, config, rst_actions)
                found_reset = True
        if found_system:
            g.api.add_resource(ComputerSystemAPI, '/redfish/v1/Systems/<string:ident>')
        if found_reset:
            g.api.add_resource(ResetAction_API, '/redfish/v1/Systems/<string:ident>/Actions/ComputerSystem.Reset')

    def init_chassis(self):
        try:
            collection = self.resource_dictionary.get_resource('Chassis')
            if len(collection['Members']) == 0:
                # Found chassis collection with no members. Don't create a dynamic resource.
                return
        except:
            return
        #
        # Chassis Reset Actions
        #
        found_chassis = False
        found_reset = False
        for member in collection['Members']:
            found_chassis = True
            id = member['@odata.id'].replace('/redfish/v1/Chassis/', '')
            config = self.resource_dictionary.get_resource('Chassis/' + id)
            rst_actions = []
            if 'Actions' in config and '#Chassis.Reset' in config['Actions']:
                if 'ResetType@Redfish.AllowableValues' in config['Actions']['#Chassis.Reset']:
                    rst_actions = config['Actions']['#Chassis.Reset']['ResetType@Redfish.AllowableValues']
                else:
                    try:
                        actionInfo = self.resource_dictionary.get_resource('Chassis/%s/ResetActionInfo' % id)
                        rst_actions = actionInfo['Parameters'][0]['AllowableValues']
                    except:
                        logging.info('Using default reset actions for Chassis/%s' % id)
                found_reset = True
            InitChassis(id, config, rst_actions)
        if found_chassis:
            g.api.add_resource(ChassisAPI, '/redfish/v1/Chassis/<string:chassis_id>')
        if found_reset:
            g.api.add_resource(ChassisResetActionAPI, '/redfish/v1/Chassis/<string:chassis_id>/Actions/Chassis.Reset')

    def init_manager_reset(self):
        try:
            collection = self.resource_dictionary.get_resource('Managers')
            if len(collection['Members']) == 0:
                # Found Managers collection with no members. Don't create a dynamic resource.
                return
        except:
            return
        #
        # Manager Reset Actions
        #
        found = False
        for member in collection['Members']:
            id = member['@odata.id'].replace('/redfish/v1/Managers/', '')
            config = self.resource_dictionary.get_resource('Managers/' + id)
            if 'Actions' in config and '#Manager.Reset' in config['Actions']:
                rst_actions = []
                if 'ResetType@Redfish.AllowableValues' in config['Actions']['#Manager.Reset']:
                    rst_actions = config['Actions']['#Manager.Reset']['ResetType@Redfish.AllowableValues']
                else:
                    try:
                        actionInfo = self.resource_dictionary.get_resource('Managers/%s/ResetActionInfo' % id)
                        rst_actions = actionInfo['Parameters'][0]['AllowableValues']
                    except:
                        logging.info('Using default reset actions for Managers/%s' % id)
                CreateManager(id, config, rst_actions)
                found = True
        if found:
            g.api.add_resource(ManagerResetActionAPI, '/redfish/v1/Managers/<string:ident>/Actions/Manager.Reset')

    def init_update_service(self):
        try:
            updateService = self.resource_dictionary.get_resource('UpdateService/FirmwareInventory')
            # Found Update Service
        except:
            return
        #
        # Firmware Update
        #
        g.api.add_resource(UpdateServiceAPI, '/redfish/v1/UpdateService/FirmwareInventory/<string:ident>')
        g.api.add_resource(SimpleUpdateAPI, '/redfish/v1/UpdateService/SimpleUpdate')
        for member in updateService['Members']:
            target_id = member['@odata.id'].replace('/redfish/v1/UpdateService/FirmwareInventory/', '')
            config = self.resource_dictionary.get_resource('UpdateService/FirmwareInventory/' + target_id)
            CreateFirmwareTarget(target_id, config)

        # Firmware Update Configurations
        g.api.add_resource(UpdateServiceConfigAPI, '/redfish/v1/UpdateService/FirmwareInventory/Config')

    def init_event_service(self):
        try:
            eventService = self.resource_dictionary.get_resource('EventService')
            # Found Event Service
        except:
            return
        #
        # Event Service
        #
        sub_config = self.resource_dictionary.get_resource('EventService/Subscriptions')
        # Remove any existing subscriptions in our static mockup
        sub_config['Members'] = []
        sub_config['Members@odata.count'] = 0
        sub_generator = get_subscription_instance
        CreateEventService(eventService, sub_config, sub_generator)

        self.get_event_template()

        # Here we tell the event generator what templates to use for forming
        # redfish events. Since not all BMC types form events the same way.
        # eventTemplates = GetEventRecordTemplates()
        eventTemplates = self.get_event_template()
        EventGenerator(eventTemplates)

    def init_account_service(self):
        try:
            accountService = self.resource_dictionary.get_resource('AccountService/Accounts')
            # Found Account Service
        except:
            return
        #
        # Account Service
        #
        g.api.add_resource(AccountCollectionAPI, '/redfish/v1/AccountService/Accounts')
        g.api.add_resource(AccountAPI, '/redfish/v1/AccountService/Accounts/<string:ident>')
        account_schema = ''
        for member in accountService['Members']:
            account_id = member['@odata.id'].replace('/redfish/v1/AccountService/Accounts/', '')
            config = self.resource_dictionary.get_resource('AccountService/Accounts/' + account_id)
            account_schema = config['@odata.type']
            CreateAccount(account_id, config)
        CreateAccountService(accountService, account_schema)

    def init_session_service(self):
        try:
            sessionService = self.resource_dictionary.get_resource('SessionService/Sessions')
            # Found Session Service
        except:
            return
        #
        # Session Service
        #
        g.api.add_resource(SessionCollectionAPI, '/redfish/v1/SessionService/Sessions')
        g.api.add_resource(SessionAPI, '/redfish/v1/SessionService/Sessions/<string:ident>')
        sessionService = self.resource_dictionary.get_resource('SessionService/Sessions')
        # Remove any existing sessions in our static mockup
        sessionService['Members'] = []
        sessionService['Members@odata.count'] = 0
        CreateSessionService(sessionService)

    def init_cert_service(self):
        #
        # Certificate Service
        #
        is_hpe_cray_ex_cert = False
        is_proliant_ilo_cert = False
        try:
            certService = self.resource_dictionary.get_resource('CertificateService')
        except:
            return
        try:
            # Determine if this is the HPE Cray EX Certificate Service
            certCollection = self.resource_dictionary.get_resource('Managers/BMC/NetworkProtocol/HTTPS/Certificates')
            if '#CertificateService.ReplaceCertificate' in certService['Actions']:
                is_hpe_cray_ex_cert = True
                # Found HPE Cray EX Certificate Service
        except:
            pass
        if not is_hpe_cray_ex_cert:
            try:
                # Determine if this is the proliant iLO Certificate Service
                securityService = self.resource_dictionary.get_resource('Managers/1/SecurityService/HttpsCert')
                if '#HpeHttpsCert.ImportCertificate' in securityService['Actions']:
                    is_proliant_ilo_cert = True
            except:
                pass
        if is_hpe_cray_ex_cert:
            g.api.add_resource(hpe_cray_ex_cert.ReplaceCertificateAPI, '/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate')
            certCollection = self.resource_dictionary.get_resource('Managers/BMC/NetworkProtocol/HTTPS/Certificates')
            for member in certCollection['Members']['Certificates']:
                cert_id = member['@odata.id'].replace('/redfish/v1/Managers/BMC/NetworkProtocol/HTTPS/Certificates/', '')
                cert_config = self.resource_dictionary.get_resource('Managers/BMC/NetworkProtocol/HTTPS/Certificates/%s' % cert_id)
                hpe_cray_ex_cert.CreateCert(cert_id, cert_config)
        elif is_proliant_ilo_cert:
            # TODO: Add this schema
            pass

    def init_manager_network_protocol(self):
        #
        # Manager Network Protocol
        #
        found_network_protocol = False
        try:
            collection = self.resource_dictionary.get_resource('Managers')
            for member in collection['Members']:
                manager_id = member['@odata.id'].replace('/redfish/v1/Managers/', '')
                manager = self.resource_dictionary.get_resource('Managers/%s' % manager_id)
                if 'NetworkProtocol' in manager:
                    found_network_protocol = True
                    config = self.resource_dictionary.get_resource('Managers/%s/NetworkProtocol' % manager_id)
                    CreateNetworkProtocol(manager_id, config)
        except:
            return
        if found_network_protocol:
            g.api.add_resource(ManagerNetworkProtocolAPI, '/redfish/v1/Managers/<string:m_id>/NetworkProtocol')

    def init_manager_virtual_media(self):
        try:
            managers = self.resource_dictionary.get_resource('Managers')
            if len(managers['Members']) == 0:
                # Found managers collection with no members. Don't create a dynamic resource.
                return
        except:
            return

        try:
            for member in managers['Members']:
                manager_id = member['@odata.id'].replace('/redfish/v1/Managers/', '')
                manager = self.resource_dictionary.get_resource('Managers/%s' % manager_id)
                if 'VirtualMedia' in manager:
                    vmedia = self.resource_dictionary.get_resource('Managers/%s/VirtualMedia' % manager_id)
                    for vmedia_member in vmedia['Members']:
                        vmedia_id = vmedia_member['@odata.id'].replace('/redfish/v1/Managers/%s/VirtualMedia/' % manager_id, '')
                        vmedia_inst = self.resource_dictionary.get_resource('Managers/%s/VirtualMedia/%s' % (manager_id, vmedia_id))
                        CreateVirtualMedia(vmedia_id, vmedia_inst)
                        g.api.add_resource(VirtualMediaAPI, '/redfish/v1/Managers/'+manager_id+'/VirtualMedia/<string:vmedia_id>')
                        g.api.add_resource(VirtualMediaEjectAPI, '/redfish/v1/Managers/'+manager_id+'/VirtualMedia/<string:vmedia_id>/Actions/VirtualMedia.EjectMedia')
                        g.api.add_resource(VirtualMediaInsertAPI, '/redfish/v1/Managers/'+manager_id+'/VirtualMedia/<string:vmedia_id>/Actions/VirtualMedia.InsertMedia')
        except:
           return

    def init_system_storage(self):
        try:
            systems = self.resource_dictionary.get_resource('Systems')
            if len(systems['Members']) == 0:
                # Found systems collection with no members. Don't create a dynamic resource.
                return
        except:
            return

        found_system_storage = False
        try:
            for sys_member in systems['Members']:
                system_id = sys_member['@odata.id'].replace('/redfish/v1/Systems/', '')
                storage = self.resource_dictionary.get_resource('Systems/' + system_id + '/Storage')
                InitStorage(system_id, storage)
                if len(storage['Members']) == 0:
                    continue

                for storage_member in storage['Members']:
                    found_system_storage = True
                    storage_id = storage_member['@odata.id'].replace('/redfish/v1/Systems/%s/Storage/' % system_id, '')
                    storage_inst = self.resource_dictionary.get_resource('Systems/%s/Storage/%s' % (system_id, storage_id))
                    InitSystemStorageInstance(system_id, storage_id, storage_inst)
                    volumes = self.resource_dictionary.get_resource('Systems/%s/Storage/%s/Volumes' % (system_id, storage_id))
                    InitVolumes(storage_id, volumes)
        except:
            return

        if found_system_storage:
            g.api.add_resource(SystemStorageAPI, '/redfish/v1/Systems/<string:system_id>/Storage')
            g.api.add_resource(SystemStorageInstanceAPI, '/redfish/v1/Systems/<string:system_id>/Storage/<string:storage_id>')
            g.api.add_resource(StorageVolumeCollectionAPI, '/redfish/v1/Systems/<string:system_id>/Storage/<string:storage_id>/Volumes')
            g.api.add_resource(StorageVolumeAPI, '/redfish/v1/Systems/<string:system_id>/Storage/<string:storage_id>/Volumes/<string:volume_id>')

    def init_chassis_drive(self):
        try:
            collection = self.resource_dictionary.get_resource('Chassis')
            if len(collection['Members']) == 0:
                # Found chassis collection with no members. Don't create a dynamic resource.
                return
        except:
            return
        #
        # Chassis Drive Actions
        #
        found = False
        for member in collection['Members']:
            chassis_id = member['@odata.id'].replace('/redfish/v1/Chassis/', '')
            chassis = self.resource_dictionary.get_resource('Chassis/' + chassis_id)
            if chassis['ChassisType'] == 'StorageEnclosure':
                drives = self.resource_dictionary.get_resource('Chassis/%s/Drives' % chassis_id)
                for drive_member in drives['Members']:
                    found = True
                    drive_id = drive_member['@odata.id'].replace('/redfish/v1/Chassis/%s/Drives/' % chassis_id, '')
                    drive = self.resource_dictionary.get_resource('Chassis/%s/Drives/%s' % (chassis_id, drive_id))
                    # Create the Drive resource
                    InitChassisDrive(chassis_id, drive_id, drive)

        if found:
            g.api.add_resource(ChassisDriveAPI, '/redfish/v1/Chassis/<string:chassis_id>/Drives/<string:drive_id>')
            g.api.add_resource(DriveSecureEraseActionAPI, '/redfish/v1/Chassis/<string:chassis_id>/Drives/<string:drive_id>/Actions/Drive.SecureErase')

    # Get the BMC type
    def get_type(self):
        return self.BMC_Type

    # Tries to determine if the event record schema is one of the known sets. Otherwise, use the generic.
    def get_event_template(self):
        while True:
            try:
                # Intel
                eventRegistry = self.resource_dictionary.get_resource('Registries/EventingMessages/Alert.1.0.0.json')
                templates = intel_events.GetEventRecordTemplates()
                logging.info('Using Intel redfish event schema')
                break
            except:
                pass
            try:
                # Gigabyte
                eventRegistry = self.resource_dictionary.get_resource('Registries/EventLog.1.0.0.json')
                templates = gb_events.GetEventRecordTemplates()
                logging.info('Using Gigabyte redfish event schema')
                break
            except:
                pass
            try:
                # HPE Cray EX
                eventRegistry = self.resource_dictionary.get_resource('Registries/CrayAlerts.1.0.0.json')
                templates = hpe_cray_ex_events.GetEventRecordTemplates()
                logging.info('Using HPE Cray EX redfish event schema')
                break
            except:
                pass
            try:
                # Proliant iLO
                eventRegistry = self.resource_dictionary.get_resource('Registries/iLOEvents')
                templates = ilo_events.GetEventRecordTemplates()
                logging.info('Using Proliant iLO redfish event schema')
                break
            except:
                pass
            templates = generic_events.GetEventRecordTemplates()
            logging.info('Using generic redfish event schema')
            break
        return templates

    def randomize(self):
        # By seeding the random number generated based off the BMC's xname (if set) will allow the
        # RIE instance to return build up the same data if the BMC is restarted.
        fru_random = random.Random(self.fru_random_seed)

        # List of all of the paths with serial numbers we want to randomize
        foundSNs = {}
        base = self.resource_dictionary.get_resource('')
        if 'Chassis' in base:
            chassisCollection = self.resource_dictionary.get_resource('Chassis')
            for member in chassisCollection['Members']:
                path = member['@odata.id'].replace('/redfish/v1/', '')
                chassis = self.resource_dictionary.get_resource(path)
                if 'SerialNumber' in chassis:
                    sn = chassis['SerialNumber']
                    if sn in foundSNs:
                        chassis['SerialNumber'] = foundSNs[sn]
                    else:
                        rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                        foundSNs[sn] = rndSN
                        chassis['SerialNumber'] = rndSN
                if 'Assembly' in chassis:
                    url = chassis['Assembly']['@odata.id'].replace('/redfish/v1/', '')
                    page = self.resource_dictionary.get_resource(url)
                    for assembly in page['Assemblies']:
                        if 'SerialNumber' in assembly:
                            sn = assembly['SerialNumber']
                            if sn in foundSNs:
                                assembly['SerialNumber'] = foundSNs[sn]
                            else:
                                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                                foundSNs[sn] = rndSN
                                assembly['SerialNumber'] = rndSN
                if 'NetworkAdapters' in chassis:
                    url = chassis['NetworkAdapters']['@odata.id'].replace('/redfish/v1/', '')
                    collection_page = self.resource_dictionary.get_resource(url)
                    if 'Members' in collection_page:
                        for memberUrl in collection_page['Members']:
                            url = memberUrl['@odata.id'].replace('/redfish/v1/', '')
                            page = self.resource_dictionary.get_resource(url)
                            if 'SerialNumber' in page:
                                sn = page['SerialNumber']
                                if sn in foundSNs:
                                    page['SerialNumber'] = foundSNs[sn]
                                else:
                                    rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                                    foundSNs[sn] = rndSN
                                    page['SerialNumber'] = rndSN
                if 'Power' in chassis:
                    url = chassis['Power']['@odata.id'].replace('/redfish/v1/', '')
                    power = self.resource_dictionary.get_resource(url)
                    if 'PowerSupplies' in power:
                        for power_supply in power["PowerSupplies"]:
                            if "SerialNumber" in power_supply:
                                sn = power_supply["SerialNumber"]
                                if sn not in foundSNs:
                                    rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                                    foundSNs[sn] = rndSN
                                power_supply['SerialNumber'] = foundSNs[sn]
                if 'Oem' in chassis:
                    if 'Hpe' in chassis['Oem']:
                        if 'Links' in chassis['Oem']['Hpe']:
                            if 'Devices' in chassis['Oem']['Hpe']['Links']:
                                url = chassis['Oem']['Hpe']['Links']['Devices']['@odata.id'].replace('/redfish/v1/', '')
                                collection_page = self.resource_dictionary.get_resource(url)
                                if 'Members' in collection_page:
                                    for memberUrl in collection_page['Members']:
                                        url = memberUrl['@odata.id'].replace('/redfish/v1/', '')
                                        page = self.resource_dictionary.get_resource(url)
                                        if 'SerialNumber' in page:
                                            sn = page['SerialNumber']
                                            if sn in foundSNs:
                                                page['SerialNumber'] = foundSNs[sn]
                                            else:
                                                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                                                foundSNs[sn] = rndSN
                                                page['SerialNumber'] = rndSN
        if 'Systems' in base:
            systems = self.resource_dictionary.get_resource('Systems')
            for i in range(len(systems['Members'])):
                member = systems['Members'][i]
            # for member in systems['Members']:
                path = member['@odata.id'].replace('/redfish/v1/', '')
                system = self.resource_dictionary.get_resource(path)
                if 'SerialNumber' in system:
                    sn = system['SerialNumber']
                    if sn in foundSNs:
                        system['SerialNumber'] = foundSNs[sn]
                    else:
                        rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                        foundSNs[sn] = rndSN
                        system['SerialNumber'] = rndSN
                for collection in ['Memory', 'Processors']:
                    if collection in system:
                        url = system[collection]['@odata.id'].replace('/redfish/v1/', '')
                        collection_page = self.resource_dictionary.get_resource(url)
                        for memberUrl in collection_page['Members']:
                            url = memberUrl['@odata.id'].replace('/redfish/v1/', '')
                            page = self.resource_dictionary.get_resource(url)
                            if 'SerialNumber' in page:
                                sn = page['SerialNumber']
                                if sn in foundSNs:
                                    page['SerialNumber'] = foundSNs[sn]
                                else:
                                    rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}', randomizer=fru_random).render()
                                    foundSNs[sn] = rndSN
                                    page['SerialNumber'] = rndSN
                if 'EthernetInterfaces' in system:
                    url = system['EthernetInterfaces']['@odata.id'].replace('/redfish/v1/', '')
                    collection_page = self.resource_dictionary.get_resource(url)
                    for memberUrl in collection_page['Members']:
                        url = memberUrl['@odata.id'].replace('/redfish/v1/', '')
                        page = self.resource_dictionary.get_resource(url)
                        if self.mac_schema == 'Mountain' and url.startswith("Managers/"):
                            # Only mountain BMCs have algorithmic MACs
                            fields = [int(s) for s in re.findall(r'-?\d+\.?\d*', self.xname)]
                            charFields = [s for s in re.findall(r'-?\D+\.?\D*', self.xname)]
                            # x3000c0s0b0
                            if len(charFields) > 3:
                                if charFields[2] == 's':
                                    fields[2] += 48
                                else:
                                    fields[2] += 96
                            else:
                                for num in range(4):
                                    if len(charFields) < num:
                                        fields.append(0)
                            rndMAC = [ 0x02,
                                (fields[0]>>8)&0xff,
                                fields[0]&0xff,
                                fields[1]&0xff,
                                fields[2]&0xff,
                                (fields[3]<<4)&0xff]
                        else:
                            rndMAC = [ 0x00, 0x40, 0xa6,
                                fru_random.randint(0x00, 0x7f),
                                fru_random.randint(0x00, 0xff),
                                fru_random.randint(0x00, 0xff)]
                        newMAC = ':'.join(map(lambda x: "%02x" % x, rndMAC))
                        if 'MACAddress' in page and re.match("[0-9a-f]{2}([-:]?)[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", page['MACAddress'].lower()):
                            page['MACAddress'] = newMAC
                            page['PermanentMACAddress'] = newMAC
