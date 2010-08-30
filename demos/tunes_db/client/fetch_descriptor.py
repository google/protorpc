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

"""Boot-strap development by fetching package set from service.

This script fetches a protobuf encoded FileSet from get_file_set
method of a service.
"""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import optparse
import os
import sys
import urllib2


def parse_options(argv):
  """Parse options.

  Args:
    argv: List of original unparsed options.

  Results:
    Tuple (service_url, options):
      service_url: Service URL read from parameter list.
      options: Options object as parsed by optparse.
  """
  program = os.path.split(__file__)[-1]
  parser = optparse.OptionParser(usage='%s [options] <service-url>' % program)

  parser.add_option('-o', '--output',
                    dest='output',
                    help='Write descriptor to FILE.',
                    metavar='FILE',
                    default='music_service.descriptor')

  options, args = parser.parse_args(argv)

  if len(args) != 2:
    parser.print_help()
    sys.exit(1)

  return args[1], options


def main(argv):
  service_url, options = parse_options(argv)

  get_file_set_url = '%s.get_file_set' % service_url

  request = urllib2.Request(
      get_file_set_url,
      data='',
      headers={'content-type': 'application/x-google-protobuf'})
  connection = urllib2.urlopen(request)

  output = open(options.output, 'wb')
  try:
    output.write(connection.read())
  finally:
    output.close()


if __name__ == '__main__':
  main(sys.argv)
