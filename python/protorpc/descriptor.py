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

"""Services descriptor definitions.

Contains message definitions and functions for converting
service classes into transmittable message format.

Describing an Enum instance, Enum class, Field class or Message class will
generate an appropriate descriptor object that describes that class.
This message can itself be used to transmit information to clients wishing
to know the description of an enum value, enum, field or message without
needing to download the source code.  This format is also compatible with
other, non-Python languages.

The descriptors are modeled to be binary compatible with:

  http://code.google.com/p/protobuf/source/browse/trunk/src/google/protobuf/descriptor.proto

NOTE: The names of types and fields are not always the same between these
descriptors and the ones defined in descriptor.proto.  This was done in order
to make source code files that use these descriptors easier to read.  For
example, it is not necessary to prefix TYPE to all the values in
FieldDescriptor.Variant as is done in descriptor.proto FieldDescriptorProto.Type.

Example:

  class Pixel(messages.Message):

    x = messages.IntegerField(1, required=True)
    y = messages.IntegerField(2, required=True)

    color = messages.BytesField(3)

  # Describe Pixel class using message descriptor.
  fields = []

  field = FieldDescriptor()
  field.name = 'x'
  field.number = 1
  field.label = FieldDescriptor.Label.REQUIRED
  field.variant = FieldDescriptor.Variant.INT64

  field = FieldDescriptor()
  field.name = 'y'
  field.number = 2
  field.label = FieldDescriptor.Label.REQUIRED
  field.variant = FieldDescriptor.Variant.INT64

  field = FieldDescriptor()
  field.name = 'color'
  field.number = 3
  field.label = FieldDescriptor.Label.OPTIONAL
  field.variant = FieldDescriptor.Variant.BYTES

  message = MessageDescriptor()
  message.name = 'Pixel'
  message.fields = fields

  # Describing is the equivalent of building the above message.
  message == describe_message(Pixel)

Public Classes:
  EnumValueDescriptor: Describes Enum values.
  EnumDescriptor: Describes Enum classes.
  FieldDescriptor: Describes field instances.
  FileDescriptor: Describes a single 'file' unit.
  FileSet: Describes a collection of file descriptors.
  MessageDescriptor: Describes Message classes.
  MethodDescriptor: Describes a method of a service.
  ServiceDescriptor: Describes a services.

Public Functions:
  describe_enum_value: Describe an individual enum-value.
  describe_enum: Describe an Enum class.
  describe_field: Describe a Field definition.
  describe_file: Describe a 'file' unit from a Python module or object.
  describe_file_set: Describe a file set from a list of modules or objects.
  describe_message: Describe a Message definition.
  describe_method: Describe a Method definition.
  describe_service: Describe a Service definition.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import codecs

from protorpc import messages


__all__ = ['EnumDescriptor',
           'EnumValueDescriptor',
           'FieldDescriptor',
           'MessageDescriptor',
           'MethodDescriptor',
           'FileDescriptor',
           'FileSet',
           'ServiceDescriptor',

           'describe_enum',
           'describe_enum_value',
           'describe_field',
           'describe_message',
           'describe_method',
           'describe_file',
           'describe_file_set',
           'describe_service',
          ]


# NOTE: MessageField is missing because message fields cannot have
# a default value at this time.
# TODO(rafek): Support default message values.
#
# Map to functions that convert default values of fields of a given type
# to a string.  The function must return a value that is compatible with
# FieldDescriptor.default_value and therefore a unicode string.
_DEFAULT_TO_STRING_MAP = {
    messages.IntegerField: unicode,
    messages.FloatField: unicode,
    messages.BooleanField: lambda value: value and u'true' or u'false',
    messages.BytesField: lambda value: _from_utf_8(
        codecs.escape_encode(value)[0]),
    messages.StringField: lambda value: value,
    messages.EnumField: lambda value: _from_utf_8(str(value.number)),
}


class EnumValueDescriptor(messages.Message):
  """Enum value descriptor.

  Fields:
    name: Name of enumeration value.
    number: Number of enumeration value.
  """

  # TODO(rafek): Why are these listed as optional in descriptor.proto.
  # Harmonize?
  name = messages.StringField(1, required=True)
  number = messages.IntegerField(2,
                                 required=True,
                                 variant=messages.Variant.INT32)


class EnumDescriptor(messages.Message):
  """Enum class descriptor.

  Fields:
    name: Name of Enum without any qualification.
    values: Values defined by Enum class.
  """

  name = messages.StringField(1)
  values = messages.MessageField(EnumValueDescriptor, 2, repeated=True)


class FieldDescriptor(messages.Message):
  """Field definition descriptor.

  Enums:
    Variant: Wire format hint sub-types for field.
    Label: Values for optional, required and repeated fields.

  Fields:
    name: Name of field.
    number: Number of field.
    variant: Variant of field.
    type_name: Type name for message and enum fields.
    default_value: String representation of default value.
  """

  Variant = messages.Variant

  class Label(messages.Enum):
    """Field label."""

    OPTIONAL = 1
    REQUIRED = 2
    REPEATED = 3

  name = messages.StringField(1, required=True)
  number = messages.IntegerField(3,
                                 required=True,
                                 variant=messages.Variant.INT32)
  label = messages.EnumField(Label, 4, default=Label.OPTIONAL)
  variant = messages.EnumField(Variant, 5)
  type_name = messages.StringField(6)

  # For numeric types, contains the original text representation of the value.
  # For booleans, "true" or "false".
  # For strings, contains the default text contents (not escaped in any way).
  # For bytes, contains the C escaped value.  All bytes < 128 are that are
  #   traditionally considered unprintable are also escaped.
  default_value = messages.StringField(7)


class MessageDescriptor(messages.Message):
  """Message definition descriptor.

  Fields:
    name: Name of Message without any qualification.
    fields: Fields defined for message.
    enums: Nested Enum classes defined on message.
  """

  name = messages.StringField(1)
  fields = messages.MessageField(FieldDescriptor, 2, repeated=True)

  # TODO(rafek): Support nested type.  Requires self-referencing.
  enums = messages.MessageField(EnumDescriptor, 4, repeated=True)


class MethodDescriptor(messages.Message):
  """Service method definition descriptor.

  Fields:
    name: Name of service method.
    request_type: Fully qualified or relative name of request message type.
    response_type: Fully qualified or relative name of response message type.
  """

  name = messages.StringField(1)

  request_type = messages.StringField(2)
  response_type = messages.StringField(3)


class ServiceDescriptor(messages.Message):
  """Service definition descriptor.

  Fields:
    name: Name of Service without any qualification.
    methods: Remote methods of Service.
  """

  name = messages.StringField(1)

  methods = messages.MessageField(MethodDescriptor, 2, repeated=True)


class FileDescriptor(messages.Message):
  """Description of file containing protobuf definitions.

  Fields:
    package: Fully qualified name of package that definitions belong to.
    messages: Message definitions contained in file.
    enums: Enum definitions contained in file.
    services: Service definitions contained in file.
  """

  # Temporary local variable to disambiguate message module from message field.
  messages_module = messages

  package = messages_module.StringField(2)

  # TODO(rafek): Add dependency field

  messages = messages_module.MessageField(MessageDescriptor, 4, repeated=True)
  enums = messages_module.MessageField(EnumDescriptor, 5, repeated=True)
  services = messages_module.MessageField(ServiceDescriptor, 6, repeated=True)

  del messages_module


class FileSet(messages.Message):
  """A collection of FileDescriptors.

  Fields:
    files: Files in file-set.
  """

  files = messages.MessageField(FileDescriptor, 1, repeated=True)


def _from_utf_8(string_value):
  """Helper function to hide conversion of strings from utf-8 to unicode.

  Args:
    string_value: str or unicode to convert to unicode encoded str.

  Returns:
    UTF-8 decoded unicode if string_value is str, else string_value.
  """
  if isinstance(string_value, str):
    return string_value.decode('utf-8')
  else:
    assert isinstance(string_value, unicode)
    return string_value


def describe_enum_value(enum_value):
  """Build descriptor for Enum instance.

  Args:
    enum_value: Enum value to provide descriptor for.

  Returns:
    Initialized EnumValueDescriptor instance describing the Enum instance.
  """
  enum_value_descriptor = EnumValueDescriptor()
  enum_value_descriptor.name = unicode(enum_value.name)
  enum_value_descriptor.number = enum_value.number
  return enum_value_descriptor


def describe_enum(enum_definition):
  """Build descriptor for Enum class.

  Args:
    enum_definition: Enum class to provide descriptor for.

  Returns:
    Initialized EnumDescriptor instance describing the Enum class.
  """
  enum_descriptor = EnumDescriptor()
  enum_descriptor.name = enum_definition.definition_name().split('.')[-1]

  values = []
  for number in enum_definition.numbers():
    value = enum_definition.lookup_by_number(number)
    values.append(describe_enum_value(value))

  if values:
    enum_descriptor.values = values

  return enum_descriptor


def describe_field(field_definition):
  """Build descriptor for Field instance.

  Args:
    field_definition: Field instance to provide descriptor for.

  Returns:
    Initialized FieldDescriptor instance describing the Field instance.
  """
  field_descriptor = FieldDescriptor()
  field_descriptor.name = _from_utf_8(field_definition.name)
  field_descriptor.number = field_definition.number
  field_descriptor.variant = field_definition.variant

  if isinstance(field_definition, (messages.EnumField, messages.MessageField)):
    field_descriptor.type_name = field_definition.type.definition_name()

  if field_definition.default is not None:
    field_descriptor.default_value = _DEFAULT_TO_STRING_MAP[
        type(field_definition)](field_definition.default)

  # Set label.
  if field_definition.repeated:
    field_descriptor.label = FieldDescriptor.Label.REPEATED
  elif field_definition.required:
    field_descriptor.label = FieldDescriptor.Label.REQUIRED
  else:
    field_descriptor.label = FieldDescriptor.Label.OPTIONAL

  return field_descriptor


def describe_message(message_definition):
  """Build descriptor for Message class.

  Args:
    message_definition: Message class to provide descriptor for.

  Returns:
    Initialized MessageDescriptor instance describing the Message class.
  """
  message_descriptor = MessageDescriptor()
  message_descriptor.name = message_definition.definition_name().split('.')[-1]

  fields = sorted(message_definition.all_fields(),
                  key=lambda v: v.number)
  if fields:
    message_descriptor.fields = [describe_field(field) for field in fields]

  try:
    nested_enums = message_definition.__enums__
  except AttributeError:
    pass
  else:
    enums = []
    for name in nested_enums:
      value = getattr(message_definition, name)
      if isinstance(value, type) and issubclass(value, messages.Enum):
        enums.append(describe_enum(value))

    message_descriptor.enums = enums

  return message_descriptor


def describe_method(method):
  """Build descriptor for service method.

  Args:
    method: Remote service method to describe.

  Returns:
    Initialized MethodDescriptor instance describing the service method.
  """
  method_info = method.remote
  descriptor = MethodDescriptor()
  descriptor.name = _from_utf_8(method_info.method.func_name)
  descriptor.request_type = _from_utf_8(
      method_info.request_type.definition_name())
  descriptor.response_type = _from_utf_8(
      method_info.response_type.definition_name())

  return descriptor


def describe_service(service_class):
  """Build descriptor for service.

  Args:
    service_class: Service class to describe.

  Returns:
    Initialized ServiceDescriptor instance describing the service.
  """
  descriptor = ServiceDescriptor()
  descriptor.name = _from_utf_8(service_class.__name__)
  methods = []
  remote_methods = service_class.all_remote_methods()
  for name in sorted(remote_methods.iterkeys()):
    if name == 'get_descriptor':
      continue

    method = remote_methods[name]
    methods.append(describe_method(method))
  if methods:
    descriptor.methods = methods

  return descriptor


def describe_file(module):
  """Build a file from a specified Python module.

  Args:
    module: Python module to describe.

  Returns:
    Initialized FileDescriptor instance describing the module.
  """
  # May not import remote at top of file because remote depends on this
  # file
  # TODO(rafek): Straighten out this dependency.  Possibly move these functions
  # from descriptor to their own module.
  import remote

  descriptor = FileDescriptor()
  try:
    descriptor.package = _from_utf_8(module.package)
  except AttributeError:
    descriptor.package = _from_utf_8(module.__name__)

  message_descriptors = []
  enum_descriptors = []
  service_descriptors = []

  # Need to iterate over all top level attributes of the module looking for
  # message, enum and service definitions.  Each definition must be itself
  # described.
  for name in sorted(dir(module)):
    value = getattr(module, name)

    if isinstance(value, type):
      if issubclass(value, messages.Message):
        message_descriptors.append(describe_message(value))

      elif issubclass(value, messages.Enum):
        enum_descriptors.append(describe_enum(value))

      elif issubclass(value, remote.Service):
        service_descriptors.append(describe_service(value))

  if message_descriptors:
    descriptor.messages = message_descriptors

  if enum_descriptors:
    descriptor.enums = enum_descriptors

  if service_descriptors:
    descriptor.services = service_descriptors

  return descriptor


def describe_file_set(modules):
  """Build a file set from a specified Python modules.

  Args:
    modules: Iterable of Python module to describe.

  Returns:
    Initialized FileSet instance describing the modules.
  """
  descriptor = FileSet()
  file_descriptors = []
  for module in modules:
    file_descriptors.append(describe_file(module))

  if file_descriptors:
    descriptor.files = file_descriptors

  return descriptor
