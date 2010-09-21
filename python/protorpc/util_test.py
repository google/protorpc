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

"""Tests for protorpc.util."""

__author__ = 'rafek@google.com (Rafe Kaplan)'

import unittest

from protorpc import test_util
from protorpc import util


class ModuleInterfaceTest(test_util.ModuleInterfaceTest,
                          test_util.TestCase):

  MODULE = util


class UtilTest(test_util.TestCase):

  def testDecoratedFunction_LengthZero(self):
    @util.positional(0)
    def fn(kwonly=1):
      return [kwonly]
    self.assertEquals([1], fn())
    self.assertEquals([2], fn(kwonly=2))
    self.assertRaisesWithRegexpMatch(TypeError,
                                     r'fn\(\) takes at most 0 positional '
                                     r'arguments \(1 given\)',
                                     fn, 1)

  def testDecoratedFunction_LengthOne(self):
    @util.positional(1)
    def fn(pos, kwonly=1):
      return [pos, kwonly]
    self.assertEquals([1, 1], fn(1))
    self.assertEquals([2, 2], fn(2, kwonly=2))
    self.assertRaisesWithRegexpMatch(TypeError,
                                     r'fn\(\) takes at most 1 positional '
                                     r'argument \(2 given\)',
                                     fn, 2, 3)

  def testDecoratedFunction_LengthTwoWithDefault(self):
    @util.positional(2)
    def fn(pos1, pos2=1, kwonly=1):
      return [pos1, pos2, kwonly]
    self.assertEquals([1, 1, 1], fn(1))
    self.assertEquals([2, 2, 1], fn(2, 2))
    self.assertEquals([2, 3, 4], fn(2, 3, kwonly=4))
    self.assertRaisesWithRegexpMatch(TypeError,
                                     r'fn\(\) takes at most 2 positional '
                                     r'arguments \(3 given\)',
                                     fn, 2, 3, 4)

  def testDecoratedMethod(self):
    class MyClass(object):
      @util.positional(2)
      def meth(self, pos1, kwonly=1):
        return [pos1, kwonly]
    self.assertEquals([1, 1], MyClass().meth(1))
    self.assertEquals([2, 2], MyClass().meth(2, kwonly=2))
    self.assertRaisesWithRegexpMatch(TypeError,
                                     r'meth\(\) takes at most 2 positional '
                                     r'arguments \(3 given\)',
                                     MyClass().meth, 2, 3)

  def testDefaultDecoration(self):
    @util.positional
    def fn(a, b, c=None):
      return a, b, c
    self.assertEquals((1, 2, 3), fn(1, 2, c=3))
    self.assertEquals((3, 4, None), fn(3, b=4))
    self.assertRaisesWithRegexpMatch(TypeError,
                                     r'fn\(\) takes at most 2 positional '
                                     r'arguments \(3 given\)',
                                     fn, 2, 3, 4)


def main():
  unittest.main()


if __name__ == '__main__':
  main()
