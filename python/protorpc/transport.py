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

"""Transport library for ProtoRPC.

Contains underlying infrastructure used for communicating RPCs over low level
transports such as HTTP.

Includes HTTP transport built over urllib2.
"""

import logging
import sys
import urllib2

from protorpc import messages
from protorpc import protobuf
from protorpc import remote
from protorpc import util

try:
  from google.appengine.api import urlfetch
except ImportError:
  urlfetch = None

__all__ = [
  'RpcStateError',

  'HttpTransport',
  'Rpc',
  'Transport',
]


class RpcStateError(messages.Error):
  """Raised when trying to put RPC in to an invalid state."""


class Rpc(object):
  """Represents a client side RPC.

  An RPC is created by the transport class and is used with a single RPC.  While
  an RPC is still in process, the response is set to None.  When it is complete
  the response will contain the response message.
  """

  def __init__(self, request):
    """Constructor.

    Args:
      request: Request associated with this RPC.
    """
    self.__request = request
    self.__response = None
    self.__state = remote.RpcState.RUNNING
    self.__error_message = None
    self.__error_name = None

  @property
  def request(self):
    """Request associated with RPC."""
    return self.__request

  @property
  def response(self):
    """Response associated with RPC."""
    self.wait()
    return self.__response

  @property
  def state(self):
    """State associated with RPC."""
    return self.__state

  @property
  def error_message(self):
    """Error, if any, associated with RPC."""
    self.wait()
    return self.__error_message

  @property
  def error_name(self):
    """Error name, if any, associated with RPC."""
    self.wait()
    return self.__error_name

  def wait(self):
    """Wait for an RPC to finish."""
    if self.__state == remote.RpcState.RUNNING:
      self._wait_impl()

  def _wait_impl(self):
    """Implementation for wait()."""
    raise NotImplementedError()

  def __set_state(self, state, error_message=None, error_name=None):
    if self.__state != remote.RpcState.RUNNING:
      raise RpcStateError(
        'RPC must be in RUNNING state to change to %s' % state)
    if state == remote.RpcState.RUNNING:
      raise RpcStateError('RPC is already in RUNNING state')
    self.__state = state
    self.__error_message = error_message
    self.__error_name = error_name

  def set_response(self, response):
    # TODO: Even more specific type checking.
    if not isinstance(response, messages.Message):
      raise TypeError('Expected Message type, received %r' % (response))

    self.__response = response
    self.__set_state(remote.RpcState.OK)

  def set_status(self, status):
    status.check_initialized()
    self.__set_state(status.state, status.error_message, status.error_name)


class Transport(object):
  """Transport base class.

  Provides basic support for implementing a ProtoRPC transport such as one
  that can send and receive messages over HTTP.

  Implementations override _start_rpc.  This method receives a RemoteInfo
  instance and a request Message. The transport is expected to set the rpc
  response or raise an exception before termination.
  """

  @util.positional(1)
  def __init__(self, protocol=protobuf):
    """Constructor.

    Args:
      protocol: The protocol implementation.  Must implement encode_message and
        decode_message.
    """
    self.__protocol = protocol

  @property
  def protocol(self):
    """Protocol associated with this transport."""
    return self.__protocol

  def send_rpc(self, remote_info, request):
    """Initiate sending an RPC over the transport.

    Args:
      remote_info: RemoteInfo instance describing remote method.
      request: Request message to send to service.

    Returns:
      An Rpc instance intialized with the request..
    """
    request.check_initialized()

    rpc = self._start_rpc(remote_info, request)

    return rpc

  def _start_rpc(self, remote_info, request):
    """Start a remote procedure call.

    Args:
      remote_info: RemoteInfo instance describing remote method.
      request: Request message to send to service.

    Returns:
      An Rpc instance initialized with the request.
    """
    raise NotImplementedError()


class HttpTransport(Transport):
  """Transport for communicating with HTTP servers."""

  class __HttpRequest(object):
    """Base class for library-specific requests."""

    def __init__(self, method_url, transport, encoded_request):
      """Constructor.

      Args:
        method_url: The URL where the method is located.
        transport: The Transport instance making the request.
      """
      self._method_url = method_url
      self._transport = transport

      self._start_request(encoded_request)

    def _http_error_to_exception(self, content_type, content):
      protocol = self._transport.protocol
      if content_type == protocol.CONTENT_TYPE:
        try:
          rpc_status = protocol.decode_message(remote.RpcStatus, content)
        except Exception, decode_err:
          logging.warning(
            'An error occurred trying to parse status: %s\n%s',
            str(decode_err), content)
        else:
          # TODO: Move the check_rpc_status to the Rpc.response property.
          # Will raise exception if rpc_status is in an error state.
          remote.check_rpc_status(rpc_status)

    def _start_request(self):
      raise NotImplementedError()

    def get_response(self):
      raise NotImplementedError()


  class __UrlfetchRequest(__HttpRequest):
    """Request cycle for a remote call using urlfetch."""

    __urlfetch_rpc = None

    def _start_request(self, encoded_request):
      """Initiate async call."""

      self.__urlfetch_rpc = urlfetch.create_rpc()

      headers = {
        'Content-type': self._transport.protocol.CONTENT_TYPE
      }

      urlfetch.make_fetch_call(self.__urlfetch_rpc,
                               self._method_url,
                               payload=encoded_request,
                               method='POST',
                               headers=headers)

    def get_response(self):
      """Get the encoded response for the request."""

      try:
        http_response = self.__urlfetch_rpc.get_result()

        if http_response.status_code >= 400:
          self._http_error_to_exception(
            http_response.headers.get('content-type'),
            http_response.content)

          raise remote.ServerError, (http_response.content, http_response)

      except urlfetch.DownloadError, err:
        raise remote.NetworkError, (str(err), err)

      except urlfetch.InvalidURLError, err:
        raise remote.RequestError, 'Invalid URL, received: %s' % (
          self.__urlfetch.request.url())

      except urlfetch.ResponseTooLargeError:
        raise remote.NetworkError(
          'The response data exceeded the maximum allowed size.')

      return http_response.content


  class __UrllibRequest(__HttpRequest):
    """Request cycle for a remote call using Urllib."""

    def _start_request(self, encoded_request):
      """Create the urllib2 request. """

      http_request = urllib2.Request(self._method_url, encoded_request)
      http_request.add_header('Content-type',
                              self._transport.protocol.CONTENT_TYPE)

      self.__http_request = http_request

    def get_response(self):
      """Get the encoded response for request."""

      try:
        http_response = urllib2.urlopen(self.__http_request)
      except urllib2.HTTPError, err:
        if err.code >= 400:
          self._http_error_to_exception(err.hdrs.get('content-type'), err.msg)

        # TODO: Map other types of errors to appropriate exceptions.
        _, _, trace_back = sys.exc_info()
        raise remote.ServerError, (err.msg, err), trace_back

      except urllib2.URLError, err:
        _, _, trace_back = sys.exc_info()
        if isinstance(err, basestring):
          error_message = err
        else:
          error_message = err.args[0]
        raise remote.NetworkError, (error_message, err), trace_back

      return http_response.read()

  @util.positional(2)
  def __init__(self, service_url, protocol=protobuf):
    """Constructor.

    Args:
      service_url: URL where the service is located.  All communication via
        the transport will go to this URL.
      protocol: The protocol implementation.  Must implement encode_message and
        decode_message.
    """
    super(HttpTransport, self).__init__(protocol=protocol)
    self.__service_url = service_url

    if urlfetch:
      self.__request_type = self.__UrlfetchRequest
    else:
      self.__request_type = self.__UrllibRequest

  def _start_rpc(self, remote_info, request):
    """Start a remote procedure call.

    Args:
      remote_info: A RemoteInfo instance for this RPC.
      request: The request message for this RPC.

    Returns:
      An Rpc instance initialized with a Request.
    """
    method_url = '%s.%s' % (self.__service_url, remote_info.method.func_name)
    encoded_request = self.protocol.encode_message(request)

    http_request = self.__request_type(method_url=method_url,
                                       transport=self,
                                       encoded_request=encoded_request)

    rpc = Rpc(request)

    def wait_impl():
      """Implementation of _wait for an Rpc."""
      encoded_response = http_request.get_response()
      response = self.protocol.decode_message(remote_info.response_type,
                                              encoded_response)
      rpc.set_response(response)

    rpc._wait_impl = wait_impl

    return rpc
