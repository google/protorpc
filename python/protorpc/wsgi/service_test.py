#!/usr/bin/env python
#
# Copyright 2011 Google Inc.
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

"""WSGI application tests."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import logging
import unittest
from wsgiref import util as wsgi_util

from google.appengine.ext import webapp

from protorpc import end2end_test
from protorpc import protojson
from protorpc import remote
from protorpc import transport
from protorpc import test_util
from protorpc import webapp_test_util
from protorpc.wsgi import service


class ProtoRpcServiceTest(end2end_test.EndToEndTest):

  def setUp(self):
    self.protocols = None
    super(ProtoRpcServiceTest, self).setUp()

  def  CreateWsgiApplication(self):
    """Create WSGI application used on the server side for testing."""
    my_service = service.service_mapping(webapp_test_util.TestService,
                                         '/my/service')
    my_other_service = service.service_mapping(
      webapp_test_util.TestService.new_factory('initialized'),
      '/my/other_service',
      protocols=self.protocols)

    def request_router(environ, start_response):
      path_info = environ['PATH_INFO']
      if path_info.startswith('/my/service'):
        return my_service(environ, start_response)
      elif path_info.startswith('/my/other_service'):
        return my_other_service(environ, start_response)
      raise AssertionError('Should never get here')
    return request_router

  def testAlternateProtocols(self):
    self.protocols = remote.Protocols()
    self.protocols.add_protocol(protojson, 'altproto', 'image/png')
    self.ResetServer()

    self.connection = transport.HttpTransport(
      self.service_url, protocol=self.protocols.lookup_by_name('altproto'))
    self.stub = webapp_test_util.TestService.Stub(self.connection)

    self.stub.optional_message(string_value='alternate-protocol')


def main():
  unittest.main()


if __name__ == '__main__':
  main()
