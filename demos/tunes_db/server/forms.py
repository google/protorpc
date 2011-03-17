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

"""Forms interface library for Services API demo.

This contains a set of handlers that will add an automatically generated
form for each API call of a service for any number of services that is defined
within an App engine webapp.  The fields of the form interface generated for
each RPC directly represents a corresponding field in the underlying request
protocol message.  The form is generated in a way such that when a POST is sent
to the server, the body will be compatible with
service_handlers.URLEncodedRPCMapper.

Usage:

  main.py:

    class Hello(messages.Message):

      greeting = messages.StringField(1, required=True)

    class HelloService(remote.Service):

      @remote.method(message_types.VoidMessageType, Hello)
      def world(self, request):
        response = Hello()
        response.greeting = 'Hello World!'
        return response


    registry = ServiceRegistry()
    registry.register_service('/hello', HelloService)

    application = webapp.WSGIApplication(services_registry.mappings())

  main.html:

    <form action='http://mywebapp.example.com/hello/world' method='POST'>
      <input type="submit" name="submit" value="Get Greeting">
    </form>

  Response from post (content-type application/x-www-form-urlencoded):

    greeting=Hello World!
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import logging
import os
import sys

from google.appengine.ext import webapp
from google.appengine.ext.webapp import template

from protorpc import descriptor
from protorpc import messages
from protorpc import remote
from protorpc import service_handlers

from django.utils import simplejson as json


_LOCAL_DIRECTORY = os.path.dirname(__file__)


def message_to_dict(message):
  """Convert a Message instance to a simple dictionary.

  Nested objects are themselves converted to dictionaries.  Enumerated types
  are returned as their string representation.

  The main way to achieve building the a nested object is to define an inner
  recursive function.  The outer function's only responsibility is to check the
  parameters and ensure the message is initialized.

  Values that are set to their defaults are not stored in the dictionary.

  Args:
    message: Message instance to convert to dictionary.

  Returns:
    Dictionary representing the content of the message.

  Raises:
    TypeError if no message is provided.
  """

  def dict_value(value):
    """Convert any value to what is appropriate for use in the result.

    This function recurses when converting elements of repeated fields and
    nested messages.

    Args:
      value: Any message or value stored in a message, including lists from
        repeated fields.

    Returns:
      A value appropriate for storing in the dictionary representation of a
      message.

    Raises:
      TypeError if an unexpected type is found in a Message.
    """
    if value is None or isinstance(value, (int, long, float, basestring)):
      return value

    if isinstance(value, (list, tuple)):
      return [dict_value(item) for item in value]

    if isinstance(value, messages.Enum):
      return str(value)

    if isinstance(value, messages.Message):
      result = {}
      for field in value.all_fields():
        field_value = getattr(value, field.name)
        field_dict_value = dict_value(field_value)
        if field_value is None or field_value in (field.default, (), []):
          continue
        result[field.name] = field_dict_value
      return result

    raise TypeError('Unexpected type')

  if not isinstance(message, messages.Message):
    raise TypeError('Must provide message.')
  message.check_initialized()
  return dict_value(message)


class ServiceRegistry(object):
  """Service registry for tracking all services in a webapp.

  Central registry where service classes are registered at runtime.  The
  registry can provide standard mappings giving a web based forms interface
  to all services registered with it.

  Services are registered by mapping a URL path to the service class.
  """

  def __init__(self, forms_path='/forms'):
    """Constructor.

    Args:
      forms_path: Path on server where the main page for the forms interface is.

    Attributes:
      forms_path: The main forms page that will show all services and methods.
    """
    # __registration_order: List of service URL path mappings used to preserve
    #   the order in which services were registered.  Services are listed in the
    #   web-app mapping in the original order that they were registered.
    # __services: Mapping (url_path) -> service_factory:
    #   url_path: URL path that service is mapped to in web-app.
    #   service_factory: A service handler factory for a service.
    self.forms_path = forms_path
    self.__registration_order = []
    self.__services = {}

  @property
  def services(self):
    """Map of services registered in registry."""
    return dict(self.__services)

  def register_service(self, url_path, service_class):
    """Register a service with the registry.

    Args:
      url_path: URL path to map service to within webapp.  This is the URL
        that most clients that are not using the form interface will use to
        send requests to.
      service_class: The service class to map.
    """
    service_factory = service_handlers.ServiceHandlerFactory(service_class)

    service_factory.add_request_mapper(FormURLEncodedRPCMapper())
    service_factory.add_request_mapper(service_handlers.URLEncodedRPCMapper())
    service_factory.add_request_mapper(service_handlers.ProtobufRPCMapper())
    service_factory.add_request_mapper(service_handlers.JSONRPCMapper())

    self.__registration_order.append(url_path)

    self.__services[url_path] = service_factory

  def mappings(self):
    """Generate a list of mappings for all services and form interfaces.

    Returns:
      A list of web-app mappings.  Creates the following mappings:
        - A main page as specific by self.forms_path containing a list of
          all services and methods with links to form pages for each method.
        - A mapping to each service as defined during registration.
        - Under each service URL a form/file_set URL used for fetching the
          complete JSON representation of the file-set descriptor for that
          service.
    """
    mappings = [(self.forms_path, FormHandler.factory(self)),
               ]
    for url_path in self.__registration_order:
      # TODO(rafek): Probably should map all these to /forms/file_set instead.
      invoke_path = '%s/form/method.(.*)' % url_path
      file_set_path = '%s/form/file_set' % url_path

      mappings.extend([
          (invoke_path, InvocationHandler.factory(self, url_path)),
          (file_set_path, FileSetHandler.factory(self, url_path)),
          ])

      service_factory = self.__services[url_path]
      rpc_mapping = service_factory.mapping(url_path)
      mappings.append(rpc_mapping)
    return mappings


class _HandlerBase(webapp.RequestHandler):
  """Base class for all form handlers."""

  def __init__(self, registry):
    """Constructor.

    Args:
      registry: Service registry to use with form interface.
    """
    self.registry = registry

  @classmethod
  def template_file(self, name):
    """Resolve the path to a template file.

    Args:
      name: Relative file name to template file from this Python file.
    """
    return os.path.join(_LOCAL_DIRECTORY, name)

  @classmethod
  def factory(cls, *args):
    """Create factory for service handler.

    Args:
      args: Parameters to pass to constructor of handler when instantiated by
        the webapp framework.

    Returns:
      Factory that creates new instances of form handler.
    """
    def form_handler_factory():
      return cls(*args)
    return form_handler_factory

  @property
  def service_class(self):
    return self.registry.services[self.url_path].service_factory


class FormHandler(_HandlerBase):
  """Main forms page handler.

  Displays all services with links to methods web forms.
  """

  def get(self):
    registry_view = []
    services = self.registry.services
    for url_path in sorted(services):
      service_class = services[url_path].service_factory
      service_descriptor = descriptor.describe_service(service_class)
      registry_view.append((url_path,
                            service_class.definition_name(),
                            service_descriptor))

    self.response.out.write(
        template.render(self.template_file('forms_static/services.html'),
                        {'registry': registry_view,
                         'forms_path': self.registry.forms_path,
                         }))


# TODO(rafek): Better and easier to just embed the file-set in the main
# invocation handler GET response.
class FileSetHandler(_HandlerBase):
  """Retrieve the whole file-set descriptors in JSON for a service.

  The invocation GET response contains an AJAX call to fetch a JSON
  representation of the file-set for a service in order to dynamically
  build a form.  This handler will send that JSON response.

  See apphosting.ext.services.descriptor.FileSet for more information
  about file-sets.
  """

  def __init__(self, registry, url_path):
    """Constructor.

    Args:
      registry: Service registry to use with form interface.
      url_path: URL path of service to get file-set for.
    """
    super(FileSetHandler, self).__init__(registry)
    self.url_path = url_path

  def get(self):
    # TODO(rafek): This needs to look for external references.  Right now just
    # builds descriptor for immediate service module which works for the demo.
    module = sys.modules[self.service_class.__module__]
    file_set = descriptor.describe_file_set([module])

    self.response.headers['content-type'] = 'application/json'
    self.response.out.write(json.dumps(message_to_dict(file_set)))


class FormURLEncodedRPCMapper(service_handlers.URLEncodedRPCMapper):

  def build_response(self, handler, response):
    """Build text/plain response.

    Response is returned as a pretty-formatted JSON string as a text/plain
    content-type.

    Args:
      handler: RequestHandler instance that is servicing request.
      response: Response message as returned from the service object.
    """
    handler.response.headers['Content-Type'] = 'text/plain'
    handler.response.out.write(json.dumps(message_to_dict(response), indent=2))

  def match_request(self, handler):
    """Match a URL encoded request.

    Requests for the human readable response format should have a parameter
    'response_format' set to 'text/plain'.

    Args:
      handler: RequestHandler instance that is servicing request.

    Returns:
      True if the request is a valid URL encoded RPC request, else False.
    """
    if not handler.request.get('response_format') == 'text/plain':
      return False
    return super(FormURLEncodedRPCMapper, self).match_request(handler)


# TODO(rafek): Maybe there is no need to have a separate POST handler here.
# Implement the JSON protobuf protocol and have the invocation handler generate
# the form and the response entirely dyanamically.
class InvocationHandler(_HandlerBase):
  """Present method form and handle form POST RPCs."""

  def __init__(self, registry, url_path):
    """Constructor.

    Args:
      registry: Service registry to use with form interface.
      url_path: URL path of service to get file-set for.
    """
    super(InvocationHandler, self).__init__(registry)
    self.url_path = url_path

  def get(self, remote_method):
    """Display a form for requested method of service.

    The invoke.html template will contain a function that will call back
    to the file-set handler of the service.  The invoke.js script will complete
    the RPC form for the method when it receives the file-set.

    Args:
      remote_method: Name of method for service to display.
    """
    service_method = getattr(self.service_class, remote_method)
    method = descriptor.describe_method(service_method)

    self.response.out.write(
        template.render(self.template_file('forms_static/invoke.html'),
                        {'service_path': self.url_path,
                         'service_name': self.service_class.definition_name(),
                         'forms_path': self.registry.forms_path,
                         'method': method,
                         'script': 'invoke.js'
                        }))
