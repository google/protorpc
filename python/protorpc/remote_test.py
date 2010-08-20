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

"""Tests for protorpc.remote."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import sys
import types
import unittest

import test_util
from protorpc import descriptor
from protorpc import message_types
from protorpc import messages
from protorpc import remote


class ModuleInterfaceTest(test_util.ModuleInterfaceTest,
                          test_util.TestCase):

  MODULE = remote


class Request(messages.Message):
  """Test request message."""

  value = messages.StringField(1)

class Response(messages.Message):
  """Test response message."""

  value = messages.StringField(1)

class MyService(remote.Service):

  @remote.remote(Request, Response)
  def remote_method(self, request):
    response = Response()
    response.value = request.value
    return response


class SimpleRequest(messages.Message):
  """Simple request message type used for tests."""


class SimpleResponse(messages.Message):
  """Simple response message type used for tests."""


class BasicService(object):
  """A basic service with decorated remote method."""

  def __init__(self):
    self.request_ids = []

  @remote.remote(SimpleRequest, SimpleResponse)
  def remote_method(self, request):
    self.request_ids.append(id(request))
    return SimpleResponse()


class RemoteTest(test_util.TestCase):
  """Test remote method decorator."""

  def testRemote(self):
    """Test use of remote decorator."""
    self.assertEquals(SimpleRequest,
                      BasicService.remote_method.remote.request_type)
    self.assertEquals(SimpleResponse,
                      BasicService.remote_method.remote.response_type)
    self.assertTrue(isinstance(BasicService.remote_method.remote.method,
                               types.FunctionType))

  def testInvocation(self):
    """Test that invocation passes request through properly."""
    service = BasicService()
    request = SimpleRequest()
    self.assertEquals(SimpleResponse(), service.remote_method(request))
    self.assertEquals([id(request)], service.request_ids)

  def testInvocation_WrongRequestType(self):
    """Wrong request type passed to remote method."""
    service = BasicService()

    self.assertRaises(remote.InvalidRequestError,
                      service.remote_method,
                      'wrong')

    self.assertRaises(remote.InvalidRequestError,
                      service.remote_method,
                      None)

    self.assertRaises(remote.InvalidRequestError,
                      service.remote_method,
                      SimpleResponse())

  def testInvocation_WrongResponseType(self):
    """Wrong response type returned from remote method."""

    class AnotherService(object):

      @remote.remote(SimpleRequest, SimpleResponse)
      def remote_method(self, unused_request):
        return self.return_this

    service = AnotherService()

    service.return_this = 'wrong'
    self.assertRaises(remote.InvalidResponseError,
                      service.remote_method,
                      SimpleRequest())
    service.return_this = None
    self.assertRaises(remote.InvalidResponseError,
                      service.remote_method,
                      SimpleRequest())
    service.return_this = SimpleRequest()
    self.assertRaises(remote.InvalidResponseError,
                      service.remote_method,
                      SimpleRequest())

  def testBadRequestType(self):
    """Test bad request types used in remote definition."""

    for request_type in (None, 'wrong', messages.Message, str):

      def declare():
        class BadService(object):

          @remote.remote(request_type, SimpleResponse)
          def remote_method(self, request):
            pass

      self.assertRaises(TypeError, declare)

  def testBadResponseType(self):
    """Test bad response types used in remote definition."""

    for response_type in (None, 'wrong', messages.Message, str):

      def declare():
        class BadService(object):

          @remote.remote(SimpleRequest, response_type)
          def remote_method(self, request):
            pass

      self.assertRaises(TypeError, declare)


class RequestStateTest(test_util.TestCase):
  """Test request state."""

  def testConstructor(self):
    """Test constructor."""
    state = remote.RequestState(remote_host='remote-host',
                                remote_address='remote-address',
                                server_host='server-host',
                                server_port=10)
    self.assertEquals('remote-host', state.remote_host)
    self.assertEquals('remote-address', state.remote_address)
    self.assertEquals('server-host', state.server_host)
    self.assertEquals(10, state.server_port)

    state = remote.RequestState()
    self.assertEquals(None, state.remote_host)
    self.assertEquals(None, state.remote_address)
    self.assertEquals(None, state.server_host)
    self.assertEquals(None, state.server_port)

  def testConstructorError(self):
    """Test unexpected keyword argument."""
    self.assertRaises(TypeError,
                      remote.RequestState,
                      x=10)

  def testRepr(self):
    """Test string representation."""
    self.assertEquals('<remote.RequestState>', repr(remote.RequestState()))
    self.assertEquals('<remote.RequestState remote_host=abc>',
                      repr(remote.RequestState(remote_host='abc')))
    self.assertEquals('<remote.RequestState remote_host=abc '
                      'remote_address=def>',
                      repr(remote.RequestState(remote_host='abc',
                                               remote_address='def')))
    self.assertEquals('<remote.RequestState remote_host=abc '
                      'remote_address=def '
                      'server_host=ghi>',
                      repr(remote.RequestState(remote_host='abc',
                                               remote_address='def',
                                               server_host='ghi')))
    self.assertEquals('<remote.RequestState remote_host=abc '
                      'remote_address=def '
                      'server_host=ghi '
                      'server_port=102>',
                      repr(remote.RequestState(remote_host='abc',
                                               remote_address='def',
                                               server_host='ghi',
                                               server_port=102)))


class ServiceTest(test_util.TestCase):
  """Test Service class."""

  def testServiceBase_AllRemoteMethods(self):
    """Test that service base class has no remote methods."""
    self.assertEquals({}, remote.Service.all_remote_methods())

  def testServiceBase_GetDescriptor(self):
    """Test that get_descriptor on the Service base class returns descriptor."""
    expected = descriptor.describe_service(remote.Service)
    service = remote.Service()

    self.assertEquals(expected,
                      service.get_descriptor(message_types.VoidMessage()))

  def testAllRemoteMethods(self):
    """Test all_remote_methods with properly Service subclass."""
    self.assertEquals({'remote_method': MyService.remote_method},
                      MyService.all_remote_methods())

  def testAllRemoteMethods_SubClass(self):
    """Test all_remote_methods on a sub-class of a service."""
    class SubClass(MyService):

      @remote.remote(Request, Response)
      def sub_class_method(self, request):
        pass

    self.assertEquals({'remote_method': SubClass.remote_method,
                       'sub_class_method': SubClass.sub_class_method,
                      },
                      SubClass.all_remote_methods())

  def testGetDescriptor(self):
    """Test calling get descriptor on a complex subclass."""
    expected = descriptor.describe_service(MyService)
    service = MyService()

    self.assertEquals(expected,
                      service.get_descriptor(message_types.VoidMessage()))

  def testCallingRemoteMethod(self):
    """Test invoking a remote method."""
    expected = Response()
    expected.value = 'what was passed in'

    request = Request()
    request.value = 'what was passed in'

    service = MyService()
    self.assertEquals(expected, service.remote_method(request))

  def testFactory(self):
    """Test using factory to pass in state."""
    class StatefulService(remote.Service):

      def __init__(self, a, b, c=None):
        self.a = a
        self.b = b
        self.c = c

    state = [1, 2, 3]

    factory = StatefulService.new_factory(1, state)

    self.assertEquals('Creates new instances of service StatefulService.\n\n'
                      'Returns:\n'
                      '  New instance of __main__.StatefulService.',
                      factory.func_doc)
    self.assertEquals('StatefulService_service_factory', factory.func_name)

    service = factory()
    self.assertEquals(1, service.a)
    self.assertEquals(id(state), id(service.b))
    self.assertEquals(None, service.c)

    factory = StatefulService.new_factory(2, b=3, c=4)
    service = factory()
    self.assertEquals(2, service.a)
    self.assertEquals(3, service.b)
    self.assertEquals(4, service.c)

  def testFactoryError(self):
    """Test misusing a factory."""
    # Passing positional argument that is not accepted by class.
    self.assertRaises(TypeError, remote.Service.new_factory(1))

    # Passing keyword argument that is not accepted by class.
    self.assertRaises(TypeError, remote.Service.new_factory(x=1))

    class StatefulService(remote.Service):

      def __init__(self, a):
        pass

    # Missing required parameter.
    self.assertRaises(TypeError, StatefulService.new_factory())

  def testDefinitionName(self):
    """Test getting service definition name."""
    class TheService(remote.Service):
      pass

    self.assertEquals('__main__.TheService', TheService.definition_name())

  def testDefinitionNameWithPackage(self):
    """Test getting service definition name when package defined."""
    global package
    package = 'my.package'
    try:
      class TheService(remote.Service):
        pass

      self.assertEquals('my.package.TheService', TheService.definition_name())
    finally:
      del package

  def testDefinitionNameWithNoModule(self):
    """Test getting service definition name when package defined."""
    module = sys.modules[__name__]
    try:
      del sys.modules[__name__]
      class TheService(remote.Service):
        pass

      self.assertEquals('TheService', TheService.definition_name())
    finally:
      sys.modules[__name__] = module


def main():
  unittest.main()


if __name__ == '__main__':
  main()
