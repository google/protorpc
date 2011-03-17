#!/usr/bin/env python
#
# Copyright 2010 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from distutils import core

core.setup(name='protorpc',
           version='0.1',
           py_modules=[
               'protorpc.definition',
               'protorpc.descriptor',
               'protorpc.dynamic',
               'protorpc.forms',
               'protorpc.generate',
               'protorpc.generate_proto',
               'protorpc.generate_python',
               'protorpc.message_types',
               'protorpc.messages',
               'protorpc.protobuf',
               'protorpc.protojson',
               'protorpc.protourlencode',
               'protorpc.registry',
               'protorpc.remote',
               'protorpc.service_handlers',
               'protorpc.transport',
               'protorpc.util',
               ],
           )
