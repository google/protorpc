// Copyright 2010 Google Inc.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//

/**
 * @fileoverview Render form appropriate for RPC method.
 * @author rafek@google.com (Rafe Kaplan)
 */

/**
 * Find file descriptor of a service definition.
 * @param fileSet {object} JSON file-set object containing all definitions.
 * @param name {string} Fully qualified name of service to find file for.
 * @return {object} JSON file object containing service definition.
 */
function findFileDescriptor(fileSet, name) {
  for (var index = 0; index < fileSet.files.length; index++) {
    var fileDescriptor = fileSet.files[index];
    var packageName = fileDescriptor.package;
    if (name.indexOf(packageName) == 0) {
      return fileDescriptor;
    }
  }
}

/**
 * Find message definition.
 * @param fileSet {object} JSON file-set object containing all definitions.
 * @param name {string} Fully qualified name of message to find.
 * @return {object} JSON message definition.
 */
function findMessage(fileSet, name) {
  // TODO(rafek): Support nested messages.
  var fileDescriptor = findFileDescriptor(fileSet, name);
  var name = name.substr(fileDescriptor.package.length + 1);

  if (fileDescriptor.message_types) {
    for (var index = 0; index < fileDescriptor.message_types.length; index++) {
      var message = fileDescriptor.message_types[index];
      if (message.name == name) {
        return message;
      }
    }
  }
}

/**
 * Find service definition.
 * @param fileSet {object} JSON file-set object containing all definitions.
 * @param name {string} Fully qualified name of service to find.
 * @return {object} JSON service definition.
 */
function findService(fileSet, name) {
  var fileDescriptor = findFileDescriptor(fileSet, name);
  var name = name.substr(fileDescriptor.package.length + 1);

  if (fileDescriptor.service_types) {
    for (var index = 0; index < fileDescriptor.service_types.length; index++) {
      var service = fileDescriptor.service_types[index];
      if (service.name == name) {
        return service;
      }
    }
  }
}

/**
 * Find method definition.
 * @param service {object} JSON service definition containing method.
 * @param name {string} Name of method to get.
 * @return {object} JSON method definition.
 */
function getMethod(service, name) {
  if (service.methods) {
    for (var index = 0; index < service.methods.length; index++) {
      if (service.methods[index].name == name) {
        return service.methods[index];
      }
    }
  }
}

/**
 * Create closure for toggling an input field enabled and disabled.
 * @param enableToggle {Element} Checkbox with enable/disable state.
 * @param input {Element} Input element to enable or disable.
 */
function toggleInput(enableToggle, input) {
  return function() {
    if (enableToggle.val() == 'on') {
      input.removeAttr('disabled');
    } else {
      input.attr('disabled', 'disabled');
    }
  }
}

/**
 * Create a text field in the row of a table.
 * @param row {Element} Table row to insert text field in to.
 * @param field {object} JSON field definition of text field.
 * @param fieldName {string} Form field name of text field.
 */
function textField(row, field, fieldName) {
  $('<td>' + field.name + ':</td>').appendTo(row);

  var input = $('<input type="text">');

  input.attr('name', fieldName).attr('value', field['default']);

  var enablerData = $('<td>').appendTo(row);
  if (field.label != 'REQUIRED') {
    input.attr('disabled', 'disabled');
    var enableToggle = $('<input type="checkbox">').appendTo(enablerData);
    enableToggle.bind('change', toggleInput(enableToggle, input));
  }

  var data = $('<td>');
  data.appendTo(row);
  input.appendTo(data);
}

/**
 * Populate an element with fields for an RPC form.
 * @param element {Element} Element to add form fields to.
 * @param fileSet {object} JSON file-set object containing all definitions.
 * @param requestType {object} JSON message definition of request type.
 */
function populateForm(element, fileSet, requestType) {
  var table = $('<table>').appendTo(element)
  for (var index = 0; index < requestType.fields.length; index++) {
    var row = $('<tr>').appendTo(table);
    var field = requestType.fields[index];
    if (field.label == 'REPEATED') {
      alert('Repeated field ' + field.name + ' not supported.');
    } else {
      switch(field.variant) {
        case 'STRING':
          textField(row, field, field.name, 'string');
          break;

        case 'BYTES':
          textField(row, field, field.name, 'bytes');
          break;

        case 'INT64':
        case 'UINT64':
        case 'INT32':
        case 'UINT32':
        case 'SINT32':
        case 'SINT64':
          textField(row, field, field.name, 'int');
          break;

        default:
          alert('Unupported variant: ' + field.variant);
      }
    }
  }
}

VOID_MESSAGE_TYPE = 'protorpc.message_types.VoidMessage';
$(function() {
    $.getJSON(servicePath + '/form/file_set',
              function(fileSet, textStatus) {
                if (textStatus != 'success') {
                  $('#error-message').html(textStatus);
                } else {
                  var service = findService(fileSet, serviceName);
                  var method = getMethod(service, methodName);

                  // Special case the void message type.
                  if (method.request_type != VOID_MESSAGE_TYPE) {
                    var requestType = findMessage(fileSet, method.request_type);

                    populateForm($('#method-form'), fileSet, requestType);
                  }
                }
              });
  });
