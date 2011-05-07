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

"""Tests for protorpc.experimental.wsgi_handlers."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import cStringIO
import unittest
from wsgiref import validate

from protorpc.experimental import wsgi_handlers
from protorpc import protojson
from protorpc import remote
from protorpc import test_util
from protorpc import webapp_test_util

import mox

package = 'testpackage'


class TestService(remote.Service):

  def __init__(self, format='Default %s'):
    self.format = format

  @remote.method(test_util.HasDefault, test_util.HasDefault)
  def method1(self, request):
    return test_util.HasDefault(a_value=self.format % request.a_value)

  def instance_method(self):
    raise AssertionError('Do not call')


class ModuleInterfaceTest(test_util.ModuleInterfaceTest,
                          test_util.TestCase):

  MODULE = wsgi_handlers


# TODO(rafek): Test case insensitive.
class ProtocolConfigTest(test_util.TestCase):

  def testConstructor(self):
    config = wsgi_handlers.ProtocolConfig(
      protojson,
      'proto1',
      'application/x-json',
      iter(['text/json', 'text/javascript']))
    self.assertEquals(protojson, config.protocol)
    self.assertEquals('proto1', config.name)
    self.assertEquals('application/x-json', config.default_content_type)
    self.assertEquals(('text/json', 'text/javascript'),
                      config.alternate_content_types)
    self.assertEquals(('application/x-json', 'text/json', 'text/javascript'),
                      config.content_types)

  def testConstructorDefaults(self):
    config = wsgi_handlers.ProtocolConfig(
      protojson,
      'proto2')
    self.assertEquals(protojson, config.protocol)
    self.assertEquals('proto2', config.name)
    self.assertEquals('application/json', config.default_content_type)
    self.assertEquals((), config.alternate_content_types)
    self.assertEquals(('application/json',), config.content_types)

  def testDuplicateContentTypes(self):
    self.assertRaises(wsgi_handlers.ServiceConfigurationError,
                      wsgi_handlers.ProtocolConfig,
                      protojson,
                      'json',
                      'text/plain',
                      ('text/plain',))
    self.assertRaises(wsgi_handlers.ServiceConfigurationError,
                      wsgi_handlers.ProtocolConfig,
                      protojson,
                      'json',
                      'text/plain',
                      ('text/html', 'text/html'))


# TODO(rafek): Test case insensitive.
# TODO(rafek): Test lookup functions.
class ProtocolsTest(test_util.TestCase):

  def setUp(self):
    self.protocols = wsgi_handlers.Protocols()

  def testEmpty(self):
    self.assertEquals((), self.protocols.names)
    self.assertEquals((), self.protocols.content_types)

  def testHasConfigs(self):
    self.protocols.add_protocol(protojson, 'json')
    self.protocols.add_protocol(protojson, 'json2', 'text/x-json')
    self.protocols.add_protocol(
      protojson, 'alpha', 'text/plain', ('text/other',))
    self.assertEquals(('alpha', 'json', 'json2'), self.protocols.names)
    self.assertEquals(('application/json',
                       'text/other',
                       'text/plain',
                       'text/x-json'),
                      self.protocols.content_types)


class ServiceAppTest(test_util.TestCase):

  def setUp(self):
    self.protocols = wsgi_handlers.Protocols()
    self.protocols.add_protocol(protojson, 'json')
    self.mox = mox.Mox()
    self.environ = webapp_test_util.GetDefaultEnvironment()
    self.environ['HTTP_METHOD'] = 'POST'
    self.environ['CONTENT_TYPE'] = protojson.CONTENT_TYPE
    self.start_response = self.mox.CreateMockAnything()

  def SetUpCall(self, service_path, method, message):
    self.environ['PATH_INFO'] = '%s.%s' % (service_path, method)
    self.environ['wsgi.input'] = cStringIO.StringIO(
      protojson.encode_message(message))

  def CreateApp(self,
                service_factory=TestService.new_factory('Copy %s'),
                service_path=r'/test/service',
                protocols=None,
                validate_app=True):
    app = wsgi_handlers.ServiceApp(service_factory,
                                   service_path,
                                   protocols or self.protocols)

    if validate_app:
      return validate.validator(app)
    else:
      return app

  def CallApp(self, app, environ, start_response):
    iterator = app(environ, start_response)
    try:
      return ''.join(iterator)
    finally:
      # Iterator should be closed for WSGI compliance.
      iterator.close()

  def testServiceFactory(self):
    factory = TestService.new_factory('Whatever %s')
    app = self.CreateApp(service_factory=factory, validate_app=False)
    self.assertEquals(factory, app.service_factory)
    self.assertEquals(TestService, app.service_class)

  def testServiceClassAsFactory(self):
    app = self.CreateApp(service_factory=TestService, validate_app=False)
    self.assertEquals(TestService, app.service_factory)
    self.assertEquals(TestService, app.service_class)

  def testServicePath(self):
    app = self.CreateApp(validate_app=False)
    self.assertEquals(r'/test/service', app.service_path)

  def testImplicitServicePath(self):
    app = self.CreateApp(service_path=None, validate_app=False)
    self.assertEquals(r'/testpackage/TestService', app.service_path)

  def testProtocols(self):
    app = self.CreateApp(validate_app=False)
    self.assertTrue(isinstance(app.protocols, wsgi_handlers.Protocols))
    self.assertEquals(('json',), app.protocols.names)

  def testDefaultProtocols(self):
    app = wsgi_handlers.ServiceApp(TestService, '/whatever')
    self.assertTrue(isinstance(app.protocols, wsgi_handlers.Protocols))
    self.assertEquals((), app.protocols.names)

  def testBasicRequest(self):
    app = self.CreateApp()
    expected = '{"a_value": "Copy hello"}'

    self.start_response('200 OK', [('content-type', 'application/json'),
                                   ('content-length', str(len(expected))),
                                  ])
    self.mox.ReplayAll()

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))

    content = self.CallApp(app, self.environ, self.start_response)

    self.assertEquals(expected, content)

    self.mox.VerifyAll()

  def testNotMatchingRequestPath(self):
    app = self.CreateApp()

    self.SetUpCall('/does/not/match', 'method1',
                   test_util.HasDefault(a_value='hello'))

    self.start_response("404 Request path '/does/not/match.method1' does not "
                        "match service path r'/test/service'",
                        [('content-length', '0'),
                         ('content-type', 'application/json')
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testNotValidHttpMethod(self):
    app = self.CreateApp()

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))
    self.environ['HTTP_METHOD'] = 'GET'

    self.start_response('404 HTTP method GET not supported',
                        [('content-length', '0'),
                         ('content-type', 'application/json')
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testMethodNotFound(self):
    app = self.CreateApp()

    self.SetUpCall('/test/service', 'not_found',
                   test_util.HasDefault(a_value='hello'))

    self.start_response('400 No such remote method "not_found"',
                        [('content-length', '0'),
                         ('content-type', 'application/json')
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testMethodNotRemote(self):
    app = self.CreateApp()

    self.SetUpCall('/test/service', 'instance_method',
                   test_util.HasDefault(a_value='hello'))

    self.start_response('400 No such remote method "instance_method"',
                        [('content-length', '0'),
                         ('content-type', 'application/json')
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testMissingContentType(self):
    # A valid WSGI app will always send a content-type to the application.
    app = self.CreateApp(validate_app=False)

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))
    del self.environ['CONTENT_TYPE']

    self.start_response('400 Must provide content-type for ProtoRPC requests',
                        [('content-length', '0'),
                         ('content-type', 'text/html')
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testUnrecognizedContentType(self):
    app = self.CreateApp()

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))
    self.environ['CONTENT_TYPE'] = 'application/json-rpc'

    self.start_response('400 Unrecognized content-type application/json-rpc '
                        'for ProtoRPC request',
                        [('content-length', '0'),
                         ('content-type', 'text/html'),
                        ])

    self.mox.ReplayAll()

    content = self.CallApp(app, self.environ, self.start_response)
    self.assertEquals('', content)

    self.mox.VerifyAll()

  def testGetOversizedContentLength(self):
    app = self.CreateApp()
    expected = '{"a_value": "Copy hello"}'

    self.start_response('200 OK', [('content-type', 'application/json'),
                                   ('content-length', str(len(expected))),
                                  ])
    self.environ['CONTENT_LENGTH'] = '1000'
    self.mox.ReplayAll()

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))

    content = self.CallApp(app, self.environ, self.start_response)

    self.assertEquals(expected, content)

    self.mox.VerifyAll()

  def testNoContentLength(self):
    app = self.CreateApp()
    expected = '{"a_value": "Copy hello"}'

    self.start_response('200 OK', [('content-type', 'application/json'),
                                   ('content-length', str(len(expected))),
                                  ])
    del self.environ['CONTENT_LENGTH']
    self.mox.ReplayAll()

    self.SetUpCall('/test/service', 'method1',
                   test_util.HasDefault(a_value='hello'))

    content = self.CallApp(app, self.environ, self.start_response)

    self.assertEquals(expected, content)

    self.mox.VerifyAll()


def main():
  unittest.main()


if __name__ == '__main__':
  main()
