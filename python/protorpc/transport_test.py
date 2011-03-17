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

import StringIO
import types
import unittest
import urllib2

from protorpc import messages
from protorpc import protobuf
from protorpc import protojson
from protorpc import test_util
from protorpc import remote
from protorpc import transport

import mox


class ModuleInterfaceTest(test_util.ModuleInterfaceTest,
                          test_util.TestCase):

  MODULE = transport


class Message(messages.Message):

  value = messages.StringField(1)


class Service(remote.Service):
  
  @remote.method(Message, Message)
  def method(self, request):
    pass


class RpcTest(test_util.TestCase):

  def testRpc(self):

    request = Message()
    request.value = u'request'
    rpc = transport.Rpc(request)
    self.assertEquals(request, rpc.request)

    response = Message()
    response.value = u'response'
    rpc.set_response(response)
    self.assertEquals(response, rpc.get_response())


class TransportTest(test_util.TestCase):

  def do_test(self, protocol, trans):
    request = Message()
    request.value = u'request'

    response = Message()
    response.value = u'response'

    encoded_request = protocol.encode_message(request)
    encoded_response = protocol.encode_message(response)

    self.assertEquals(protocol, trans.protocol)

    received_rpc = [None]
    def transport_rpc(remote, data, rpc):
      received_rpc[0] = rpc
      self.assertEquals(remote, Service.method.remote)
      self.assertEquals(encoded_request, data)
      self.assertTrue(isinstance(rpc, transport.Rpc))
      self.assertEquals(request, rpc.request)
      self.assertEquals(None, rpc.get_response())
      rpc.set_response(response)
    trans._transport_rpc = transport_rpc

    rpc = trans.send_rpc(Service.method.remote, request)
    self.assertEquals(received_rpc[0], rpc)

  def testDefaultProtocol(self):
    self.do_test(protobuf, transport.Transport())

  def testAlternateProtocol(self):
    self.do_test(protojson, transport.Transport(protocol=protojson))


class HttpTransportTest(test_util.TestCase):

  def setUp(self):
    self.mox = mox.Mox()
    self.mox.StubOutWithMock(urllib2, 'urlopen')

  def tearDown(self):
    self.mox.UnsetStubs()
    self.mox.VerifyAll()

  def do_test_send_rpc(self, protocol):
    trans = transport.HttpTransport('http://myserver/myservice',
                                    protocol=protocol)

    class MyRequest(messages.Message):
      request_value = messages.StringField(1)

    class MyResponse(messages.Message):
      response_value = messages.StringField(1)

    @remote.method(MyRequest, MyResponse)
    def mymethod(request):
      self.fail('mymethod should not be directly invoked.')

    request = MyRequest()
    request.request_value = u'The request value'
    encoded_request = protocol.encode_message(request)

    response = MyResponse()
    response.response_value = u'The response value'
    encoded_response = protocol.encode_message(response)

    def verify_request(urllib2_request):
      self.assertEquals('http://myserver/myservice.mymethod',
                        urllib2_request.get_full_url())
      self.assertEquals(urllib2_request.get_data(), encoded_request)
      self.assertEquals(protocol.CONTENT_TYPE,
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

    actual_rpc = trans.send_rpc(mymethod.remote, request)
    self.assertEquals(response, actual_rpc.get_response())

    self.assertRaises(transport.RpcError,
                      trans.send_rpc, mymethod.remote, request)

  def testSendProtobuf(self):
    self.do_test_send_rpc(protobuf)

  def testSendProtobuf(self):
    self.do_test_send_rpc(protojson)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
