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

"""Tests for protorpc.service_handlers."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import cgi
import cStringIO
import re
import unittest
import urllib

import test_util
import webapp_test_util

from google.appengine.ext import webapp
from protorpc import messages
from protorpc import protobuf
from protorpc import protojson
from protorpc import protourlencode
from protorpc import remote
from protorpc import service_handlers

import mox


class ModuleInterfaceTest(test_util.ModuleInterfaceTest,
                          test_util.TestCase):

  MODULE = service_handlers


class Enum1(messages.Enum):
  """A test enum class."""

  VAL1 = 1
  VAL2 = 2
  VAL3 = 3


class Request1(messages.Message):
  """A test request message type."""

  integer_field = messages.IntegerField(1)
  string_field = messages.StringField(2)
  enum_field = messages.EnumField(Enum1, 3)


class Response1(messages.Message):
  """A test response message type."""

  integer_field = messages.IntegerField(1)
  string_field = messages.StringField(2)
  enum_field = messages.EnumField(Enum1, 3)


class SuperMessage(messages.Message):
  """A test message with a nested message field."""

  sub_message = messages.MessageField(Request1, 1)
  sub_messages = messages.MessageField(Request1, 2, repeated=True)


class SuperSuperMessage(messages.Message):
  """A test message with two levels of nested."""

  sub_message = messages.MessageField(SuperMessage, 1)
  sub_messages = messages.MessageField(Request1, 2, repeated=True)


class RepeatedMessage(messages.Message):
  """A test message with a repeated field."""

  ints = messages.IntegerField(1, repeated=True)
  strings = messages.StringField(2, repeated=True)
  enums = messages.EnumField(Enum1, 3, repeated=True)


class Service(object):
  """A simple service that takes a Request1 and returns Request2."""

  @remote.remote(Request1, Response1)
  def method1(self, request):
    response = Response1()
    if hasattr(request, 'integer_field'):
      response.integer_field = request.integer_field
    if hasattr(request, 'string_field'):
      response.string_field = request.string_field
    if hasattr(request, 'enum_field'):
      response.enum_field = request.enum_field
    return response

  @remote.remote(RepeatedMessage, RepeatedMessage)
  def repeated_method(self, request):
    response = RepeatedMessage()
    if hasattr(request, 'ints'):
      response = request.ints
    return response

  def not_remote(self):
    pass


def VerifyResponse(test,
                   response,
                   expected_status,
                   expected_status_message,
                   expected_content):
  def write(content):
    if expected_content == '':
      test.assertEquals('', content)
    else:
      test.assertNotEquals(-1, content.find(expected_content))

  def start_response(response, headers):
    status, message = response.split(' ', 1)
    test.assertEquals(expected_status, status)
    test.assertEquals(expected_status_message, message)
    return write

  response.wsgi_write(start_response)


class ServiceHandlerFactoryTest(test_util.TestCase):
  """Tests for the service handler factory."""

  def testAllRequestMappers(self):
    """Test all_request_mappers method."""
    configuration = service_handlers.ServiceHandlerFactory(Service)
    mapper1 = service_handlers.RPCMapper(['whatever'], 'whatever', None)
    mapper2 = service_handlers.RPCMapper(['whatever'], 'whatever', None)

    configuration.add_request_mapper(mapper1)
    self.assertEquals([mapper1], list(configuration.all_request_mappers()))

    configuration.add_request_mapper(mapper2)
    self.assertEquals([mapper1, mapper2],
                      list(configuration.all_request_mappers()))

  def testServiceClass(self):
    """Test that service_class attribute is set."""
    factory = service_handlers.ServiceHandlerFactory(Service)
    self.assertEquals(Service, factory.service_class)

  def testFactoryMethod(self):
    """Test that factory creates correct instance of class."""
    factory = service_handlers.ServiceHandlerFactory(Service)
    handler = factory()

    self.assertTrue(isinstance(handler, service_handlers.ServiceHandler))
    self.assertTrue(isinstance(handler.service, Service))

  def testMapping(self):
    """Test the mapping method."""
    factory = service_handlers.ServiceHandlerFactory(Service)
    path, mapped_factory = factory.mapping('/my_service')

    self.assertEquals(r'/my_service' + service_handlers._METHOD_PATTERN, path)
    self.assertEquals(id(factory), id(mapped_factory))
    match = re.match(path, '/my_service.my_method')
    self.assertEquals('my_method', match.group(1))

    path, mapped_factory = factory.mapping('/my_service/nested')
    self.assertEquals('/my_service/nested' +
                      service_handlers._METHOD_PATTERN, path)
    match = re.match(path, '/my_service/nested.my_method')
    self.assertEquals('my_method', match.group(1))

  def testRegexMapping(self):
    """Test the mapping method using a regex."""
    factory = service_handlers.ServiceHandlerFactory(Service)
    path, mapped_factory = factory.mapping('.*/my_service')

    self.assertEquals(r'.*/my_service' + service_handlers._METHOD_PATTERN, path)
    self.assertEquals(id(factory), id(mapped_factory))
    match = re.match(path, '/whatever_preceeds/my_service.my_method')
    self.assertEquals('my_method', match.group(1))
    match = re.match(path, '/something_else/my_service.my_other_method')
    self.assertEquals('my_other_method', match.group(1))

  def testMapping_BadPath(self):
    """Test bad parameterse to the mapping method."""
    factory = service_handlers.ServiceHandlerFactory(Service)
    self.assertRaises(ValueError, factory.mapping, '/my_service/')

  def testDefault(self):
    """Test the default factory convenience method."""
    factory = service_handlers.ServiceHandlerFactory.default(
        Service,
        parameter_prefix='my_prefix.')

    self.assertEquals(Service, factory.service_class)

    mappers = factory.all_request_mappers()

    # Verify URL encoded mapper.
    url_encoded_mapper = mappers.next()
    self.assertTrue(isinstance(url_encoded_mapper,
                               service_handlers.URLEncodedRPCMapper))
    self.assertEquals('my_prefix.', url_encoded_mapper.parameter_prefix)

    # Verify Protobuf encoded mapper.
    protobuf_mapper = mappers.next()
    self.assertTrue(isinstance(protobuf_mapper,
                               service_handlers.ProtobufRPCMapper))

    # Verify JSON encoded mapper.
    json_mapper = mappers.next()
    self.assertTrue(isinstance(json_mapper,
                               service_handlers.JSONRPCMapper))

    # Should have no more mappers.
    self.assertRaises(StopIteration, mappers.next)


class ServiceHandlerTest(webapp_test_util.RequestHandlerTestBase):
  """Test the ServiceHandler class."""

  def setUp(self):
    self.mox = mox.Mox()
    self.service_factory = Service
    self.remote_host = 'remote.host.com'
    self.server_host = 'server.host.com'
    self.ResetRequestHandler()

    self.request = Request1()
    self.request.integer_field = 1
    self.request.string_field = 'a'
    self.request.enum_field = Enum1.VAL1

  def ResetRequestHandler(self):
    super(ServiceHandlerTest, self).setUp()

  def CreateService(self):
    return self.service_factory()

  def CreateRequestHandler(self):
    self.rpc_mapper1 = self.mox.CreateMock(service_handlers.RPCMapper)
    self.rpc_mapper1.http_methods = set(['POST'])
    self.rpc_mapper1.content_types = set(['application/x-www-form-urlencoded'])
    self.rpc_mapper2 = self.mox.CreateMock(service_handlers.RPCMapper)
    self.rpc_mapper2.http_methods = set(['GET'])
    self.rpc_mapper2.content_types = set(['application/x-www-form-urlencoded'])
    self.factory = service_handlers.ServiceHandlerFactory(
        self.CreateService)
    self.factory.add_request_mapper(self.rpc_mapper1)
    self.factory.add_request_mapper(self.rpc_mapper2)
    return self.factory()

  def GetEnvironment(self):
    """Create handler to test."""
    environ = super(ServiceHandlerTest, self).GetEnvironment()
    if self.remote_host:
      environ['REMOTE_HOST'] = self.remote_host
    if self.server_host:
      environ['SERVER_HOST'] = self.server_host
    return environ

  def VerifyResponse(self,
                      expected_status,
                      expected_status_message,
                      expected_content):
    VerifyResponse(self,
                   self.response,
                   expected_status,
                   expected_status_message,
                   expected_content)

  def testRedirect(self):
    """Test that redirection is disabled."""
    self.assertRaises(NotImplementedError, self.handler.redirect, '/')

  def testFirstMapper(self):
    """Make sure service attribute works when matches first RPCMapper."""
    self.rpc_mapper1.build_request(
        self.handler, Request1).AndReturn(self.request)

    def build_response(handler, response):
      output = '%s %s %s' % (response.integer_field,
                             response.string_field,
                             response.enum_field)
      handler.response.out.write(output)
    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1)).WithSideEffects(build_response)

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('200', 'OK', '1 a VAL1')

    self.mox.VerifyAll()

  def testSecondMapper(self):
    """Make sure service attribute works when matches first RPCMapper.

    Demonstrates the multiplicity of the RPCMapper configuration.
    """
    self.rpc_mapper2.build_request(
        self.handler, Request1).AndReturn(self.request)

    def build_response(handler, response):
      output = '%s %s %s' % (response.integer_field,
                             response.string_field,
                             response.enum_field)
      handler.response.out.write(output)
    self.rpc_mapper2.build_response(
        self.handler, mox.IsA(Response1)).WithSideEffects(build_response)

    self.mox.ReplayAll()

    self.handler.handle('GET', 'method1')

    self.VerifyResponse('200', 'OK', '1 a VAL1')

    self.mox.VerifyAll()

  def testCaseInsensitiveContentType(self):
    """Ensure that matching content-type is case insensitive."""
    request = Request1()
    request.integer_field = 1
    request.string_field = 'a'
    request.enum_field = Enum1.VAL1
    self.rpc_mapper1.build_request(self.handler,
                                   Request1).AndReturn(self.request)

    def build_response(handler, response):
      output = '%s %s %s' % (response.integer_field,
                             response.string_field,
                             response.enum_field)
      handler.response.out.write(output)
    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1)).WithSideEffects(build_response)

    self.mox.ReplayAll()

    self.handler.request.headers['Content-Type'] = ('ApPlIcAtIoN/'
                                                    'X-wWw-FoRm-UrLeNcOdEd')

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('200', 'OK', '1 a VAL1')

    self.mox.VerifyAll()

  def testContentTypeWithParameters(self):
    """Test that content types have parameters parsed out."""
    request = Request1()
    request.integer_field = 1
    request.string_field = 'a'
    request.enum_field = Enum1.VAL1
    self.rpc_mapper1.build_request(self.handler,
                                   Request1).AndReturn(self.request)

    def build_response(handler, response):
      output = '%s %s %s' % (response.integer_field,
                             response.string_field,
                             response.enum_field)
      handler.response.out.write(output)
    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1)).WithSideEffects(build_response)

    self.mox.ReplayAll()

    self.handler.request.headers['Content-Type'] = ('application/'
                                                    'x-www-form-urlencoded' +
                                                    '; a=b; c=d')

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('200', 'OK', '1 a VAL1')

    self.mox.VerifyAll()

  def testRequestState(self):
    """Make sure request state is passed in to handler that supports it."""
    class ServiceWithState(object):

      initialize_request_state = self.mox.CreateMockAnything()

      @remote.remote(Request1, Response1)
      def method1(self, request):
        return Response1()

    self.service_factory = ServiceWithState

    # Reset handler with new service type.
    self.ResetRequestHandler()

    self.rpc_mapper1.build_request(
        self.handler, Request1).AndReturn(Request1())
    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1))

    def verify_state(state):
      return ('remote.host.com' ==  state.remote_host and
              '127.0.0.1' == state.remote_address and
              'server.host.com' == state.server_host and
              8080 == state.server_port)
    ServiceWithState.initialize_request_state(mox.Func(verify_state))

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('200', 'OK', '')

    self.mox.VerifyAll()

  def testRequestState_MissingHosts(self):
    """Make sure missing state environment values are handled gracefully."""
    class ServiceWithState(object):

      initialize_request_state = self.mox.CreateMockAnything()

      @remote.remote(Request1, Response1)
      def method1(self, request):
        return Response1()

    self.service_factory = ServiceWithState
    self.remote_host = None
    self.server_host = None

    # Reset handler with new service type.
    self.ResetRequestHandler()

    self.rpc_mapper1.build_request(
        self.handler, Request1).AndReturn(Request1())
    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1))

    def verify_state(state):
      return (None is state.remote_host and
              '127.0.0.1' == state.remote_address and
              None is state.server_host and
              8080 == state.server_port)
    ServiceWithState.initialize_request_state(mox.Func(verify_state))

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('200', 'OK', '')

    self.mox.VerifyAll()

  def testNoMatch_UnknownHTTPMethod(self):
    """Test what happens when no RPCMapper matches.."""
    self.mox.ReplayAll()

    self.handler.handle('UNKNOWN', 'does_not_matter')

    self.VerifyResponse('400', 'Unrecognized RPC format.', '')

    self.mox.VerifyAll()

  def testNoMatch_UnknownContentType(self):
    """Test what happens when no RPCMapper matches.."""
    self.mox.ReplayAll()

    self.handler.request.headers['Content-Type'] = 'image/png'
    self.handler.handle('POST', 'method1')

    self.VerifyResponse('400', 'Unrecognized RPC format.', '')

    self.mox.VerifyAll()

  def testNoMatch_NoContentType(self):
    """Test what happens when no RPCMapper matches.."""
    self.mox.ReplayAll()

    del self.handler.request.headers['Content-Type']
    self.handler.handle('POST', 'method1')

    self.VerifyResponse('400', 'Unrecognized RPC format.', '')

    self.mox.VerifyAll()

  def testNoSuchMethod(self):
    """When service method not found."""
    self.mox.ReplayAll()

    self.handler.handle('POST', 'no_such_method')

    self.VerifyResponse('400', 'Unrecognized RPC method: no_such_method', '')

    self.mox.VerifyAll()

  def testNoSuchRemoteMethod(self):
    """When service method exists but is not remote."""
    self.mox.ReplayAll()

    self.handler.handle('POST', 'not_remote')

    self.VerifyResponse('400', 'Unrecognized RPC method: not_remote', '')

    self.mox.VerifyAll()

  def testRequestError(self):
    """RequestError handling."""
    def build_request(handler, request):
      raise service_handlers.RequestError('This is a request error')
    self.rpc_mapper1.build_request(
        self.handler, Request1).WithSideEffects(build_request)

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('400', 'Invalid RPC request.', '')

    self.mox.VerifyAll()

  def testDecodeError(self):
    """DecodeError handling."""
    def build_request(handler, request):
      raise messages.DecodeError('This is a decode error')
    self.rpc_mapper1.build_request(
        self.handler, Request1).WithSideEffects(build_request)

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('400', 'Invalid RPC request.', '')

    self.mox.VerifyAll()

  def testResponseException(self):
    """Test what happens when build_response raises ResponseError."""
    self.rpc_mapper1.build_request(
        self.handler, Request1).AndReturn(self.request)

    self.rpc_mapper1.build_response(
        self.handler, mox.IsA(Response1)).AndRaise(
        service_handlers.ResponseError)

    self.mox.ReplayAll()

    self.handler.handle('POST', 'method1')

    self.VerifyResponse('500', 'Invalid RPC response.', '')

    self.mox.VerifyAll()

  def testGet(self):
    """Test that GET goes to 'handle' properly."""
    self.handler.handle = self.mox.CreateMockAnything()
    self.handler.handle('GET', 'alternate_method')

    self.mox.ReplayAll()

    self.handler.get('alternate_method')

    self.mox.VerifyAll()

  def testPost(self):
    """Test that POST goes to 'handle' properly."""
    self.handler.handle = self.mox.CreateMockAnything()
    self.handler.handle('POST', 'alternate_method')

    self.mox.ReplayAll()

    self.handler.post('alternate_method')

    self.mox.VerifyAll()


class RPCMapperTestBase(test_util.TestCase):

  def setUp(self):
    """Set up test framework."""
    self.Reinitialize()

  def Reinitialize(self, input='',
                   get=False,
                   path_method='method1',
                   content_type='text/plain'):
    """Allows reinitialization of test with custom input values and POST.

    Args:
      input: Query string or POST input.
      get: Use GET method if True.  Use POST if False.
    """
    self.factory = service_handlers.ServiceHandlerFactory(Service)

    self.service_handler = service_handlers.ServiceHandler(self.factory,
                                                           Service())
    self.service_handler.remote_method = path_method
    request_path = '/servicepath'
    if path_method:
      request_path += '/' + path_method
    if get:
      request_path += '?' + input

    if get:
      environ = {'wsgi.input': cStringIO.StringIO(''),
                 'CONTENT_LENGTH': '0',
                 'QUERY_STRING': input,
                 'REQUEST_METHOD': 'GET',
                 'PATH_INFO': request_path,
                }
      self.service_handler.method = 'GET'
    else:
      environ = {'wsgi.input': cStringIO.StringIO(input),
                 'CONTENT_LENGTH': str(len(input)),
                 'QUERY_STRING': '',
                 'REQUEST_METHOD': 'POST',
                 'PATH_INFO': request_path,
                }
      self.service_handler.method = 'POST'

    self.request = webapp.Request(environ)

    self.response = webapp.Response()

    self.service_handler.initialize(self.request, self.response)

    self.service_handler.request.headers['Content-Type'] = content_type


class RPCMapperTest(RPCMapperTestBase, webapp_test_util.RequestHandlerTestBase):
  """Test the RPCMapper base class."""

  def setUp(self):
    RPCMapperTestBase.setUp(self)
    webapp_test_util.RequestHandlerTestBase.setUp(self)
    self.mox = mox.Mox()
    self.protocol = self.mox.CreateMockAnything()

  def GetEnvironment(self):
    """Get environment.

    Return bogus content in body.

    Returns:
      dict of CGI environment.
    """
    environment = super(RPCMapperTest, self).GetEnvironment()
    environment['wsgi.input'] = cStringIO.StringIO('my body')
    environment['CONTENT_LENGTH'] = len('my body')
    return environment

  def testInvalidArguments(self):
    """Test invalid arguments in to constructor."""
    self.assertRaisesWithRegexpMatch(
        TypeError,
        "Found unexpected arguments: {'unknown': 'whatever'}",
        service_handlers.RPCMapper,
        ['GET', 'POST'],
        'my-content-type',
        self.protocol,
        unknown='whatever')

  def testContentTypes_JustDefault(self):
    """Test content type attributes."""
    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['GET', 'POST'],
                                        'my-content-type',
                                        self.protocol)

    self.assertEquals(frozenset(['GET', 'POST']), mapper.http_methods)
    self.assertEquals('my-content-type', mapper.default_content_type)
    self.assertEquals(frozenset(['my-content-type']),
                                mapper.content_types)

    self.mox.VerifyAll()

  def testContentTypes_Extended(self):
    """Test content type attributes."""
    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['GET', 'POST'],
                                        'my-content-type',
                                        self.protocol,
                                        content_types=['a', 'b'])

    self.assertEquals(frozenset(['GET', 'POST']), mapper.http_methods)
    self.assertEquals('my-content-type', mapper.default_content_type)
    self.assertEquals(frozenset(['my-content-type', 'a', 'b']),
                                mapper.content_types)

    self.mox.VerifyAll()

  def testBuildRequest(self):
    """Test building a request."""
    expected_request = Request1()
    self.protocol.decode_message(Request1,
                                 'my body').AndReturn(expected_request)

    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['POST'],
                                        'my-content-type',
                                        self.protocol)

    request = mapper.build_request(self.handler, Request1)

    self.assertTrue(expected_request is request)

  def testBuildRequest_ValidationError(self):
    """Test building a request generating a validation error."""
    expected_request = Request1()
    self.protocol.decode_message(
        Request1, 'my body').AndRaise(messages.ValidationError('xyz'))

    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['POST'],
                                        'my-content-type',
                                        self.protocol)

    self.assertRaisesWithRegexpMatch(
        service_handlers.RequestError,
        'Unable to parse request content: xyz',
        mapper.build_request,
        self.handler,
        Request1)

  def testBuildRequest_DecodeError(self):
    """Test building a request generating a decode error."""
    expected_request = Request1()
    self.protocol.decode_message(
        Request1, 'my body').AndRaise(messages.DecodeError('xyz'))

    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['POST'],
                                        'my-content-type',
                                        self.protocol)

    self.assertRaisesWithRegexpMatch(
        service_handlers.RequestError,
        'Unable to parse request content: xyz',
        mapper.build_request,
        self.handler,
        Request1)

  def testBuildResponse(self):
    """Test building a response."""
    response = Response1()
    self.protocol.encode_message(response).AndReturn('encoded')

    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['POST'],
                                        'my-content-type',
                                        self.protocol)

    request = mapper.build_response(self.handler, response)

    self.assertEquals('my-content-type',
                      self.handler.response.headers['Content-Type'])
    self.assertEquals('encoded', self.handler.response.out.getvalue())

  def testBuildResponse(self):
    """Test building a response."""
    response = Response1()
    self.protocol.encode_message(response).AndRaise(
        messages.ValidationError('xyz'))

    self.mox.ReplayAll()

    mapper = service_handlers.RPCMapper(['POST'],
                                        'my-content-type',
                                        self.protocol)

    self.assertRaisesWithRegexpMatch(service_handlers.ResponseError,
                                     'Unable to encode message: xyz',
                                     mapper.build_response,
                                     self.handler,
                                     response)


class ProtocolMapperTestBase(object):
  """Base class for basic protocol mapper tests."""

  def setUp(self):
    """Reinitialize test specifically for protocol buffer mapper."""
    super(ProtocolMapperTestBase, self).setUp()
    self.Reinitialize(path_method='my_method',
                      content_type='application/x-google-protobuf')

    self.request_message = Request1()
    self.request_message.integer_field = 1
    self.request_message.string_field = u'something'
    self.request_message.enum_field = Enum1.VAL1

    self.response_message = Response1()
    self.response_message.integer_field = 1
    self.response_message.string_field = u'something'
    self.response_message.enum_field = Enum1.VAL1

  def testBuildRequest(self):
    """Test request building."""
    self.Reinitialize(self.protocol.encode_message(self.request_message),
                      content_type=self.content_type)

    mapper = self.mapper()
    parsed_request = mapper.build_request(self.service_handler,
                                          Request1)
    self.assertEquals(self.request_message, parsed_request)

  def testBuildResponse(self):
    """Test response building."""

    mapper = self.mapper()
    mapper.build_response(self.service_handler, self.response_message)
    self.assertEquals(self.protocol.encode_message(self.response_message),
                      self.service_handler.response.out.getvalue())

  def testWholeRequest(self):
    """Test the basic flow of a request with mapper class."""
    body = self.protocol.encode_message(self.request_message)
    self.Reinitialize(input=body,
                      content_type=self.content_type)
    self.factory.add_request_mapper(self.mapper())
    self.service_handler.handle('POST', 'method1')
    VerifyResponse(self,
                   self.service_handler.response,
                   '200',
                   'OK',
                   self.protocol.encode_message(self.response_message))


class URLEncodedRPCMapperTest(ProtocolMapperTestBase, RPCMapperTestBase):
  """Test the URL encoded RPC mapper."""

  content_type = 'application/x-www-form-urlencoded'
  protocol = protourlencode
  mapper = service_handlers.URLEncodedRPCMapper

  def testBuildRequest_Prefix(self):
    """Test building request with parameter prefix."""
    self.Reinitialize(urllib.urlencode([('prefix_integer_field', '10'),
                                        ('prefix_string_field', 'a string'),
                                        ('prefix_enum_field', 'VAL1'),
                                       ]),
                      self.content_type)

    url_encoded_mapper = service_handlers.URLEncodedRPCMapper(
        parameter_prefix='prefix_')
    request = url_encoded_mapper.build_request(self.service_handler,
                                               Request1)
    self.assertEquals(10, request.integer_field)
    self.assertEquals('a string', request.string_field)
    self.assertEquals(Enum1.VAL1, request.enum_field)

  def testBuildRequest_DecodeError(self):
    """Test trying to build request that causes a decode error."""
    self.Reinitialize(urllib.urlencode((('integer_field', '10'),
                                        ('integer_field', '20'),
                                        )),
                      content_type=self.content_type)

    url_encoded_mapper = service_handlers.URLEncodedRPCMapper()

    self.assertRaises(service_handlers.RequestError,
                      url_encoded_mapper.build_request,
                      self.service_handler,
                      Service.method1.remote.request_type)

  def testBuildResponse_Prefix(self):
    """Test building a response with parameter prefix."""
    response = Response1()
    response.integer_field = 10
    response.string_field = u'a string'
    response.enum_field = Enum1.VAL3

    url_encoded_mapper = service_handlers.URLEncodedRPCMapper(
        parameter_prefix='prefix_')

    url_encoded_mapper.build_response(self.service_handler, response)
    self.assertEquals('application/x-www-form-urlencoded',
                      self.response.headers['content-type'])
    self.assertEquals(cgi.parse_qs(self.response.out.getvalue(), True, True),
                      {'prefix_integer_field': ['10'],
                       'prefix_string_field': [u'a string'],
                       'prefix_enum_field': ['VAL3'],
                      })


class ProtobufRPCMapperTest(ProtocolMapperTestBase, RPCMapperTestBase):
  """Test the protobuf encoded RPC mapper."""

  content_type = 'application/x-google-protobuf'
  protocol = protobuf
  mapper = service_handlers.ProtobufRPCMapper


class JSONRPCMapperTest(ProtocolMapperTestBase, RPCMapperTestBase):
  """Test the URL encoded RPC mapper."""

  content_type = 'application/json'
  protocol = protojson
  mapper = service_handlers.JSONRPCMapper


def main():
  unittest.main()


if __name__ == '__main__':
  main()
