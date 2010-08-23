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

"""Web services demo.

Implements a simple music database.  The music database is served
off the /music URL.  It supports all built in protocols (url-encoded
and protocol buffers) using the default RPC mapping scheme.

For details about the Tunes service itself, please see tunes_db.py.

For details about the datastore representation of the Tunes db, please
see model.py.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'


import logging
import os
import wsgiref.handlers

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp import util

from protorpc import service_handlers

import forms
import model
import tunes_db


class MainHandler(webapp.RequestHandler):

  def get(self):
    self.redirect('/forms')


service_registry = forms.ServiceRegistry()
service_registry.register_service('/music', tunes_db.MusicLibraryService)

# Register mapping with application.
application = webapp.WSGIApplication(
    [('/', MainHandler)] + service_registry.mappings(),
    debug=True)


def main():
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
