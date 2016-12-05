# coding: utf-8
# /*##########################################################################
#
# Copyright (c) 2015-2016 European Synchrotron Radiation Facility
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ###########################################################################*/
"""Full silx test suite.

silx.gui tests depends on Qt.
To disable them, set WITH_QT_TEST environement variable to 'False'.
"""

__authors__ = ["T. Vincent"]
__license__ = "MIT"
__date__ = "05/12/2016"


import logging
import os
import unittest


logger = logging.getLogger(__name__)


def suite():
    from . import test_version
    from . import test_resources
    from . import test_sx
    from ..io import test as test_io
    from ..math import test as test_math
    from ..image import test as test_image
    from ..gui import test as test_gui
    from ..utils import test as test_utils

    test_suite = unittest.TestSuite()
    test_suite.addTest(test_version.suite())
    test_suite.addTest(test_resources.suite())
    test_suite.addTest(test_gui.suite())
    test_suite.addTest(test_utils.suite())
    test_suite.addTest(test_io.suite())
    test_suite.addTest(test_math.suite())
    test_suite.addTest(test_image.suite())
    test_suite.addTest(test_sx.suite())
    return test_suite


def run_tests():
    """Run test complete test_suite"""
    runner = unittest.TextTestRunner()
    if not runner.run(suite()).wasSuccessful():
        print("Test suite failed")
        return 1
    else:
        print("Test suite succeeded")
        return 0
