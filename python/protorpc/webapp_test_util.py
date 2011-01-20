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

"""Testing utilities for the webapp libraries.

  GetDefaultEnvironment: Method for easily setting up CGI environment.
  RequestHandlerTestBase: Base class for setting up handler tests.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import cStringIO
import unittest

from google.appengine.ext import webapp


def GetDefaultEnvironment():
  """Function for creating a default CGI environment."""
  return {
    'LC_NUMERIC': 'C',
    'wsgi.multiprocess': True,
    'SERVER_PROTOCOL': 'HTTP/1.0',
    'SERVER_SOFTWARE': 'Dev AppServer 0.1',
    'SCRIPT_NAME': '',
    'LOGNAME': 'nickjohnson',
    'USER': 'nickjohnson',
    'QUERY_STRING': 'foo=bar&foo=baz&foo2=123',
    'PATH': '/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/bin/X11',
    'LANG': 'en_US',
    'LANGUAGE': 'en',
    'REMOTE_ADDR': '127.0.0.1',
    'LC_MONETARY': 'C',
    'CONTENT_TYPE': 'application/x-www-form-urlencoded',
    'wsgi.url_scheme': 'http',
    'SERVER_PORT': '8080',
    'HOME': '/home/mruser',
    'USERNAME': 'mruser',
    'CONTENT_LENGTH': '',
    'USER_IS_ADMIN': '1',
    'PYTHONPATH': '/tmp/setup',
    'LC_TIME': 'C',
    'HTTP_USER_AGENT': 'Mozilla/5.0 (X11; U; Linux i686 (x86_64); en-US; '
        'rv:1.8.1.6) Gecko/20070725 Firefox/2.0.0.6',
    'wsgi.multithread': False,
    'wsgi.version': (1, 0),
    'USER_EMAIL': 'test@example.com',
    'USER_EMAIL': '112',
    'wsgi.input': cStringIO.StringIO(),
    'PATH_TRANSLATED': '/tmp/request.py',
    'SERVER_NAME': 'localhost',
    'GATEWAY_INTERFACE': 'CGI/1.1',
    'wsgi.run_once': True,
    'LC_COLLATE': 'C',
    'HOSTNAME': 'myhost',
    'wsgi.errors': cStringIO.StringIO(),
    'PWD': '/tmp',
    'REQUEST_METHOD': 'GET',
    'MAIL': '/dev/null',
    'MAILCHECK': '0',
    'USER_NICKNAME': 'test',
    'HTTP_COOKIE': 'dev_appserver_login="test:test@example.com:True"',
    'PATH_INFO': '/tmp/myhandler'
  }


class RequestHandlerTestBase(unittest.TestCase):
  """Base class for writing RequestHandler tests.

  To test a specific request handler override CreateRequestHandler.
  To change the environment for that handler override GetEnvironment.
  """

  def setUp(self):
    """Set up test for request handler."""
    self.ResetHandler()

  def GetEnvironment(self):
    """Get environment.

    Override for more specific configurations.

    Returns:
      dict of CGI environment.
    """
    return GetDefaultEnvironment()

  def CreateRequestHandler(self):
    """Create RequestHandler instances.

    Override to create more specific kinds of RequestHandler instances.

    Returns:
      RequestHandler instance used in test.
    """
    return webapp.RequestHandler()

  def CheckResponse(self,
                    expected_status,
                    expected_headers,
                    expected_content):
    """Check that the web response is as expected.

    Args:
      expected_status: Expected status message.
      expected_headers: Dictionary of expected headers.  Will ignore unexpected
        headers and only check the value of those expected.
      expected_content: Expected body.
    """
    def check_content(content):
      self.assertEquals(expected_content, content)

    def start_response(status, headers):
      self.assertEquals(expected_status, status)

      found_keys = set()
      for name, value in headers:
        name = name.lower()
        try:
          expected_value = expected_headers[name]
        except KeyError:
          pass
        else:
          found_keys.add(name)
          self.assertEquals(expected_value, value)

      missing_headers = set(expected_headers.iterkeys()) - found_keys
      if missing_headers:
        self.fail('Expected keys %r not found' % (list(missing_headers),))

      return check_content

    self.handler.response.wsgi_write(start_response)

  def ResetHandler(self, change_environ=None):
    """Reset this tests environment with environment changes.

    Resets the entire test with a new handler which includes some changes to
    the default request environment.

    Args:
      change_environ: Dictionary of values that are added to default
        environment.
    """
    environment = self.GetEnvironment()
    environment.update(change_environ or {})
    
    self.request = webapp.Request(environment)
    self.response = webapp.Response()
    self.handler = self.CreateRequestHandler()
    self.handler.initialize(self.request, self.response)
