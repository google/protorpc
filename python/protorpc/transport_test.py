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

from google.appengine.api import urlfetch
from google.appengine.api import urlfetch_stub
from google.appengine.ext import testbed

from protorpc import messages
from protorpc import protobuf
from protorpc import protojson
from protorpc import remote
from protorpc import test_util
from protorpc import transport
from protorpc import webapp_test_util

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


# Remove when RPC is no longer subclasses.
class TestRpc(transport.Rpc):

  waited = False

  def _wait_impl(self):
    self.waited = True


class RpcTest(test_util.TestCase):

  def setUp(self):
    self.request = Message(value=u'request')
    self.response = Message(value=u'response')
    self.status = remote.RpcStatus(state=remote.RpcState.APPLICATION_ERROR,
                                   error_message='an error',
                                   error_name='blam')

    self.rpc = TestRpc(self.request)

  def testConstructor(self):
    self.assertEquals(self.request, self.rpc.request)
    self.assertEquals(remote.RpcState.RUNNING, self.rpc.state)
    self.assertEquals(None, self.rpc.error_message)
    self.assertEquals(None, self.rpc.error_name)

  def response(self):
    self.assertFalse(self.rpc.waited)
    self.assertEquals(None, self.rpc.response)
    self.assertTrue(self.rpc.waited)

  def testSetResponse(self):
    self.rpc.set_response(self.response)

    self.assertEquals(self.request, self.rpc.request)
    self.assertEquals(remote.RpcState.OK, self.rpc.state)
    self.assertEquals(self.response, self.rpc.response)
    self.assertEquals(None, self.rpc.error_message)
    self.assertEquals(None, self.rpc.error_name)

  def testSetResponseAlreadySet(self):
    self.rpc.set_response(self.response)

    self.assertRaisesWithRegexpMatch(
      transport.RpcStateError,
      'RPC must be in RUNNING state to change to OK',
      self.rpc.set_response,
      self.response)

  def testSetResponseAlreadyError(self):
    self.rpc.set_status(self.status)

    self.assertRaisesWithRegexpMatch(
      transport.RpcStateError,
      'RPC must be in RUNNING state to change to OK',
      self.rpc.set_response,
      self.response)

  def testSetStatus(self):
    self.rpc.set_status(self.status)

    self.assertEquals(self.request, self.rpc.request)
    self.assertEquals(remote.RpcState.APPLICATION_ERROR, self.rpc.state)
    self.assertEquals('an error', self.rpc.error_message)
    self.assertEquals('blam', self.rpc.error_name)
    self.assertRaisesWithRegexpMatch(remote.ApplicationError,
                                     'an error',
                                     getattr, self.rpc, 'response')

  def testSetStatusAlreadySet(self):
    self.rpc.set_response(self.response)

    self.assertRaisesWithRegexpMatch(
      transport.RpcStateError,
      'RPC must be in RUNNING state to change to OK',
      self.rpc.set_response,
      self.response)

  def testSetNonMessage(self):
    self.assertRaisesWithRegexpMatch(
      TypeError,
      'Expected Message type, received 10',
      self.rpc.set_response,
      10)

  def testSetStatusAlreadyError(self):
    self.rpc.set_status(self.status)

    self.assertRaisesWithRegexpMatch(
      transport.RpcStateError,
      'RPC must be in RUNNING state to change to OK',
      self.rpc.set_response,
      self.response)

  def testSetUninitializedStatus(self):
    self.assertRaises(messages.ValidationError,
                      self.rpc.set_status,
                      remote.RpcStatus())


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
    def transport_rpc(remote, rpc_request):
      self.assertEquals(remote, Service.method.remote)
      self.assertEquals(request, rpc_request)
      rpc = TestRpc(request)
      rpc.set_response(response)
      return rpc
    trans._start_rpc = transport_rpc

    rpc = trans.send_rpc(Service.method.remote, request)
    self.assertEquals(response, rpc.response)

  def testDefaultProtocol(self):
    self.do_test(protobuf, transport.Transport())

  def testAlternateProtocol(self):
    self.do_test(protojson, transport.Transport(protocol=protojson))

@remote.method(Message, Message)
def my_method(self, request):
  self.fail('self.my_method should not be directly invoked.')


class HttpTransportUrllibTest(test_util.TestCase):

  def setUp(self):
    super(HttpTransportUrllibTest, self).setUp()
    self.original_urlfetch = transport.urlfetch
    transport.urlfetch = None

    self.trans = transport.HttpTransport('http://myserver/myservice',
                                         protocol=protojson)

    self.request = Message(value=u'The request value')
    self.encoded_request = protojson.encode_message(self.request)

    self.response = Message(value=u'The response value')
    self.encoded_response = protojson.encode_message(self.response)

    self.mox = mox.Mox()
    self.mox.StubOutWithMock(urllib2, 'urlopen')

  def tearDown(self):
    super(HttpTransportUrllibTest, self).tearDown()
    transport.urlfetch = self.original_urlfetch

    self.mox.UnsetStubs()
    self.mox.VerifyAll()

  def VerifyRequest(self, urllib2_request):
    self.assertEquals('http://myserver/myservice.my_method',
                      urllib2_request.get_full_url())
    self.assertEquals(self.encoded_request,
                      urllib2_request.get_data())
    self.assertEquals('application/json',
                      urllib2_request.headers['Content-type'])

    return True

  def testCallSucceeds(self):
    urllib2.urlopen(mox.Func(self.VerifyRequest)).AndReturn(
        StringIO.StringIO(self.encoded_response))

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    self.assertEquals(self.response, rpc.response)

  def testHttpError(self):
    urllib2.urlopen(mox.Func(self.VerifyRequest)).AndRaise(
      urllib2.HTTPError('http://whatever',
                        500,
                        'a server error',
                        {},
                        StringIO.StringIO('does not matter')))

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    rpc.wait()
    self.assertEquals(remote.RpcState.SERVER_ERROR, rpc.state)
    self.assertEquals('HTTP Error 500: a server error',
                      rpc.error_message)
    self.assertEquals(None, rpc.error_name)

  def testErrorCheckedOnResultAttribute(self):
    urllib2.urlopen(mox.Func(self.VerifyRequest)).AndRaise(
      urllib2.HTTPError('http://whatever',
                        500,
                        'a server error',
                        {},
                        StringIO.StringIO('does not matter')))

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    rpc.wait()
    self.assertRaisesWithRegexpMatch(remote.ServerError,
                                     'HTTP Error 500: a server error',
                                     getattr, rpc, 'response')

  def testErrorWithContent(self):
    status = remote.RpcStatus(state=remote.RpcState.REQUEST_ERROR,
                              error_message='an error')
    urllib2.urlopen(mox.Func(self.VerifyRequest)).AndRaise(
        urllib2.HTTPError('http://whatever',
                          500,
                          'An error occured',
                          {'content-type': 'application/json'},
                          StringIO.StringIO(protojson.encode_message(status))))

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    rpc.wait()
    self.assertEquals(remote.RpcState.REQUEST_ERROR, rpc.state)
    self.assertEquals('an error', rpc.error_message)
    self.assertEquals(None, rpc.error_name)

  def testUnparsableErrorContent(self):
    urllib2.urlopen(mox.Func(self.VerifyRequest)).AndRaise(
        urllib2.HTTPError('http://whatever',
                          500,
                          'An error occured',
                          {'content-type': 'application/json'},
                          StringIO.StringIO('a text message is here anyway')))

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    rpc.wait()
    self.assertEquals(remote.RpcState.SERVER_ERROR, rpc.state)
    self.assertEquals('HTTP Error 500: An error occured', rpc.error_message)
    self.assertEquals(None, rpc.error_name)

  def testURLError(self):
    trans = transport.HttpTransport('http://myserver/myservice',
                                    protocol=protojson)

    urllib2.urlopen(mox.IsA(urllib2.Request)).AndRaise(
      urllib2.URLError('a bad connection'))

    self.mox.ReplayAll()

    request = Message(value=u'The request value')
    rpc = trans.send_rpc(my_method.remote, request)
    rpc.wait()
    
    self.assertEquals(remote.RpcState.NETWORK_ERROR, rpc.state)
    self.assertEquals('Network Error: a bad connection', rpc.error_message)
    self.assertEquals(None, rpc.error_name)


class URLFetchResponse(object):

  def __init__(self, content, status_code, headers):
    self.content = content
    self.status_code = status_code
    self.headers = headers


class HttpTransportUrlfetchTest(test_util.TestCase):

  def setUp(self):
    super(HttpTransportUrlfetchTest, self).setUp()

    self.trans = transport.HttpTransport('http://myserver/myservice',
                                         protocol=protojson)

    self.request = Message(value=u'The request value')
    self.encoded_request = protojson.encode_message(self.request)

    self.response = Message(value=u'The response value')
    self.encoded_response = protojson.encode_message(self.response)

    self.mox = mox.Mox()
    self.mox.StubOutWithMock(urlfetch, 'create_rpc')
    self.mox.StubOutWithMock(urlfetch, 'make_fetch_call')

    self.urlfetch_rpc = self.mox.CreateMockAnything()

  def tearDown(self):
    super(HttpTransportUrlfetchTest, self).tearDown()

    self.mox.UnsetStubs()
    self.mox.VerifyAll()

  def ExpectRequest(self,
                    response_content=None,
                    response_code=200,
                    response_headers=None):
    urlfetch.create_rpc().AndReturn(self.urlfetch_rpc)
    urlfetch.make_fetch_call(self.urlfetch_rpc,
                             'http://myserver/myservice.my_method',
                             payload=self.encoded_request,
                             method='POST',
                             headers={'Content-type': 'application/json'})
    if response_content is None:
      response_content = self.encoded_response
    if response_headers is None:
      response_headers = {'content-type': 'application/json'}
    self.urlfetch_response = URLFetchResponse(response_content,
                                              response_code,
                                              response_headers)
    self.urlfetch_rpc.get_result().AndReturn(self.urlfetch_response)

  def testCallSucceeds(self):
    self.ExpectRequest()

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    self.assertEquals(self.response, rpc.response)

  def testCallFails(self):
    self.ExpectRequest('an error', 500, {'content-type': 'text/plain'})

    self.mox.ReplayAll()

    rpc = self.trans.send_rpc(my_method.remote, self.request)
    rpc.wait()
    
    self.assertEquals(remote.RpcState.SERVER_ERROR, rpc.state)
    self.assertEquals('an error', rpc.error_message)
    self.assertEquals(None, rpc.error_name)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
