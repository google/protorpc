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

"""WSGI utility library tests."""

__author__ = 'rafe@google.com (Rafe Kaplan)'

import httplib
import unittest
from wsgiref import simple_server
from wsgiref import validate

from protorpc import test_util
from protorpc import webapp_test_util
from protorpc.wsgi import util as wsgi_util


class WsgiTestBase(test_util.TestCase):

  def StartServer(self, app):
    self.validated = validate.validator(app)
    self.port = test_util.pick_unused_port()
    self.server = simple_server.make_server('localhost',
                                            self.port,
                                            self.validated)
    self.server_thread = webapp_test_util.ServerThread(self.server)
    self.server_thread.start()
    self.server_thread.wait_until_running()

  def DoHttpRequest(self,
                    path='/',
                    content=None,
                    content_type='text/plain; charset=utf-8',
                    headers=None):
    connection = httplib.HTTPConnection('localhost', self.port)
    if content is None:
      method = 'GET'
    else:
      method = 'POST'
    headers = {'content=type': content_type}
    headers.update(headers)
    connection.request(method, path, content, headers)
    response = connection.getresponse()

    not_date_or_server = lambda header: header[0] not in ('date', 'server')
    headers = filter(not_date_or_server, response.getheaders())

    return response.status, response.reason, response.read(), dict(headers)


class StaticPageBase(WsgiTestBase):

  def testDefault(self):
    default_page = wsgi_util.static_page()
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(200, status)
    self.assertEquals('OK', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasContent(self):
    default_page = wsgi_util.static_page('my content')
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(200, status)
    self.assertEquals('OK', reason)
    self.assertEquals('my content', content)
    self.assertEquals({'content-length': str(len('my content')),
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasContentType(self):
    default_page = wsgi_util.static_page(content_type='text/plain')
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(200, status)
    self.assertEquals('OK', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/plain',
                      },
                      headers)

  def testHasStatus(self):
    default_page = wsgi_util.static_page(status='400 Not Good Request')
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(400, status)
    self.assertEquals('Not Good Request', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasStatusInt(self):
    default_page = wsgi_util.static_page(status=401)
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(401, status)
    self.assertEquals('Unauthorized', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasStatusUnknown(self):
    default_page = wsgi_util.static_page(status=909)
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(909, status)
    self.assertEquals('Unknown Error', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasStatusTuple(self):
    default_page = wsgi_util.static_page(status=(500, 'Bad Thing'))
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(500, status)
    self.assertEquals('Bad Thing', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                      },
                      headers)

  def testHasHeaders(self):
    default_page = wsgi_util.static_page(headers=[('x', 'foo'),
                                                  ('a', 'bar'),
                                                  ('z', 'bin')])
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(200, status)
    self.assertEquals('OK', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                       'x': 'foo',
                       'a': 'bar',
                       'z': 'bin',
                      },
                      headers)

  def testHasHeadersDict(self):
    default_page = wsgi_util.static_page(headers={'x': 'foo',
                                                  'a': 'bar',
                                                  'z': 'bin'})
    self.StartServer(default_page)
    status, reason, content, headers = self.DoHttpRequest()
    self.assertEquals(200, status)
    self.assertEquals('OK', reason)
    self.assertEquals('', content)
    self.assertEquals({'content-length': '0',
                       'content-type': 'text/html; charset=utf-8',
                       'x': 'foo',
                       'a': 'bar',
                       'z': 'bin',
                      },
                      headers)
  


if __name__ == '__main__':
  unittest.main()

