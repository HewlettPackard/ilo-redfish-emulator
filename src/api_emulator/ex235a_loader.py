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

# HPE Cray EX235a Static Mockup and Dynamic Resource Loader

import g
import logging
import strgen
import random
import re

# Resource and SubResource imports
from .loader import Loader
from .redfish.hpe_cray_ex_power_control_api import PowerAPI, CreatePower, ControlsDeepAPI
from .redfish.computer_system_api import ComputerSystemAPI, CreateComputerSystem, ResetAction_API
from .redfish.update_service_api import UpdateServiceAPI, CreateFirmwareTarget, SimpleUpdateAPI, UpdateServiceConfigAPI
from .redfish.templates.subscriptions import get_subscription_instance
from .redfish.templates.hpe_cray_ex_events import GetEventRecordTemplates
from .redfish.event_generator import EventGenerator
from .redfish.event_service_api import CreateEventService
from .redfish.account_service_api import CreateAccountService, CreateAccount, AccountCollectionAPI, AccountAPI
from .redfish.session_service_api import CreateSessionService, SessionCollectionAPI, SessionAPI
from .redfish.hpe_cray_ex_certificate_service_api import ReplaceCertificateAPI, CreateCert
from .redfish.manager_network_protocol_api import ManagerNetworkProtocolAPI, CreateNetworkProtocol

# EX235a
#
# Called to build the static and dynamic resources to emulate a EX235a Node.
#
# When merged with the Redfish-Interface-Emulator project:
# - EX235a static files live in api_emulator/redfish/static/EX235a
# - EX235a Dynamic API files live in api_emulator/redfish
# - This file will live in api_emulator
#
# Dynamic resources:
# - Power Capping
#     GET/PATCH /redfish/v1/Chassis/{sys_id}/Controls/{control_id}
# - System Power Actions
#     GET      /redfish/v1/Systems/{sys_id}
#     GET/POST /redfish/v1/Systems/{sys_id}/Actions/ComputerSystem.Reset
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
class EX235a(Loader):

    def __init__(self, resource_dictionary, config_data):
        logging.info('EX235a init called')
        config_data['mac_schema'] = 'Mountain'
        super().__init__(resource_dictionary, config_data, 'EX235a')

    def init_power_limit(self):
        #
        # Power Capping
        #
        g.api.add_resource(PowerAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls/<string:ident>')
        g.api.add_resource(ControlsDeepAPI, '/redfish/v1/Chassis/<string:ch_id>/Controls.Deep')
        chassisCollection = self.resource_dictionary.get_resource('Chassis')
        for chassis in chassisCollection['Members']:
            ch_id = chassis['@odata.id'].replace('/redfish/v1/Chassis/', '')
            ch_config = self.resource_dictionary.get_resource('Chassis/%s' % ch_id)
            if 'Controls' in ch_config:
                pwrControls = self.resource_dictionary.get_resource('Chassis/%s/Controls' % ch_id)
                for pwrControl in pwrControls['Members']:
                    control_id = pwrControl['@odata.id'].replace('/redfish/v1/Chassis/%s/Controls/' % ch_id, '')
                    config = self.resource_dictionary.get_resource('Chassis/%s/Controls/%s' % (ch_id, control_id))
                    CreatePower(ch_id, control_id, config)

    def init_cert_service(self):
        #
        # Certificate Service
        #
        g.api.add_resource(ReplaceCertificateAPI, '/redfish/v1/CertificateService/Actions/CertificateService.ReplaceCertificate')
        certCollection = self.resource_dictionary.get_resource('Managers/BMC/NetworkProtocol/HTTPS/Certificates')
        for member in certCollection['Members']['Certificates']:
            cert_id = member['@odata.id'].replace('/redfish/v1/Managers/BMC/NetworkProtocol/HTTPS/Certificates/', '')
            cert_config = self.resource_dictionary.get_resource('Managers/BMC/NetworkProtocol/HTTPS/Certificates/%s' % cert_id)
            CreateCert(cert_id, cert_config)

    # Randomize serial numbers and MAC addresses just in case multiple instances are created
    def randomize(self):
        # List of all of the paths with serial numbers we want to randomize
        paths = {
            'Chassis/Enclosure',
            'Chassis/Mezz0',
            'Chassis/Mezz1',
            'Chassis/Node0/NetworkAdapters/HPCNet0',
            'Chassis/Node0/NetworkAdapters/HPCNet1',
            'Chassis/Node0/NetworkAdapters/HPCNet2',
            'Chassis/Node0/NetworkAdapters/HPCNet3',
            'Systems/Node0',
            'Systems/Node0/Memory/DIMM0',
            'Systems/Node0/Memory/DIMM1',
            'Systems/Node0/Memory/DIMM2',
            'Systems/Node0/Memory/DIMM3',
            'Systems/Node0/Memory/DIMM4',
            'Systems/Node0/Memory/DIMM5',
            'Systems/Node0/Memory/DIMM6',
            'Systems/Node0/Memory/DIMM7',
            'Systems/Node0/Processors/CPU0',
            'Systems/Node0/Processors/GPU0',
            'Systems/Node0/Processors/GPU1',
            'Systems/Node0/Processors/GPU2',
            'Systems/Node0/Processors/GPU3',
            'Systems/Node0/Processors/GPU4',
            'Systems/Node0/Processors/GPU5',
            'Systems/Node0/Processors/GPU6',
            'Systems/Node0/Processors/GPU7'
        }
        foundSNs = {}
        for path in paths:
            page = self.resource_dictionary.get_object(path)
            sn = page.configuration['SerialNumber']
            # If they have the same SN as something else in our mockup,
            # keep it that way. Except if the value is bogus.
            if sn in foundSNs and sn != '00000000000000':
                page.configuration['SerialNumber'] = foundSNs[sn]
            else:
                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
                foundSNs[sn] = rndSN
                page.configuration['SerialNumber'] = rndSN

        path = 'Chassis/Node0/Assembly'
        page = self.resource_dictionary.get_object(path)
        for assembly in page.configuration['Assemblies']:
            sn = assembly['SerialNumber']
            if sn in foundSNs and sn != '00000000000000':
                assembly['SerialNumber'] = foundSNs[sn]
            else:
                rndSN = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
                foundSNs[sn] = rndSN
                assembly['SerialNumber'] = rndSN

        path = 'Systems/Node0/EthernetInterfaces/ManagementEthernet'
        page = self.resource_dictionary.get_object(path)
        if self.xname is None:
            rndMAC = [ 0x00, 0x40, 0xa6,
                random.randint(0x00, 0x7f),
                random.randint(0x00, 0xff),
                random.randint(0x00, 0xff)]
        else:
            fields = [int(s) for s in re.findall(r'-?\d+\.?\d*', self.xname)]
            rndMAC = [ 0x02,
                (fields[0]>>8)&0xff,
                fields[0]&0xff,
                fields[1]&0xff,
                (fields[2]+48)&0xff,
                (fields[3]<<4)&0xff]
        newMAC = ':'.join(map(lambda x: "%02x" % x, rndMAC))
        page.configuration['MACAddress'] = newMAC
        page.configuration['PermanentMACAddress'] = newMAC
