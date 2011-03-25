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

"""Remote service library.

This module contains classes that are useful for building remote services that
conform to a standard request and response model.  To conform to this model
a service must be like the following class:

  # Each service instance only handles a single request and is then discarded.
  # Make these objects light weight.
  class Service(object):

    # It must be possible to construct service objects without any parameters.
    # If your constructor needs extra information you should provide a
    # no-argument factory function to create service instances.
    def __init__(self):
      ...

    # Each remote method must use the 'remote' decorator, passing the request
    # and response message types.  The remote method itself must take a single
    # parameter which is an instance of RequestMessage and return an instance
    # of ResponseMessage.
    @method(RequestMessage, ResponseMessage)
    def remote_method(self, request):
      # Return an instance of ResponseMessage.

    # A service object may optionally implement a 'initialize_request_state'
    # method that takes as a parameter a single instance of a RequestState.  If
    # a service does not implement this method it will not receive the request
    # state.
    def initialize_request_state(self, state):
      ...

The 'Service' class is provided as a convenient base class that provides the
above functionality.  It implements all required and optional methods for a
service.  It also has convenience methods for creating factory functions that
can pass persistent global state to a new service instance.

The 'remote' decorator is used to declare which methods of a class are
meant to service RPCs.  While this decorator is not responsible for handling
actual remote method invocations, such as handling sockets, handling various
RPC protocols and checking messages for correctness, it does attach information
to methods that responsible classes can examine and ensure the correctness
of the RPC.

When the remote decorator is used on a method, the wrapper method will have a
'remote' property associated with it.  The 'remote' property contains the
request_type and response_type expected by the methods implementation.

On its own, the remote decorator does not provide any support for subclassing
remote methods.  In order to extend a service, one would need to redecorate
the sub-classes methods.  For example:

  class MyService(Service):

    @method(DoSomethingRequest, DoSomethingResponse)
    def do_something(self, request):
      ... implement do-something ...

  class MyBetterService(Service):

    @method(DoSomethingRequest, DoSomethingResponse)
    def do_something(self, request):
      response = super(MyService, self).do_something.remote.method(request)
      ... do something with response ...
      return response

A Service subclass also has a Stub class that can be used with a transport for
making RPCs.  When a stub is created, it is capable of doing both synchronous
and asynchronous RPCs if the underlying transport supports it.  To make a stub
using an HTTP transport do:

  my_service = MyService.Stub(HttpTransport('<my service URL>'))

For synchronous calls, just call the expected methods on the service stub:

  request = DoSomethingRequest()
  ...
  response = my_service.do_something(request)

Each stub instance has an async object that can be used for initiating
asynchronous RPCs if the underlying protocol transport supports it.  To
make an asynchronous call, do:

  rpc = my_service.async.do_something(request)
  response = rpc.get_response()

Public Classes:
  RequestState: Encapsulates information specific to an individual request.
  Service: Base class useful for implementing service objects.

Public Functions:
  remote: Decorator for indicating remote methods.

Public Exceptions:
  InvalidRequestError: Raised when wrong request objects received by service.
  InvalidResponseError: Raised when wrong response object sent from service.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import logging
import sys

from protorpc import message_types
from protorpc import messages
from protorpc import descriptor
from protorpc import util


__all__ = [
    'InvalidRequestError',
    'InvalidResponseError',
    'ServiceDefinitionError',

    'Service',
    'StubBase',
    'RequestState',
    'get_remote_method_info',
    'method',
    'remote',
]


class InvalidRequestError(messages.Error):
  """Raised when wrong request objects received during method invocation."""


class InvalidResponseError(messages.Error):
  """Raised when wrong response objects returned during method invocation."""


class ServiceDefinitionError(messages.Error):
  """Raised when a service is improperly defined."""


class _RemoteMethodInfo(object):
  """Object for encapsulating remote method information.

  An instance of this method is associated with the 'remote' attribute
  of the methods 'invoke_remote_method' instance.

  Instances of this class are created by the remote decorator and should not
  be created directly.
  """

  def __init__(self,
               method,
               request_type,
               response_type):
    """Constructor.

    Args:
      method: The method which implements the remote method.  This is a
        function that will act as an instance method of a class definition
        that is decorated by '@method'.  It must always take 'self' as its
        first parameter.
      request_type: Expected request type for the remote method.
      response_type: Expected response type for the remote method.
    """
    self.__method = method
    self.__request_type = request_type
    self.__response_type = response_type

  @property
  def method(self):
    """Original undecorated method."""
    return self.__method

  @property
  def request_type(self):
    """Expected request type for remote method."""
    if isinstance(self.__request_type, basestring):
      self.__request_type = messages.find_definition(
        self.__request_type,
        relative_to=sys.modules[self.__method.__module__])
    return self.__request_type

  @property
  def response_type(self):
    """Expected response type for remote method."""
    if isinstance(self.__response_type, basestring):
      self.__response_type = messages.find_definition(
        self.__response_type,
        relative_to=sys.modules[self.__method.__module__])
    return self.__response_type


def method(request_type, response_type):
  """Method decorator for creating remote methods.

  Args:
    request_type: Message type of expected request.
    response_type: Message type of expected response.

  Returns:
    'remote_method_wrapper' function.

  Raises:
    TypeError: if the request_type or response_type parameters are not
      proper subclasses of messages.Message.
  """
  if (not isinstance(request_type, basestring) and
      (not isinstance(request_type, type) or
       not issubclass(request_type, messages.Message) or
       request_type is messages.Message)):
    raise TypeError(
        'Must provide message class for request-type.  Found %s',
        request_type)

  if (not isinstance(response_type, basestring) and
      (not isinstance(response_type, type) or
       not issubclass(response_type, messages.Message) or
       response_type is messages.Message)):
    raise TypeError(
        'Must provide message class for response-type.  Found %s',
        response_type)

  def remote_method_wrapper(method):
    """Decorator used to wrap method.

    Args:
      method: Original method being wrapped.

    Returns:
      'invoke_remote_method' function responsible for actual invocation.
      This invocation function instance is assigned an attribute 'remote'
      which contains information about the remote method:
        request_type: Expected request type for remote method.
        response_type: Response type returned from remote method.

    Raises:
      TypeError: If request_type or response_type is not a subclass of Message
        or is the Message class itself.
    """

    def invoke_remote_method(service_instance, request):
      """Function used to replace original method.

      Invoke wrapped remote method.  Checks to ensure that request and
      response objects are the correct types.

      Does not check whether messages are initialized.

      Args:
        service_instance: The service object whose method is being invoked.
          This is passed to 'self' during the invocation of the original
          method.
        request: Request message.

      Returns:
        Results of calling wrapped remote method.

      Raises:
        InvalidRequestError: Request object is not of the correct type.
        InvalidResponseError: Response object is not of the correct type.
      """
      if not isinstance(request, remote_method_info.request_type):
        raise InvalidRequestError('Method %s.%s expected request type %s, '
                                  'received %s' %
                                  (type(service_instance).__name__,
                                   method.__name__,
                                   remote_method_info.request_type,
                                   type(request)))
      response = method(service_instance, request)
      if not isinstance(response, remote_method_info.response_type):
        raise InvalidResponseError('Method %s.%s expected response type %s, '
                                   'sent %s' %
                                   (type(service_instance).__name__,
                                    method.__name__,
                                    remote_method_info.response_type,
                                    type(response)))
      return response

    remote_method_info = _RemoteMethodInfo(method,
                                           request_type,
                                           response_type)

    invoke_remote_method.remote = remote_method_info
    invoke_remote_method.__name__ = method.__name__
    return invoke_remote_method

  return remote_method_wrapper


def remote(request_type, response_type):
  """Temporary backward compatibility alias for method."""
  logging.warning('The remote decorator has been renamed method.  It will be '
                  'removed in very soon from future versions of ProtoRPC.')
  return method(request_type, response_type)


def get_remote_method_info(method):
  """Get remote method info object from remote method.

  Returns:
    Remote method info object if method is a remote method, else None.
  """
  if not callable(method):
    return None

  try:
    method_info = method.remote
  except AttributeError:
    return None

  if not isinstance(method_info, _RemoteMethodInfo):
    return None

  return method_info


class StubBase(object):
  """Base class for client side service stubs.

  The remote method stubs are created by the _ServiceClass meta-class
  when a Service class is first created.  The resulting stub will
  extend both this class and the service class it handles communications for.

  Assume that there is a service:

    class NewContactRequest(messages.Message):

      name = messages.StringField(1, required=True)
      phone = messages.StringField(2)
      email = messages.StringField(3)

    class AccountService(remote.Service):

      @remote.method(NewContact, message_types.VoidMessage):
      def new_contact(self, request):
        ... implementation ...

  A stub of this service can be called in two ways.  The first is to pass in a
  correctly initialized NewContactRequest message:

    request = NewContactRequest()
    request.name = 'Bob Somebody'
    request.phone = '+1 415 555 1234'
    
    account_service_stub.new_contact(request)

  The second way is to pass in keyword parameters that correspond with the root
  request message type:

      account_service_stub.new_contact(name='Bob Somebody',
                                       phone='+1 415 555 1234')

  The second form will create a request message of the appropriate type.
  """

  def __init__(self, transport):
    """Constructor.

    Args:
      transport: Underlying transport to communicate with remote service.
    """
    self.__transport = transport

  @property
  def transport(self):
    """Transport used to communicate with remote service."""
    return self.__transport

  @classmethod
  def definition_name(self):
    """Delegates to underlying service instance."""
    return super(StubBase, self).definition_name()


class _ServiceClass(type):
  """Meta-class for service class."""
   
  def __new_async_method(cls, remote):
    """Create asynchronous method for Async handler.

    Args:
      remote: RemoteInfo to create method for.
    """
    def async_method(self, *args, **kwargs):
      """Asynchronous remote method.

      Args:
        self: Instance of StubBase.Async subclass.

        Stub methods either take a single positional argument when a full
        request message is passed in, or keyword arguments, but not both.

        See docstring for StubBase for more information on how to use remote
        stub methods.

      Returns:
        Rpc instance used to represent asynchronous RPC.
      """
      if args and kwargs:
        raise TypeError('May not provide both args and kwargs')

      if not args:
        # Construct request object from arguments.
        request = remote.request_type()
        for name, value in kwargs.iteritems():
          setattr(request, name, value)
      else:
        # First argument is request object.
        request = args[0]

      return self.transport.send_rpc(remote, request)

    async_method.__name__ = remote.method.__name__
    async_method = util.positional(2)(async_method)
    async_method.remote = remote
    return async_method

  def __new_sync_method(cls, async_method):
    """Create synchronous method for stub.

    Args:
      async_method: asynchronous method to delegate calls to.
    """
    def sync_method(self, *args, **kwargs):
      """Synchronous remote method.

      Args:
        self: Instance of StubBase.Async subclass.
        args: Tuple (request,):
          request: Request object.
        kwargs: Field values for request.  Must be empty if request object
          is provided.

      Returns:
        Response message from synchronized RPC.
      """
      return async_method(self.async, *args, **kwargs).get_response()
    sync_method.__name__ = async_method.__name__
    sync_method.remote = async_method.remote
    return sync_method

  def __create_async_methods(cls, remote_methods):
    """Construct a dictionary of asynchronous methods based on remote methods.

    Args:
      remote_methods: Dictionary of methods with associated RemoteInfo objects.

    Returns:
      Dictionary of asynchronous methods with assocaited RemoteInfo objects.
      Results added to AsyncStub subclass.
    """
    async_methods = {}
    for method_name, method in remote_methods.iteritems():
      async_methods[method_name] = cls.__new_async_method(method.remote)
    return async_methods

  def __create_sync_methods(cls, async_methods):
    """Construct a dictionary of synchronous methods based on remote methods.

    Args:
      async_methods: Dictionary of async methods to delegate calls to.

    Returns:
      Dictionary of synchronous methods with assocaited RemoteInfo objects.
      Results added to Stub subclass.
    """
    sync_methods = {}
    for method_name, async_method in async_methods.iteritems():
      sync_methods[method_name] = cls.__new_sync_method(async_method)
    return sync_methods

  def __new__(cls, name, bases, dct):
    """Instantiate new service class instance."""
    if StubBase not in bases:
      # Collect existing remote methods.
      base_methods = {}
      for base in bases:
        try:
          remote_methods = base.__remote_methods
        except AttributeError:
          pass
        else:
          base_methods.update(remote_methods)

      # Set this class private attribute so that base_methods do not have
      # to be recacluated in __init__.
      dct['_ServiceClass__base_methods'] = base_methods

      for attribute, value in dct.iteritems():
        base_method = base_methods.get(attribute, None)
        if base_method:
          if not callable(value):
            raise ServiceDefinitionError(
              'Must override %s in %s with a method.' % (
                attribute, name))

          if get_remote_method_info(value):
            raise ServiceDefinitionError(
              'Do not use remote decorator when overloading remote method %s '
              'on service %s.' %
              (attribute, name))

          base_remote_method_info = get_remote_method_info(base_method)
          remote_decorator = method(
            base_remote_method_info.request_type,
            base_remote_method_info.response_type)
          new_remote_method = remote_decorator(value)
          dct[attribute] = new_remote_method

    return type.__new__(cls, name, bases, dct)

  def __init__(cls, name, bases, dct):
    """Create uninitialized state on new class."""
    type.__init__(cls, name, bases, dct)

    # Only service implementation classes should have remote methods and stub
    # sub classes created.  Stub implementations have their own methods passed
    # in to the type constructor.
    if StubBase not in bases:
      # Create list of remote methods.
      cls.__remote_methods = dict(cls.__base_methods)

      for attribute, value in dct.iteritems():
        value = getattr(cls, attribute)
        remote_method_info = get_remote_method_info(value)
        if remote_method_info:
          cls.__remote_methods[attribute] = value

      # Build asynchronous stub class.
      stub_attributes = {'Service': cls}
      async_methods = cls.__create_async_methods(cls.__remote_methods)
      stub_attributes.update(async_methods)
      async_class = type('AsyncStub', (StubBase, cls), stub_attributes)
      cls.AsyncStub = async_class

      # Constructor for synchronous stub class.
      def __init__(self, transport):
        """Constructor.

        Args:
          transport: Underlying transport to communicate with remote service.
        """
        super(cls.Stub, self).__init__(transport)
        self.async = cls.AsyncStub(transport)

      # Build synchronous stub class.
      stub_attributes = {'Service': cls,
                         '__init__': __init__}
      stub_attributes.update(cls.__create_sync_methods(async_methods))
     
      cls.Stub = type('Stub', (StubBase, cls), stub_attributes)

  @staticmethod
  def all_remote_methods(cls):
    """Get all remote methods of service.

    Returns:
      Dict from method name to unbound method.
    """
    return dict(cls.__remote_methods)


class RequestState(object):
  """Request state information.

  Attributes:
    remote_host: Remote host name where request originated.
    remote_address: IP address where request originated.
    server_host: Host of server within which service resides.
    server_port: Post which service has recevied request from.
  """

  @util.positional(1)
  def __init__(self,
               remote_host=None,
               remote_address=None,
               server_host=None,
               server_port=None):
    """Constructor.

    Args:
      remote_host: Assigned to attribute.
      remote_address: Assigned to attribute.
      server_host: Assigned to attribute.
      server_port: Assigned to attribute.
    """
    self.remote_host = remote_host
    self.remote_address = remote_address
    self.server_host = server_host
    self.server_port = server_port

  def __repr__(self):
    """String representation of state."""
    state = []
    if self.remote_host:
      state.append(('remote_host', self.remote_host))
    if self.remote_address:
      state.append(('remote_address', self.remote_address))
    if self.server_host:
      state.append(('server_host', self.server_host))
    if self.server_port:
      state.append(('server_port', self.server_port))

    if state:
      state_string = ' ' + ' '.join(
          '%s=%s' % (name, value) for (name, value) in state)
    else:
      state_string = ''

    return '<remote.RequestState%s>' % state_string


class Service(object):
  """Service base class.

  Base class used for defining remote services.  Contains reflection functions,
  useful helpers and built-in remote methods.

  Services are expected to be constructed via either a constructor or factory
  which takes no parameters.  However, it might be required that some state or
  configuration is passed in to a service across multiple requests.

  To do this, define parameters to the constructor of the service and use
  the 'new_factory' class method to build a constructor that will transmit
  parameters to the constructor.  For example:

    class MyService(Service):

      def __init__(self, configuration, state):
        self.configuration = configuration
        self.state = state

    configuration = MyServiceConfiguration()
    global_state = MyServiceState()

    my_service_factory = MyService.new_factory(configuration,
                                               state=global_state)

  The contract with any service handler is that a new service object is created
  to handle each user request, and that the construction does not take any
  parameters.  The factory satisfies this condition:

    new_instance = my_service_factory()
    assert new_instance.state is global_state

  Attributes:
    request_state: RequestState set via initialize_request_state.
  """

  __metaclass__ = _ServiceClass

  @classmethod
  def all_remote_methods(cls):
    """Get all remote methods for service class.

    Built-in methods do not appear in the dictionary of remote methods.

    Returns:
      Dictionary mapping method name to remote method.
    """
    return _ServiceClass.all_remote_methods(cls)

  @classmethod
  def new_factory(cls, *args, **kwargs):
    """Create factory for service.

    Useful for passing configuration or state objects to the service.  Accepts
    arbitrary parameters and keywords, however, underlying service must accept
    also accept not other parameters in its constructor.

    Args:
      args: Args to pass to service constructor.
      kwargs: Keyword arguments to pass to service constructor.

    Returns:
      Factory function that will create a new instance and forward args and
      keywords to the constructor.
    """
    def service_factory():
      return cls(*args, **kwargs)

    # Update docstring so that it is easier to debug.
    full_class_name = '%s.%s' % (cls.__module__, cls.__name__)
    service_factory.func_doc = (
        'Creates new instances of service %s.\n\n'
        'Returns:\n'
        '  New instance of %s.'
        % (cls.__name__, full_class_name))

    # Update name so that it is easier to debug the factory function.
    service_factory.func_name = '%s_service_factory' % cls.__name__

    service_factory.service_class = cls

    return service_factory

  def initialize_request_state(self, request_state):
    """Save request state for use in remote method.

    Args:
      request_state: RequestState instance.
    """
    self.__request_state = request_state

  @classmethod
  def definition_name(cls):
    """Get definition name for Service class.

    Package name is determined by the global 'package' attribute in the
    module that contains the Service definition.  If no 'package' attribute
    is available, uses module name.  If no module is found, just uses class
    name as name.

    Returns:
      Fully qualified service name.
    """
    try:
      return cls.__definition_name
    except AttributeError:
      module = sys.modules.get(cls.__module__)
      if module:
        try:
          package = module.package
        except AttributeError:
          package = cls.__module__
        cls.__definition_name = '%s.%s' % (package, cls.__name__)
      else:
        cls.__definition_name = cls.__name__

      return cls.__definition_name


  @property
  def request_state(self):
    """Request state associated with this Service instance."""
    return self.__request_state
