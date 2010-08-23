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

"""Tests for protorpc.stub."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import new
import os
import StringIO
import sys
import unittest
import urllib2

import test_util
from protorpc import descriptor
from protorpc import messages
from protorpc import protobuf
from protorpc import remote
from protorpc import stub

import mox


class DefineEnumTest(test_util.TestCase):
  """Test for define_enum."""

  def testDefineEnum_Empty(self):
    """Test defining an empty enum."""
    enum_descriptor = descriptor.EnumDescriptor()
    enum_descriptor.name = 'Empty'

    enum_class = stub.define_enum(enum_descriptor, 'whatever')

    self.assertEquals('Empty', enum_class.__name__)
    self.assertEquals('whatever', enum_class.__module__)

    self.assertEquals(enum_descriptor, descriptor.describe_enum(enum_class))

  def testDefineEnum(self):
    """Test defining an enum."""
    red = descriptor.EnumValueDescriptor()
    green = descriptor.EnumValueDescriptor()
    blue = descriptor.EnumValueDescriptor()

    red.name = 'RED'
    red.number = 1
    green.name = 'GREEN'
    green.number = 2
    blue.name = 'BLUE'
    blue.number = 3

    enum_descriptor = descriptor.EnumDescriptor()
    enum_descriptor.name = 'Colors'
    enum_descriptor.values = [red, green, blue]

    enum_class = stub.define_enum(enum_descriptor, 'whatever')

    self.assertEquals('Colors', enum_class.__name__)
    self.assertEquals('whatever', enum_class.__module__)

    self.assertEquals(enum_descriptor, descriptor.describe_enum(enum_class))


class DefineFieldTest(test_util.TestCase):
  """Test for define_field."""

  def testDefineField_Optional(self):
    """Test defining an optional field instance from a method descriptor."""
    field_descriptor = descriptor.FieldDescriptor()

    field_descriptor.name = 'a_field'
    field_descriptor.number = 1
    field_descriptor.variant = descriptor.FieldDescriptor.Variant.INT32
    field_descriptor.label = descriptor.FieldDescriptor.Label.OPTIONAL

    field = stub.define_field(field_descriptor)

    # Name will not be set from the original descriptor.
    self.assertFalse(hasattr(field, 'name'))

    self.assertTrue(isinstance(field, messages.IntegerField))
    self.assertEquals(1, field.number)
    self.assertEquals(descriptor.FieldDescriptor.Variant.INT32, field.variant)
    self.assertFalse(field.required)
    self.assertFalse(field.repeated)

  def testDefineField_Required(self):
    """Test defining a required field instance from a method descriptor."""
    field_descriptor = descriptor.FieldDescriptor()

    field_descriptor.name = 'a_field'
    field_descriptor.number = 1
    field_descriptor.variant = descriptor.FieldDescriptor.Variant.STRING
    field_descriptor.label = descriptor.FieldDescriptor.Label.REQUIRED

    field = stub.define_field(field_descriptor)

    # Name will not be set from the original descriptor.
    self.assertFalse(hasattr(field, 'name'))

    self.assertTrue(isinstance(field, messages.StringField))
    self.assertEquals(1, field.number)
    self.assertEquals(descriptor.FieldDescriptor.Variant.STRING, field.variant)
    self.assertTrue(field.required)
    self.assertFalse(field.repeated)

  def testDefineField_Repeated(self):
    """Test defining a repeated field instance from a method descriptor."""
    field_descriptor = descriptor.FieldDescriptor()

    field_descriptor.name = 'a_field'
    field_descriptor.number = 1
    field_descriptor.variant = descriptor.FieldDescriptor.Variant.DOUBLE
    field_descriptor.label = descriptor.FieldDescriptor.Label.REPEATED

    field = stub.define_field(field_descriptor)

    # Name will not be set from the original descriptor.
    self.assertFalse(hasattr(field, 'name'))

    self.assertTrue(isinstance(field, messages.FloatField))
    self.assertEquals(1, field.number)
    self.assertEquals(descriptor.FieldDescriptor.Variant.DOUBLE, field.variant)
    self.assertFalse(field.required)
    self.assertTrue(field.repeated)

  def testDefineField_Message(self):
    """Test defining a message field."""
    field_descriptor = descriptor.FieldDescriptor()

    field_descriptor.name = 'a_field'
    field_descriptor.number = 1
    field_descriptor.variant = descriptor.FieldDescriptor.Variant.MESSAGE
    field_descriptor.type_name = 'something.yet.to.be.Defined'
    field_descriptor.label = descriptor.FieldDescriptor.Label.REPEATED

    field = stub.define_field(field_descriptor)

    # Name will not be set from the original descriptor.
    self.assertFalse(hasattr(field, 'name'))

    self.assertTrue(isinstance(field, messages.MessageField))
    self.assertEquals(1, field.number)
    self.assertEquals(descriptor.FieldDescriptor.Variant.MESSAGE, field.variant)
    self.assertFalse(field.required)
    self.assertTrue(field.repeated)
    self.assertRaisesWithRegexpMatch(messages.DefinitionNotFoundError,
                                     'Could not find definition for '
                                     "'something.yet.to.be.Defined'.",
                                     getattr, field, 'type')

  def testDefineField_Enum(self):
    """Test defining an enum field."""
    field_descriptor = descriptor.FieldDescriptor()

    field_descriptor.name = 'a_field'
    field_descriptor.number = 1
    field_descriptor.variant = descriptor.FieldDescriptor.Variant.ENUM
    field_descriptor.type_name = 'something.yet.to.be.Defined'
    field_descriptor.label = descriptor.FieldDescriptor.Label.REPEATED

    field = stub.define_field(field_descriptor)

    # Name will not be set from the original descriptor.
    self.assertFalse(hasattr(field, 'name'))

    self.assertTrue(isinstance(field, messages.EnumField))
    self.assertEquals(1, field.number)
    self.assertEquals(descriptor.FieldDescriptor.Variant.ENUM, field.variant)
    self.assertFalse(field.required)
    self.assertTrue(field.repeated)
    self.assertRaisesWithRegexpMatch(messages.DefinitionNotFoundError,
                                     'Could not find definition for '
                                     "'something.yet.to.be.Defined'.",
                                     getattr, field, 'type')


class DefineMessageTest(test_util.TestCase):
  """Test for define_message."""

  def testDefineMessageEmpty(self):
    """Test definition a message with no fields or enums."""
    class AMessage(messages.Message):
      pass

    message_descriptor = descriptor.describe_message(AMessage)

    message_class = stub.define_message(message_descriptor, '__main__')

    self.assertEquals('AMessage', message_class.__name__)
    self.assertEquals('__main__', message_class.__module__)

    self.assertEquals(message_descriptor,
                      descriptor.describe_message(message_class))

  def testDefineMessageEnumOnly(self):
    """Test definition a message with only enums."""
    class AMessage(messages.Message):
      class NestedEnum(messages.Enum):
        pass

    message_descriptor = descriptor.describe_message(AMessage)

    message_class = stub.define_message(message_descriptor, '__main__')

    self.assertEquals('AMessage', message_class.__name__)
    self.assertEquals('__main__', message_class.__module__)

    self.assertEquals(message_descriptor,
                      descriptor.describe_message(message_class))

  def testDefineMessageFieldsOnly(self):
    """Test definition a message with only fields."""
    class AMessage(messages.Message):

      field1 = messages.IntegerField(1)
      field2 = messages.StringField(2)

    message_descriptor = descriptor.describe_message(AMessage)

    message_class = stub.define_message(message_descriptor, '__main__')

    self.assertEquals('AMessage', message_class.__name__)
    self.assertEquals('__main__', message_class.__module__)

    self.assertEquals(message_descriptor,
                      descriptor.describe_message(message_class))

  def testDefineMessage(self):
    """Test defining Message class from descriptor."""
    class AMessage(messages.Message):
      class NestedEnum(messages.Enum):
        pass

      field1 = messages.IntegerField(1)
      field2 = messages.StringField(2)

    message_descriptor = descriptor.describe_message(AMessage)

    message_class = stub.define_message(message_descriptor, '__main__')

    self.assertEquals('AMessage', message_class.__name__)
    self.assertEquals('__main__', message_class.__module__)

    self.assertEquals(message_descriptor,
                      descriptor.describe_message(message_class))


class HTTPTransportTest(test_util.TestCase):
  """Test the HTTP transport."""

  def setUp(self):
    """Set up mox."""
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(urllib2, 'urlopen')

  def tearDown(self):
    """Tear down and verify mox."""
    self.mox.UnsetStubs()
    self.mox.VerifyAll()

  def testSendRPC(self):
    """Test sending a blocking RPC."""
    transport = stub.HTTPTransport('http://myserver/myservice')

    class MyRequest(messages.Message):
      request_value = messages.StringField(1)

    class MyResponse(messages.Message):
      response_value = messages.StringField(1)

    @remote.remote(MyRequest, MyResponse)
    def mymethod(request):
      self.fail('mymethod should not be directly invoked.')

    request = MyRequest()
    request.request_value = u'The request value'
    encoded_request = protobuf.encode_message(request)

    response = MyResponse()
    response.response_value = u'The response value'
    encoded_response = protobuf.encode_message(response)

    def verify_request(urllib2_request):
      self.assertEquals('http://myserver/myservice/mymethod',
                        urllib2_request.get_full_url())
      self.assertEquals(urllib2_request.get_data(), encoded_request)
      self.assertEquals('application/x-google-protobuf',
                        urllib2_request.headers['Content-type'])

      return True

    # First call succeeds.
    urllib2.urlopen(mox.Func(verify_request)).AndReturn(
        StringIO.StringIO(encoded_response))

    # Second call raises an HTTP error.
    urllib2.urlopen(mox.Func(verify_request)).AndRaise(
        urllib2.HTTPError('http://whatever',
                          404,
                          'Not Found',
                          {},
                          StringIO.StringIO('')))

    self.mox.ReplayAll()

    actual_response = transport.send_rpc(mymethod.remote, request)
    self.assertEquals(response, actual_response)

    self.assertRaises(stub.RPCError,
                      transport.send_rpc, mymethod.remote, request)


class ServiceProxyTest(test_util.TestCase):
  """Test the ServiceProxy class."""

  def setUp(self):
    self.mox = mox.Mox()

  def testInvokeProxyMethod(self):
    """Test creating an invoking a proxy method."""

    class MyRequest(messages.Message):
      request_value = messages.StringField(1)

    class MyResponse(messages.Message):
      response_value = messages.StringField(1)

    class MyService(stub.ServiceProxy):
      remote_method = stub.ServiceProxy.define_proxy_method(
          'remote_method',
          MyRequest,
          MyResponse)

    transport = self.mox.CreateMock(stub.HTTPTransport)
    service = MyService(transport)

    request = MyRequest()
    request.request_value = u'Request value'

    response = MyResponse()
    response.response_value = u'Response value'

    transport.send_rpc(MyService.remote_method.remote, request).AndReturn(
        response)

    self.mox.ReplayAll()

    self.assertEquals(service.remote_method(request), response)

    self.mox.VerifyAll()


class DefineServiceTest(test_util.TestCase):
  """Test service proxy definition."""

  def setUp(self):
    """Set up mock and request classes."""
    self.mox = mox.Mox()

    self.module = new.module('stocks')

    class GetQuoteRequest(messages.Message):
      __module__ = 'stocks'

      symbols = messages.StringField(1, repeated=True)

    class GetQuoteResponse(messages.Message):
      __module__ = 'stocks'

      prices = messages.IntegerField(1, repeated=True)

    self.module.GetQuoteRequest = GetQuoteRequest
    self.module.GetQuoteResponse = GetQuoteResponse

  def testDefineService(self):
    """Test service definition from descriptor."""
    method_descriptor = descriptor.MethodDescriptor()
    method_descriptor.name = 'get_quote'
    method_descriptor.request_type = 'GetQuoteRequest'
    method_descriptor.response_type = 'GetQuoteResponse'

    service_descriptor = descriptor.ServiceDescriptor()
    service_descriptor.name = 'Stocks'
    service_descriptor.methods = [method_descriptor]

    StockService = stub.define_service(service_descriptor, self.module)

    transport = self.mox.CreateMock(stub.HTTPTransport)

    request = self.module.GetQuoteRequest()
    request.symbols = ['GOOG', 'AAPL']

    response = self.module.GetQuoteResponse()
    response.prices = [70000, 13000]

    transport.send_rpc(StockService.get_quote.remote, request).AndReturn(
        response)

    self.mox.ReplayAll()

    service = StockService(transport)
    service.get_quote(request)

    self.mox.VerifyAll()


class ModuleTest(test_util.TestCase):
  """Test for module creation and importation functions."""

  def MakeFileDescriptor(self, package):
    """Helper method to construct FileDescriptors.

    Creates FileDescriptor with a MessageDescriptor and an EnumDescriptor.

    Args:
      package: Package name to give new file descriptors.

    Returns:
      New FileDescriptor instance.
    """
    enum_descriptor = descriptor.EnumDescriptor()
    enum_descriptor.name = u'MyEnum'

    message_descriptor = descriptor.MessageDescriptor()
    message_descriptor.name = u'MyMessage'

    service_descriptor = descriptor.ServiceDescriptor()
    service_descriptor.name = u'MyService'

    file_descriptor = descriptor.FileDescriptor()
    file_descriptor.package = package
    file_descriptor.enums = [enum_descriptor]
    file_descriptor.messages = [message_descriptor]
    file_descriptor.services = [service_descriptor]

    return file_descriptor

  def testDefineModule(self):
    """Test define_module function."""
    file_descriptor = self.MakeFileDescriptor('my.package')

    module = stub.define_file(file_descriptor)

    self.assertEquals('my.package', module.__name__)
    self.assertEquals('my.package', module.MyEnum.__module__)
    self.assertEquals('my.package', module.MyMessage.__module__)
    self.assertEquals('my.package', module.MyService.__module__)

    self.assertEquals(file_descriptor, descriptor.describe_file(module))

  def testDefineModule_ReuseModule(self):
    """Test updating module with additional definitions."""
    file_descriptor = self.MakeFileDescriptor('my.package')

    module = new.module('override')
    self.assertEquals(module, stub.define_file(file_descriptor, module))

    self.assertEquals('override', module.MyEnum.__module__)
    self.assertEquals('override', module.MyMessage.__module__)
    self.assertEquals('override', module.MyService.__module__)

    # One thing is different between original descriptor and new.
    file_descriptor.package = 'override'
    self.assertEquals(file_descriptor, descriptor.describe_file(module))

  def testImportFile(self):
    """Test importing FileDescriptor in to module space."""
    modules = {}
    file_descriptor = self.MakeFileDescriptor('standalone')
    stub.import_file(file_descriptor, modules)
    self.assertEquals(file_descriptor,
                      descriptor.describe_file(modules['standalone']))

  def testImportFile_InToExisting(self):
    """Test importing FileDescriptor in to existing module."""
    module = new.module('standalone')
    modules = {'standalone': module}
    file_descriptor = self.MakeFileDescriptor('standalone')
    stub.import_file(file_descriptor, modules)
    self.assertEquals(module, modules['standalone'])
    self.assertEquals(file_descriptor,
                      descriptor.describe_file(modules['standalone']))

  def testImportFile_InToGlobalModules(self):
    """Test importing FileDescriptor in to global modules."""
    original_modules = sys.modules
    try:
      sys.modules = dict(sys.modules)
      if 'standalone' in sys.modules:
        del sys.modules['standalone']
      file_descriptor = self.MakeFileDescriptor('standalone')
      stub.import_file(file_descriptor)
      self.assertEquals(file_descriptor,
                        descriptor.describe_file(sys.modules['standalone']))
    finally:
      sys.modules = original_modules

  def testImportFile_Nested(self):
    """Test importing FileDescriptor in to existing nested module."""
    modules = {}
    file_descriptor = self.MakeFileDescriptor('root.nested')
    stub.import_file(file_descriptor, modules)
    self.assertEquals(modules['root'].nested, modules['root.nested'])
    self.assertEquals(file_descriptor,
                      descriptor.describe_file(modules['root.nested']))

  def testImportFile_NoPackage(self):
    """Test importing FileDescriptor with no package."""
    file_descriptor = self.MakeFileDescriptor('does not matter')
    file_descriptor.reset('package')
    self.assertRaisesWithRegexpMatch(ValueError,
                                     'File descriptor must have package name.',
                                     stub.import_file,
                                     file_descriptor)

  def testImportFileSet(self):
    """Test importing a whole file set."""
    file_set = descriptor.FileSet()
    file_set.files = [self.MakeFileDescriptor(u'standalone'),
                      self.MakeFileDescriptor(u'root.nested'),
                      self.MakeFileDescriptor(u'root.nested.nested'),
    ]

    root = new.module('root')
    nested = new.module('root.nested')
    root.nested = nested
    modules = {
        'root': root,
        'root.nested': nested,
    }

    stub.import_file_set(file_set, modules)

    self.assertEquals(root, modules['root'])
    self.assertEquals(nested, modules['root.nested'])
    self.assertEquals(nested.nested, modules['root.nested.nested'])

    self.assertEquals(file_set,
                      descriptor.describe_file_set(
                          [modules['standalone'],
                           modules['root.nested'],
                           modules['root.nested.nested'],
                          ]))

  def testImportFileSetFromFile(self):
    """Test importing a whole file set from a file."""
    file_set = descriptor.FileSet()
    file_set.files = [self.MakeFileDescriptor(u'standalone'),
                      self.MakeFileDescriptor(u'root.nested'),
                      self.MakeFileDescriptor(u'root.nested.nested'),
    ]

    stream = StringIO.StringIO(protobuf.encode_message(file_set))

    self.mox = mox.Mox()
    opener = self.mox.CreateMockAnything()
    opener('my-file.dat', 'rb').AndReturn(stream)

    self.mox.ReplayAll()

    modules = {}
    stub.import_file_set('my-file.dat', modules, _open=opener)

    self.assertEquals(file_set,
                      descriptor.describe_file_set(
                          [modules['standalone'],
                           modules['root.nested'],
                           modules['root.nested.nested'],
                          ]))


if __name__ == '__main__':
  unittest.main()
