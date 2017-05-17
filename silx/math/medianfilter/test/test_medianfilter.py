# coding: utf-8
# ##########################################################################
# Copyright (C) 2017 European Synchrotron Radiation Facility
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
# ############################################################################
"""Tests of the median filter"""

__authors__ = ["H. Payno"]
__license__ = "MIT"
__date__ = "02/05/2017"

import unittest
import numpy
import os
from silx.math.medianfilter import medfilt2d
from silx.math.medianfilter.medianfilter import reflect, mirror
from silx.test.utils import ParametricTestCase
try:
    import scipy
    import scipy.misc
except:
    scipy = None
else:
    import scipy.ndimage

import logging
_logger = logging.getLogger(__name__)

RANDOM_FLOAT_MAT = numpy.array([
    [0.05564293, 0.62717157, 0.75002406, 0.40555336, 0.70278975],
    [0.76532598, 0.02839148, 0.05272484, 0.65166994, 0.42161216],
    [0.23067427, 0.74219128, 0.56049024, 0.44406320, 0.28773158],
    [0.81025249, 0.20303021, 0.68382382, 0.46372299, 0.81281709],
    [0.94691602, 0.07813661, 0.81651256, 0.84220106, 0.33623165]])

RANDOM_INT_MAT = numpy.array([
    [0, 5, 2, 6, 1],
    [2, 3, 1, 7, 1],
    [9, 8, 6, 7, 8],
    [5, 6, 8, 2, 4]])


class TestMedianFilterNearest(ParametricTestCase):
    """Unit tests for the median filter in nearest mode"""

    def testFilter3_100(self):
        """Test median filter on a 10x10 matrix with a 3x3 kernel."""
        dataIn = numpy.arange(100, dtype=numpy.int32)
        dataIn = dataIn.reshape((10, 10))

        dataOut = medfilt2d(image=dataIn,
                            kernel_size=(3, 3),
                            conditional=False,
                            mode='nearest')
        self.assertTrue(dataOut[0, 0] == 1)
        self.assertTrue(dataOut[9, 0] == 90)
        self.assertTrue(dataOut[9, 9] == 98)

        self.assertTrue(dataOut[0, 9] == 9)
        self.assertTrue(dataOut[0, 4] == 5)
        self.assertTrue(dataOut[9, 4] == 93)
        self.assertTrue(dataOut[4, 4] == 44)

    def testFilter3_9(self):
        "Test median filter on a 3x3 matrix a 3x3 kernel."
        dataIn = numpy.array([0, -1, 1,
                              12, 6, -2,
                              100, 4, 12],
                             dtype=numpy.int16)
        dataIn = dataIn.reshape((3, 3))
        dataOut = medfilt2d(image=dataIn,
                            kernel_size=(3, 3),
                            conditional=False,
                            mode='nearest')
        self.assertTrue(dataOut.shape == dataIn.shape)
        self.assertTrue(dataOut[1, 1] == 4)
        self.assertTrue(dataOut[0, 0] == 0)
        self.assertTrue(dataOut[0, 1] == 0)
        self.assertTrue(dataOut[1, 0] == 6)

    def testFilterWidthOne(self):
        """Make sure a filter of one by one give the same result as the input
        """
        dataIn = numpy.arange(100, dtype=numpy.int32)
        dataIn = dataIn.reshape((10, 10))

        dataOut = medfilt2d(image=dataIn,
                            kernel_size=(1, 1),
                            conditional=False,
                            mode='nearest')

        self.assertTrue(numpy.array_equal(dataIn, dataOut))

    def testInputDataIsNotModify(self):
        """Make sure input data is not modify by the median filter"""
        dataIn = numpy.arange(100, dtype=numpy.int32)
        dataIn = dataIn.reshape((10, 10))
        dataInCopy = dataIn.copy()

        medfilt2d(image=dataIn,
                  kernel_size=(3, 3),
                  conditional=False,
                  mode='nearest')
        self.assertTrue(numpy.array_equal(dataIn, dataInCopy))

    def testFilter3Conditionnal(self):
        """Test that the conditional filter apply correctly"""
        dataIn = numpy.arange(100, dtype=numpy.int32)
        dataIn = dataIn.reshape((10, 10))

        dataOut = medfilt2d(image=dataIn,
                            kernel_size=(3, 3),
                            conditional=True,
                            mode='nearest')
        self.assertTrue(dataOut[0, 0] == 1)
        self.assertTrue(dataOut[0, 1] == 1)
        self.assertTrue(numpy.array_equal(dataOut[1:8, 1:8], dataIn[1:8, 1:8]))
        self.assertTrue(dataOut[9, 9] == 98)

    def testTypes(self):
        """Test that all needed types have their implementation of the median
        filter
        """
        for testType in [numpy.float32, numpy.float64, numpy.int16,
                         numpy.uint16, numpy.int32, numpy.int64, numpy.uint64]:
            data = (numpy.random.rand(10, 10) * 65000).astype(testType)
            out = medfilt2d(image=data,
                            kernel_size=(3, 3),
                            conditional=False,
                            mode='nearest')
            self.assertTrue(out.dtype.type is testType)

    def testFilter3_1D(self):
        """Simple test of a three by three kernel median filter"""
        dataIn = numpy.arange(100, dtype=numpy.int32)

        dataOut = medfilt2d(image=dataIn,
                            kernel_size=(5),
                            conditional=False,
                            mode='nearest')

        self.assertTrue(dataOut[0] == 0)
        self.assertTrue(dataOut[9] == 9)
        self.assertTrue(dataOut[99] == 99)

    @unittest.skipUnless(scipy, "scipy not available")
    def testWithArange(self):
        data = numpy.arange(10000, dtype=numpy.int32)
        data = data.reshape(100, 100)

        kernels = [(3, 7), (7, 5), (1, 1), (3, 3)]
        for kernel in kernels:
            with self.subTest(kernel=kernel):
                resScipy = scipy.ndimage.median_filter(input=data,
                                                       size=kernel,
                                                       mode='nearest')
                resSilx = medfilt2d(image=data,
                                    kernel_size=kernel,
                                    conditional=False,
                                    mode='nearest')

                self.assertTrue(numpy.array_equal(resScipy, resSilx))

    @unittest.skipUnless(scipy, "scipy not available")
    def testRandomMatrice(self):
        kernels = [(3, 7), (7, 5), (1, 1), (3, 3)]
        for kernel in kernels:
            with self.subTest(kernel=kernel):
                resScipy = scipy.ndimage.median_filter(input=RANDOM_FLOAT_MAT,
                                                       size=kernel,
                                                       mode='nearest')

                resSilx = medfilt2d(image=RANDOM_FLOAT_MAT,
                                    kernel_size=kernel,
                                    conditional=False,
                                    mode='nearest')

                self.assertTrue(numpy.array_equal(resScipy, resSilx))

    @unittest.skipUnless(scipy, "scipy not available")
    def testAscentOrLena(self):
        if hasattr(scipy.misc, 'ascent'):
            img = scipy.misc.ascent()
        else:
            img = scipy.misc.lena()

        kernels = [(3, 1), (3, 5), (5, 9), (9, 3)]
        for kernel in kernels:
            with self.subTest(kernel=kernel):
                resScipy = scipy.ndimage.median_filter(input=img,
                                                       size=kernel,
                                                       mode='nearest')

                resSilx = medfilt2d(image=img,
                                    kernel_size=kernel,
                                    conditional=False,
                                    mode='nearest')

                self.assertTrue(numpy.array_equal(resScipy, resSilx))


class TestMedianFilterReflect(ParametricTestCase):
    """Unit test for the median filter in reflect mode"""

    @unittest.skipUnless(scipy, "scipy not available")
    def testAscentOrLena(self):
        """Simple test vs scipy"""
        if hasattr(scipy.misc, 'ascent'):
            img = scipy.misc.ascent()
        else:
            img = scipy.misc.lena()

        kernels = [(3, 1), (3, 5), (5, 9), (9, 3)]
        for kernel in kernels:
            with self.subTest(kernel=kernel):
                resScipy = scipy.ndimage.median_filter(input=img,
                                                       size=kernel,
                                                       mode='reflect')

                resSilx = medfilt2d(image=img,
                                    kernel_size=kernel,
                                    conditional=False,
                                    mode='reflect')

                self.assertTrue(numpy.array_equal(resScipy, resSilx))

    def testArange9(self):
        """Test from a 3x3 window to an arange array"""
        img = numpy.arange(9, dtype=numpy.int32)
        img = img.reshape(3, 3)
        kernel = (3, 3)
        res = medfilt2d(image=img,
                        kernel_size=kernel,
                        conditional=False,
                        mode='reflect')
        self.assertTrue(
            numpy.array_equal(res.ravel(), [1, 2, 2, 3, 4, 5, 6, 6, 7]))

    def testRandom10(self):
        """Test a (5, 3) window to a random array"""
        kernel = (5, 3)

        thRes = numpy.array([
            [0.23067427, 0.56049024, 0.56049024, 0.4440632, 0.42161216],
            [0.23067427, 0.62717157, 0.56049024, 0.56049024, 0.46372299],
            [0.62717157, 0.62717157, 0.56049024, 0.56049024, 0.4440632],
            [0.76532598, 0.68382382, 0.56049024, 0.56049024, 0.42161216],
            [0.81025249, 0.68382382, 0.56049024, 0.68382382, 0.46372299]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=False,
                        mode='reflect')

        self.assertTrue(numpy.array_equal(thRes, res))

    def testApplyReflect1D(self):
        """Test the reflect function used for the median filter in reflect mode
        """
        # test for inside values
        self.assertTrue(reflect(2, 3) == 2)
        # test for boundaries values
        self.assertTrue(reflect(3, 3) == 2)
        self.assertTrue(reflect(4, 3) == 1)
        self.assertTrue(reflect(5, 3) == 0)
        self.assertTrue(reflect(6, 3) == 0)
        self.assertTrue(reflect(7, 3) == 1)
        self.assertTrue(reflect(-1, 3) == 0)
        self.assertTrue(reflect(-2, 3) == 1)
        self.assertTrue(reflect(-3, 3) == 2)
        self.assertTrue(reflect(-4, 3) == 2)
        self.assertTrue(reflect(-5, 3) == 1)
        self.assertTrue(reflect(-6, 3) == 0)
        self.assertTrue(reflect(-7, 3) == 0)

    def testRandom10Conditionnal(self):
        """Test the median filter in reflect mode and with the conditionnal
        option"""
        kernel = (3, 1)

        thRes = numpy.array([
            [0.05564293, 0.62717157, 0.75002406, 0.40555336, 0.70278975],
            [0.23067427, 0.62717157, 0.56049024, 0.44406320, 0.42161216],
            [0.76532598, 0.20303021, 0.56049024, 0.46372299, 0.42161216],
            [0.81025249, 0.20303021, 0.68382382, 0.46372299, 0.33623165],
            [0.94691602, 0.07813661, 0.81651256, 0.84220106, 0.33623165]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=True,
                        mode='reflect')
        self.assertTrue(numpy.array_equal(thRes, res))


class TestMedianFilterMirror(ParametricTestCase):
    """Unit test for the median filter in mirror mode
    """

    def testApplyMirror1D(self):
        """Test the reflect function used for the median filter in mirror mode
        """
        # test for inside values
        self.assertTrue(mirror(2, 3) == 2)
        # test for boundaries values
        self.assertTrue(mirror(4, 4) == 2)
        self.assertTrue(mirror(5, 4) == 1)
        self.assertTrue(mirror(6, 4) == 0)
        self.assertTrue(mirror(7, 4) == 1)
        self.assertTrue(mirror(8, 4) == 2)
        self.assertTrue(mirror(-1, 4) == 1)
        self.assertTrue(mirror(-2, 4) == 2)
        self.assertTrue(mirror(-3, 4) == 3)
        self.assertTrue(mirror(-4, 4) == 2)
        self.assertTrue(mirror(-5, 4) == 1)
        self.assertTrue(mirror(-6, 4) == 0)

    def testRandom10(self):
        """Test a (5, 3) window to a random array"""
        kernel = (3, 5)

        thRes = numpy.array([
            [0.05272484, 0.40555336, 0.42161216, 0.42161216, 0.42161216],
            [0.56049024, 0.56049024, 0.4440632, 0.4440632, 0.4440632],
            [0.56049024, 0.46372299, 0.46372299, 0.46372299, 0.46372299],
            [0.68382382, 0.56049024, 0.56049024, 0.46372299, 0.56049024],
            [0.68382382, 0.46372299, 0.68382382, 0.46372299, 0.68382382]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=False,
                        mode='mirror')

        self.assertTrue(numpy.array_equal(thRes, res))

    @unittest.skipUnless(scipy, "scipy not available")
    def testAscentOrLena(self):
        """Simple test vs scipy"""
        if hasattr(scipy.misc, 'ascent'):
            img = scipy.misc.ascent()
        else:
            img = scipy.misc.lena()

        kernels = [(3, 1), (3, 5), (5, 9), (9, 3)]
        for kernel in kernels:
            with self.subTest(kernel=kernel):
                resScipy = scipy.ndimage.median_filter(input=img,
                                                       size=kernel,
                                                       mode='mirror')

                resSilx = medfilt2d(image=img,
                                    kernel_size=kernel,
                                    conditional=False,
                                    mode='mirror')

                self.assertTrue(numpy.array_equal(resScipy, resSilx))

    def testRandom10Conditionnal(self):
        """Test the median filter in reflect mode and with the conditionnal
        option"""
        kernel = (1, 3)

        thRes = numpy.array([
            [0.62717157, 0.62717157, 0.62717157, 0.70278975, 0.40555336],
            [0.02839148, 0.05272484, 0.05272484, 0.42161216, 0.65166994],
            [0.74219128, 0.56049024, 0.56049024, 0.44406320, 0.44406320],
            [0.20303021, 0.68382382, 0.46372299, 0.68382382, 0.46372299],
            [0.07813661, 0.81651256, 0.81651256, 0.81651256, 0.84220106]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=True,
                        mode='mirror')

        self.assertTrue(numpy.array_equal(thRes, res))


class TestMedianFilterShrink(ParametricTestCase):
    """Unit test for the median filter in mirror mode
    """

    def testRandom_3x3(self):
        """Test the median filter in shrink mode and with the conditionnal
        option"""
        kernel = (3, 3)

        thRes = numpy.array([
            [0.62717157, 0.62717157, 0.62717157, 0.65166994, 0.65166994],
            [0.62717157, 0.56049024, 0.56049024, 0.44406320, 0.44406320],
            [0.74219128, 0.56049024, 0.46372299, 0.46372299, 0.46372299],
            [0.74219128, 0.68382382, 0.56049024, 0.56049024, 0.46372299],
            [0.81025249, 0.81025249, 0.68382382, 0.81281709, 0.81281709]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=False,
                        mode='shrink')

        self.assertTrue(numpy.array_equal(thRes, res))

    def testBounds(self):
        """Test the median filter in shrink mode with 3 different kernels
        which should return the same result due to the large values of kernels
        used.
        """
        kernel1 = (1, 9)
        kernel2 = (1, 11)
        kernel3 = (1, 21)

        thRes = numpy.array([[2, 2, 2, 2, 2],
                             [2, 2, 2, 2, 2],
                             [8, 8, 8, 8, 8],
                             [5, 5, 5, 5, 5]])

        resK1 = medfilt2d(image=RANDOM_INT_MAT,
                          kernel_size=kernel1,
                          conditional=False,
                          mode='shrink')

        resK2 = medfilt2d(image=RANDOM_INT_MAT,
                          kernel_size=kernel2,
                          conditional=False,
                          mode='shrink')

        resK3 = medfilt2d(image=RANDOM_INT_MAT,
                          kernel_size=kernel3,
                          conditional=False,
                          mode='shrink')

        self.assertTrue(numpy.array_equal(resK1, thRes))
        self.assertTrue(numpy.array_equal(resK2, resK1))
        self.assertTrue(numpy.array_equal(resK3, resK1))

    def testRandom_3x3Conditionnal(self):
        """Test the median filter in reflect mode and with the conditionnal
        option"""
        kernel = (3, 3)

        thRes = numpy.array([
            [0.05564293, 0.62717157, 0.62717157, 0.40555336, 0.65166994],
            [0.62717157, 0.56049024, 0.05272484, 0.65166994, 0.42161216],
            [0.23067427, 0.74219128, 0.56049024, 0.44406320, 0.46372299],
            [0.81025249, 0.20303021, 0.68382382, 0.46372299, 0.81281709],
            [0.81025249, 0.81025249, 0.81651256, 0.81281709, 0.81281709]])

        res = medfilt2d(image=RANDOM_FLOAT_MAT,
                        kernel_size=kernel,
                        conditional=True,
                        mode='shrink')

        self.assertTrue(numpy.array_equal(res, thRes))

    def testRandomInt(self):
        """Test 3x3 kernel on RANDOM_INT_MAT
        """
        kernel = (3, 3)

        thRes = numpy.array([[3, 2, 5, 2, 6],
                             [5, 3, 6, 6, 7],
                             [6, 6, 6, 6, 7],
                             [8, 8, 7, 7, 7]])

        resK1 = medfilt2d(image=RANDOM_INT_MAT,
                          kernel_size=kernel,
                          conditional=False,
                          mode='shrink')

        self.assertTrue(numpy.array_equal(resK1, thRes))


def suite():
    test_suite = unittest.TestSuite()
    for test in [TestMedianFilterNearest, TestMedianFilterReflect,
                 TestMedianFilterMirror, TestMedianFilterShrink]:
        test_suite.addTest(
            unittest.defaultTestLoader.loadTestsFromTestCase(test))
    return test_suite


if __name__ == '__main__':
    unittest.main(defaultTest='suite')
