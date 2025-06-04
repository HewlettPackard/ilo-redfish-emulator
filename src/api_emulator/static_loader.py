# Copyright Notice:
# Copyright 2016-2019 DMTF. All rights reserved.
# License: BSD 3-Clause License. For full text see link: https://github.com/DMTF/Redfish-Interface-Emulator/blob/master/LICENSE.md
#
# The original DMTF contents of this file have been modified to support
# The CSM Redfish Interface Emulator. These modifications are subject to the following:
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

# Module for loading in static data (mockups)

import json
import os
import re

import sys, traceback
from .utils import process_id
from .resource_dictionary import ResourceDictionary

class StaticLoadError(Exception):
    pass

class Member():
    def __init__(self, config):
        self.config = config

    @property
    def configuration(self):
        return self.config

def load_static(name, spec, mode, rest_base, resource_dictionary):
    """
    Loads the static data starting at the directory ./<spec>/static/<name>, recursively.

    Populates the resdict dictionary, with the file path as the key.

    Expects a single index.json file in each directory.  Ignores other files.

    Arguments:
        name      - Name of the static data
        spec      - Which spec the data is under, must be either redfish
                    or chinook
        rest_base - Base URL of the RESTful interface
    """
    try:
        assert spec.lower() in ['redfish'], 'Unknown spec: ' + spec
        assert mode.lower() in ['local', 'cloud'], 'Unknown mode: ' + mode
        dirname = os.path.dirname(__file__)
        base_dir = os.path.join(dirname, spec.lower(), 'static', name)
        index = os.path.join(base_dir, 'index.json')
        assert os.path.exists(index), 'Static data for ' + name + ' does not exist'

        for dirName, subdirList, fileList in os.walk(base_dir):
            # print('Found directory: %s' % dirName)
            for fname in fileList:
                if fname != 'index.json':
                    continue
                path = os.path.join(dirName, fname)
                f = open(path)
                index = json.load(f)
                m = Member(index)

                # Create shortpath starting at ServiceRoot
                if mode == 'Cloud':
                    shortpath = re.sub(base_dir + '/', '', path)
                else:
                    shortpath = os.path.relpath(path, base_dir)
                    shortpath = shortpath.replace('\\', '/')
                if dirName == base_dir:
                    shortpath = ''
                else:
                    shortpath = re.sub('/index.json', '', shortpath)
                resource_dictionary.add_resource(shortpath, m)
# debug print
#        resource_dictionary.print_dictionary()

    except AssertionError as e:
        traceback.print_exc()
        raise StaticLoadError(e)
    return shortpath
