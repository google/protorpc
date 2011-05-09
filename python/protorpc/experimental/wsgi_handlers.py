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

"""WSGI application for protorpc.

This module contains classes that may be used to build a service
on top of WSGI using Pythons built in wsgiref:

  http://www.wsgi.org

The services request handler can be configured to handle requests in a number
of different request formats.  All different request formats must have a way
to map the request to the service handlers defined request message.Message
class.  The handler can also send a response in any format that can be mapped
from the response message.Message class.

Participants in an RPC:

  There are three classes involved with the life cycle of an RPC.

    Service factory: A user-defined service factory that is responsible for
      instantiating an RPC service.  The methods intended for use as RPC
      methods must be decorated by the 'remote' decorator.

    Protocols: Responsible for determining whether or not a specific request
      matches a particular RPC format and translating between the actual
      request/response and the underlying message types.  A single instance of
      Protocols is used to resolve to multiple ProtocolConfig instances.
      The ProtocolConfig instance determines the mapping between content-types
      and underlying protocol format implementations.

    ServiceApp: A class that implements the WSGI application interface.  It
      mediates between the Protocols and service implementation class during a
      request.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import logging
import re
import wsgiref
from wsgiref import util as wsgiref_util

from protorpc import remote
from protorpc import util

__all__ = [
  'Error',
  'ServiceConfigurationError',
  'RequestError',
  'ResponseError',

  'ProtocolConfig',
  'Protocols',
  'ServiceApp',
]

# The whole method pattern is an optional regex.  It contains a single
# group used for mapping to the query parameter.  This is passed to the
# parameters of 'get' and 'post' on the ServiceHandler.
_METHOD_PATTERN = r'(?:\.([^?]*))?'


class Error(Exception):
  """Base class for all errors in service handlers module."""


class ServiceConfigurationError(Error):
  """When service configuration is incorrect."""


class RequestError(Error):
  """Error occurred when building request."""


class ResponseError(Error):
  """Error occurred when building response."""


class ProtocolConfig(object):
  """Configuration for single protocol mapping.

  A read-only protocol configuration provides a given protocol implementation
  with a name and a set of content-types that it recognizes.

  Properties:
    protocol: The protocol implementation for configuration (for example,
      protojson, protobuf, etc.).
    name: Name of protocol configuration.
    default_content_type: The default content type for the protocol.
    alternative_content_types: A list of alternative content-types supported
      by the protocol.  Must not contain the default content-type, nor
      duplicates.
    content_types: A list of all content-types supported by configuration.
      Combination of default content-type and alternatives.
  """

  def __init__(self,
               protocol,
               name,
               default_content_type=None,
               alternative_content_types=None):
    """Constructor.

    Args:
      protocol: The protocol implementation for configuration.
      name: The name of the protocol configuration.
      default_content_type: The default content-type for protocol.  If none
        provided it will check protocol.CONTENT_TYPE.
      alternative_content_types:  A list of content-types.

    Raises:
      ServiceConfigurationError if there are any duplicate content-types.
    """
    self.__protocol = protocol
    self.__name = name
    self.__default_content_type = default_content_type or protocol.CONTENT_TYPE
    self.__alternative_content_types = tuple(alternative_content_types or [])
    self.__content_types = (
      (self.__default_content_type,) + self.__alternative_content_types)
    previous_type = object()
    for content_type in sorted(self.content_types):
      if content_type == previous_type:
        raise ServiceConfigurationError(
          'Duplicate content-type %s' % content_type)
      previous_type = content_type

  @property
  def protocol(self):
    return self.__protocol

  @property
  def name(self):
    return self.__name

  @property
  def default_content_type(self):
    return self.__default_content_type

  @property
  def alternate_content_types(self):
    return self.__alternative_content_types

  @property
  def content_types(self):
    return self.__content_types


class Protocols(object):
  """Collection of protocol configurations.

  Used to describe a complete set of content-type mappings for multiple
  protocol configurations.

  Properties:
    names: Sorted list of the names of registered protocols.
    content_types: Sorted list of supported content-types.
  """

  def __init__(self):
    """Constructor."""
    self.__by_name = {}
    self.__by_content_type = {}

  def add_protocol_config(self, config):
    """Add a protocol configuration to protocol mapping.

    Args:
      config: A ProtocolConfig.

    Raises:
      ServiceConfigurationError if protocol.name is already registered
        or any of it's content-types are already registered.
    """
    if config.name in self.__by_name:
      raise ServiceConfigurationError(
        'Protocol name %r is already in use' % config.name)
    for content_type in config.content_types:
      if content_type in self.__by_content_type:
        raise ServiceConfigurationError(
          'Content type %r is already in use' % content_type)

    self.__by_name[config.name] = config
    self.__by_content_type.update((t, config) for t in config.content_types)

  def add_protocol(self, *args, **kwargs):
    """Add a protocol configuration from basic parameters.

    Simple helper method that creates and registeres a ProtocolConfig instance.
    """
    self.add_protocol_config(ProtocolConfig(*args, **kwargs))

  @property
  def names(self):
    return tuple(sorted(self.__by_name))

  @property
  def content_types(self):
    return tuple(sorted(self.__by_content_type))

  def lookup_by_name(self, name):
    """Look up a ProtocolConfig by name.

    Args:
      name: Name of protocol to look for.

    Returns:
      ProtocolConfig associated with name.

    Raises:
      KeyError if there is no protocol for name.
    """
    return self.__by_name[name]

  def lookup_by_content_type(self, content_type):
    """Look up a ProtocolConfig by content-type.

    Args:
      content_type: Content-type to find protocol configuration for.

    Returns:
      ProtocolConfig associated with content-type.

    Raises:
      KeyError if there is no protocol for content-type.
    """
    return self.__by_content_type[content_type]


class ServiceApp(object):
  """WSGI compatible application instance that wraps a single service."""

  def __init__(self, service_factory, service_path=None, protocols=None):
    """Constructor.

    Args:
      service_factory: Service factory or Service class that will serve RPC
        requests to this application.
      service_path: Regular expression that describes the expected request
        service path.  If none provided, will translate the service definition
        name to the service path.  For example:

          some.package.SomeService -> /some/package/SomeService

        The paths of incoming requests are matched against the service_path
        regular expression.  Non-matching paths generate 404.
      protocols: Protocols instance.  An empty instance is created if none is
        provided.
    """
    if (isinstance(service_factory, type) and
        issubclass(service_factory, remote.Service)):
      service_class = service_factory
    else:
      service_class = service_factory.service_class

    if service_path is None:
      service_path = '/' + service_class.definition_name().replace('.', '/')

    self.__service_factory = service_factory
    self.__service_path = service_path
    self.__service_class = service_class
    self.__service_path_regex = re.compile('(%s)%s' % (service_path,
                                                       _METHOD_PATTERN))
    self.__protocols = protocols

    self.__protocol_names = {}
    self.__content_types = {}
    self.__default_content_types = {}

  @property
  def service_factory(self):
    return self.__service_factory

  @property
  def service_path(self):
    return self.__service_path

  @property
  def service_class(self):
    return self.__service_class

  @property
  def protocols(self):
    return self.__protocols

  def run_application(self, environ, start_response):
    """Run the WSGI application."""
    protocols = self.__protocols or environ['protorpc.protocols']

    def http_error(status):
      """Helper function that returns an error to client."""
      logging.debug('HTTP Error %s', status)
      content_type = environ.get('CONTENT_TYPE', None)
      if content_type is not None:
        try:
          protocols.lookup_by_content_type(content_type)
        except KeyError:
          content_type = None
      if content_type is None:
        content_type = 'text/html'
      start_response(
        status,
        [('content-length', '0'), ('content-type', content_type)])

    # Match path.
    request_path = environ['PATH_INFO']
    path_match = self.__service_path_regex.match(request_path)
    if not path_match:
      http_error('404 Request path %r does not match service path r%r' %
                 (request_path, self.__service_path))
      return

    service_path = path_match.group(1)
    method_name = path_match.group(2)

    # Check HTTP method.
    # TODO(rafek): Allow for other methods.
    http_method = environ['REQUEST_METHOD']
    if http_method != 'POST':
      http_error('404 HTTP method %s not supported' % http_method)
      return

    # Create service instance.
    service_instance = self.__service_factory()

    # Resolve service method.
    service_method = getattr(service_instance, method_name, None)
    try:
      remote_info = service_method.remote
    except AttributeError:
      remote_info = None
    if not (service_method and remote_info):
      http_error('400 No such remote method "%s"' % method_name)
      return

    # Resolve protocol.
    content_type = environ.get('CONTENT_TYPE', None)
    if not content_type:
      http_error('400 Must provide content-type for ProtoRPC requests')
      return

    try:
      protocol_config = protocols.lookup_by_content_type(content_type)
    except KeyError:
      http_error('400 Unrecognized content-type %s for '
                 'ProtoRPC request' % content_type)
      return
    protocol = protocol_config.protocol

    # Get the body.
    content_length = int(environ.get('CONTENT_LENGTH') or '-1')
    if content_length < 0:
      body = environ['wsgi.input'].read()
    else:
      body = environ['wsgi.input'].read(content_length)

    # Parse content
    request_message = protocol.decode_message(
      service_method.remote.request_type, body)

    # Call method
    response_message = service_method(request_message)

    # Send response
    response_body = protocol.encode_message(response_message)
    response_headers = [
      ('content-type', content_type),
      ('content-length', str(len(response_body))),
    ]

    start_response('200 OK', response_headers)
    yield response_body

  def __call__(self, *params):
    """Wrapps run_application."""
    return self.run_application(*params)
