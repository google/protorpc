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

"""Experimental utils.

These utility classes should be considered very unstable.  They might change
and move around unexpectedly.  Use at your own risk.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import logging

from wsgiref import headers as wsgi_headers

from protorpc.experimental import util as exp_util
from protorpc.experimental import filters
from protorpc import messages
from protorpc import remote
from protorpc import util

__all__ = [
  'service_app',
]

_METHOD_PATTERN = r'(?:\.([^?]*))?'


@util.positional(1)
def service_app(service_factory,
                service_path,
                app=None,
                protocols=None):
  if isinstance(service_factory, type):
    service_class = service_factory
  else:
    service_class = service_factory.service_class

  if service_path is None:
    if app != None:
      raise filters.ServiceConfigurationError(
        'Do not provide default application for service with no '
        'explicit service path')
    service_path = r'.*'

  app = app or filters.HTTP_NOT_FOUND

  def service_app_application(environ, start_response):
    # Make sure there is a content-type.
    content_type = environ.get('CONTENT_TYPE')
    if not content_type:
      content_type = environ.get('HTTP_CONTENT_TYPE')
      if not content_type:
        return filters.HTTP_BAD_REQUEST(environ, start_response)

    local_protocols = protocols or environ.get(filters.PROTOCOLS_ENVIRON)

    try:
      config = local_protocols.lookup_by_content_type(content_type)
    except KeyError:
      return filters.HTTP_BAD_REQUEST(environ, start_response)

    # New service instance.
    service_instance = service_class()
    try:
      initialize_request_state = service_instance.initialize_request_state
    except AttributeError:
      pass
    else:
      header_list = []
      for name, value in environ.iteritems():
        if name.startswith('HTTP_'):
          header_list.append((
            name[len('HTTP_'):].lower().replace('_', '-'), value))
      initialize_request_state(remote.HttpRequestState(
        http_method='POST',
        service_path=environ['PATH_INFO.0'],
        headers=header_list,
        remote_host=environ.get('REMOTE_HOST', None),
        remote_address=environ.get('REMOTE_ADDR', None),
        server_host=environ.get('SERVER_HOST', None)))

    # Resolve method.
    method_name = environ['PATH_INFO.1']
    try:
      method = getattr(service_instance, method_name)
    except AttributeError:
      return HTTP_BAD_REQUEST(environ, start_response)

    try:
      remote_info = getattr(method, 'remote')
    except AttributeError:
      return HTTP_BAD_REQUEST(environ, start_response)

    request_type = remote_info.request_type

    # Parse request.
    logging.error(environ)
    body = environ['wsgi.input']
    content = body.read(int(environ['CONTENT_LENGTH']))
    try:
      request = config.protocol.decode_message(request_type, content)
    except messages.DecodeError:
      return HTTP_BAD_REQUEST(environ, start_response)

    # Execute method.
    try:
      response = method(request)
    except:
      return HTTP_INTERNAL_REQUEST_ERROR(environ, start_response)

    # Build and send response.
    try:
      encoded_response = config.protocol.encode_message(response)
    except messages.ValidationError, err:
      return HTTP_INTERNAL_REQUEST_ERROR(environ, start_response)

    start_response('200 OK', [('content-type', content_type),
                              ('content-length', str(len(encoded_response)))])
    return [encoded_response]

  application = service_app_application

  # Must be POST.
  application = filters.environ_equals('REQUEST_METHOD', 'POST',
                                       app=application)

  # Must match request path.  Parses out actual service-path.
  application = filters.match_path(r'(%s)%s' % (service_path, _METHOD_PATTERN),
                                   app=application,
                                   on_error=app)

  if not protocols:
    application = filters.expect_environ(filters.PROTOCOLS_ENVIRON,
                                         app=application)

  return application
