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

# Redfish Event Generator

import strgen
import datetime
import copy
from uuid import uuid4

_GENERIC = \
{
    "EventType": "",
    "Severity": "OK",
    "Message": "",
    "MessageId": "Alert.1.0",
    "MessageArgs": [],
    "OriginOfCondition": "",
    "Context": "{Context}"
}

templates = {}
count = 1

# GenEvent
#
# Create a redfish event with the given EventRecords
def GenEvent(events):
    """
    Event constructor
    """
    config = {
        "@odata.context": "/redfish/v1/$metadata#Event.Event",
        "@odata.type": "#Event.v1_3_1.Event",
        "@odata.id": "/redfish/v1/EventService/Events",
        "Id": "1",
        "Name": "Event Array",
        "Events@odata.count": len(events),
        "Events": events
    }
    return config

# GenEventRecord
#
# Create a redfish event record with the given parameters. How the parameters
# affect the event record is determined by the template used.
# This function generates a timestamp (timestamp), uuid(uuid), random alphanumaric
# string (rnd_str), and counter (count) for use with a template if those arguments
# are specified in the template.
def GenEventRecord(schemaType='Power', **wildcards):
    """
    Event record constructor
    """
    global count
    
    # See if we want to use one of our predefined event
    # schemas to more closely mimic our bmc_type.
    if schemaType in templates:
        wildcards['count'] = count
        count += 1
        wildcards['uuid'] = str(uuid4())
        wildcards['rnd_str'] = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
        wildcards['timestamp'] = datetime.datetime.now().isoformat()
        template = templates[schemaType]

        config = copy.deepcopy(template)
        # Apply event type defaults
        for field in config:
            if field == 'MessageArgs':
                for i in range(len(config[field])):
                    config[field][i] = config[field][i].format(**wildcards)
            elif field == 'OriginOfCondition' and '@odata.id' in config[field]:
                config[field]['@odata.id'] = config[field]['@odata.id'].format(**wildcards)
            elif field != 'Context':
                # Don't add Context here, that will get added later
                config[field] = config[field].format(**wildcards)
    else:
        # If it doesn't match one of our pre-defined event templates the
        # wildcards will just be used to do a striaght field replacement.
        config = copy.deepcopy(_GENERIC)
        for field, value in wildcards.items():
            if field != 'Context':
                config[field] = value
        config['EventId'] = strgen.StringGenerator('[A-Z]{3}[0-9]{10}').render()
        config['EventTimestamp'] = datetime.datetime.now().isoformat()
    return config

# EventGenerator
#
# Initialize the EventGenerator with the templates to use for generating events.
class EventGenerator:
    def __init__(self, eventTemplates):
        global templates
        templates = eventTemplates
