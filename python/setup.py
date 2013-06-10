#!/usr/bin/env python
#
# Copyright 2013 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Setup configuration."""

import platform

from ez_setup import use_setuptools
use_setuptools()
import setuptools

# Configure the required packages and scripts to install, depending on
# Python version and OS.
REQUIRED_PACKAGES = []
CONSOLE_SCRIPTS = [
    'gen_protorpc = gen_protorpc:main',
    ]

py_version = platform.python_version()
if py_version < '2.6':
  REQUIRED_PACKAGES.append('simplejson')

_PROTORPC_VERSION = '0.9'

setuptools.setup(
    name='protorpc',
    version=_PROTORPC_VERSION,
    description='Google Protocol RPC',
    url='http://code.google.com/p/google-protorpc/',
    author='Google Inc.',
    author_email='rafek@google.com',
    # Contained modules and scripts.
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': CONSOLE_SCRIPTS,
        },
    install_requires=REQUIRED_PACKAGES,
    provides=[
        'protorpc (%s)' % (_PROTORPC_VERSION,),
        ],
    # PyPI package information.
    classifiers=[
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    license='Apache 2.0',
    keywords='google protocol rpc',
    )
