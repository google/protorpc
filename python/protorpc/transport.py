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

import sys
import urllib2

from protorpc import messages
from protorpc import protobuf
from protorpc import util

__all__ = [
  'RpcError',

  'HttpTransport',
  'Rpc',
  'Transport',
]


class RpcError(messages.Error):
  """Error occurred during RPC."""


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

  @property
  def request(self):
    """Request associated with RPC."""
    return self.__request

  def set_response(self, response):
    """Set successful response.

    Transport will set response upon successful non-error completion of RPC.

    Args:
      response: Response message from RPC.
    """
    self.__response = response

  def get_response(self):
    """Returns response received from transport."""
    return self.__response


class Transport(object):
  """Transport base class.

  Provides basic support for implementing a ProtoRPC transport such as one
  that can send and receive messages over HTTP.

  Implementations override _transport_rpc.  This method receives an encoded
  response as determined by the transports configured protocol.  The transport
  is expected to set the rpc response or raise an exception before termination.

  Asynchronous transports are not supported.
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
      An Rpc instance intialized with request and response.
    """
    request.check_initialized()
    encoded_request = self.__protocol.encode_message(request)
    rpc = Rpc(request)

    self._transport_rpc(remote_info, encoded_request, rpc)

    return rpc

  def _transport_rpc(self, remote_info, encoded_request, rpc):
    """Transport RPC method.

    Args:
      remote_info: RemoteInfo instance describing remote method.
      encoded_request: Request message as encoded by transport protocol.
      rpc: Rpc instance associated with a single request.
    """
    raise NotImplementedError()


class HttpTransport(Transport):
  """Transport for communicating with HTTP servers."""

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

  def _transport_rpc(self, remote_info, encoded_request, rpc):
    """HTTP transport rpc method.

    Uses urllib2 as underlying HTTP transport.
    """
    method_url = '%s.%s' % (self.__service_url, remote_info.method.func_name)
    http_request = urllib2.Request(method_url, encoded_request)
    http_request.add_header('content-type', self.protocol.CONTENT_TYPE)

    try:
      http_response = urllib2.urlopen(http_request)
    except urllib2.HTTPError, err:
      _, _, trace_back = sys.exc_info()
      raise RpcError, 'HTTP error: %s' % str(err), trace_back

    encoded_response = http_response.read()
    response = self.protocol.decode_message(remote_info.response_type,
                                            encoded_response)
    rpc.set_response(response)
