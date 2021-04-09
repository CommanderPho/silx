# coding: utf-8
# /*##########################################################################
#
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
# ############################################################################*/
"""This module provides a h5py-like API to access FioFile data.

API description
+++++++++++++++

Fiofile data structure exposed by this API:

::

  /
      n.1/
          title = "…"
          start_time = "…"
          instrument/
              fiofile/
                  comments = "…"
                  parameter = "…"
              comment = "…"
              parameter/
                  parameter_name = value

          measurement/
              colname0 = …
              colname1 = …
              …


The top level scan number ``n.1`` is determined from the filename as in
``prefix_n.fio``. (e.g. ``eh1_sixc_00045.fio`` would give ``45.1``)
If no number is available, will use the filename instead.

``comments`` and ``parameter`` in group ``fiofile`` are the raw headers as they
appear in the original file, as a string of lines separated by newline
(``\\n``) characters. ``comment`` are the remaining comments,
which were not parsed.



The title is the content of the first comment header line
(e.g ``"ascan  ss1vo -4.55687 -0.556875  40 0.2"``).
The start_time is parsed from the second comment line.

Datasets are stored in the data format specified in the fio file header.

Scan data  (e.g. ``/1.1/measurement/colname0``) is accessed by column,
the dataset name ``colname0`` being the column label as defined in the
``Col …`` header line.

If a ``/`` character is present in a column label or in a motor name in the
original FIO file, it will be substituted with a ``%`` character in the
corresponding dataset name.

MCA data is not yet supported.

This reader requires a fio file as defined in
src/sardana/macroserver/recorders/storage.py of the Sardana project
(https://github.com/sardana-org/sardana).


Accessing data
++++++++++++++

Data and groups are accessed in :mod:`h5py` fashion::

    from silx.io.fioh5 import FioH5

    # Open a FioFile
    sfh5 = FioH5("test_00056.fio")

    # using FioH5 as a regular group to access scans
    scan1group = sfh5["56.1"]
    instrument_group = scan1group["instrument"]

    # alternative: full path access
    measurement_group = sfh5["/56.1/measurement"]

    # accessing a scan data column by name as a 1D numpy array
    data_array = measurement_group["Pslit HGap"]


:class:`FioH5` files and groups provide a :meth:`keys` method::

    >>> sfh5.keys()
    ['96.1', '97.1', '98.1']
    >>> sfh5['96.1'].keys()
    ['title', 'start_time', 'instrument', 'measurement']

They can also be treated as iterators:

.. code-block:: python

    from silx.io import is_dataset

    for scan_group in FioH5("test_00056.fio"):
        dataset_names = [item.name in scan_group["measurement"] if
                         is_dataset(item)]
        print("Found data columns in scan " + scan_group.name)
        print(", ".join(dataset_names))

You can test for existence of data or groups::

    >>> "/1.1/measurement/Pslit HGap" in sfh5
    True
    >>> "positioners" in sfh5["/2.1/instrument"]
    True
    >>> "spam" in sfh5["1.1"]
    False

.. note::

    Text used to be stored with a dtype ``numpy.string_`` in silx versions
    prior to *0.7.0*. The type ``numpy.string_`` is a byte-string format.
    The consequence of this is that you had to decode strings before using
    them in **Python 3**::

        >>> from silx.io.fioh5 import FioH5
        >>> sfh5 = FioH5("31oct98_00068.fio")
        >>> sfh5["/68.1/title"]
        b'ascan  tx3 -28.5 -24.5  20 0.5'
        >>> sfh5["/68.1/title"].decode()
        'ascan  tx3 -28.5 -24.5  20 0.5'

    From silx version *0.7.0* onwards, text is now stored as unicode. This
    corresponds to the default text type in python 3, and to the *unicode*
    type in Python 2.

    To be on the safe side, you can test for the presence of a *decode*
    attribute, to ensure that you always work with unicode text::

        >>> title = sfh5["/68.1/title"]
        >>> if hasattr(title, "decode"):
        ...     title = title.decode()

"""

__authors__ = ["T. Fuchs"]
__license__ = "MIT"
__date__ = "09/04/2021"


import os

import datetime
import logging
import io

import h5py
import numpy
import six

from silx import version as silx_version
from . import commonh5
from .spech5 import SpecH5NodeDataset

logger1 = logging.getLogger(__name__)

text_dtype = h5py.special_dtype(vlen=six.text_type)

ABORTLINENO = 5

dtypeConverter = {'STRING': 'U32',
                  'DOUBLE': 'f8',
                  'FLOAT': 'f4',
                  'INTEGER': 'i8',
                  'BOOLEAN': '?'}


def to_h5py_utf8(str_list):
    """Convert a string or a list of strings to a numpy array of
    unicode strings that can be written to HDF5 as utf-8.

    This ensures that the type will be consistent between python 2 and
    python 3, if attributes or datasets are saved to an HDF5 file.
    """
    return numpy.array(str_list, dtype=text_dtype)


def is_fiofile(filename):
    """Test if a file is a FIO file, by checking if three consecutive lines
    start with *!*. Tests up to ABORTLINENO lines at the start of the file.

    :param str filename: File path
    :return: *True* if file is a FIO file, *False* if it is not a FIO file
    :rtype: bool
    """
    if not os.path.isfile(filename):
        return False
    # test for presence of three ! in first lines
    with open(filename, "rb") as f:
        chunk = f.read(2500)
    count = 0
    for i, line in enumerate(chunk.split(b"\n")):
        if line.startswith(b"!"):
            count += 1
            if count >= 3:
                return True
        else:
            count = 0
        if i >= ABORTLINENO:
            break
    return False


class FioFile(object):
    """This class opens a FIO file and reads the data.

    It inherits :class:`silx.io.commonh5.Group` (via :class:`commonh5.File`),
    which implements most of its API.
    """

    def __init__(self, filepath):
        # parse filename
        filename = os.path.basename(filepath)
        fnowithsuffix = filename.split('_')[-1]
        try:
            self.scanno = int(fnowithsuffix.split('.')[0])
        except Exception:
            self.scanno = None
            logger1.warning("Cannot parse scan number of file %s", filename)

        with open(filepath, 'r') as fiof:

            prev = 0
            line_counter = 0

            while(True):
                line = fiof.readline()
                if line.startswith('!'):  # skip comments
                    prev = fiof.tell()
                    line_counter = 0
                    continue
                if line.startswith('%c'):
                    line_counter = 0
                    self.commentsection = ''
                    line = fiof.readline()
                    while(not line.startswith('%')
                            and not line.startswith('!')):
                        self.commentsection += line
                        prev = fiof.tell()
                        line = fiof.readline()
                if line.startswith('%p'):
                    line_counter = 0
                    self.parameterssection = ''
                    line = fiof.readline()
                    while(not line.startswith('%')
                            and not line.startswith('!')):
                        self.parameterssection += line
                        prev = fiof.tell()
                        line = fiof.readline()
                if line.startswith('%d'):
                    line_counter = 0
                    self.datacols = []
                    self.names = []
                    self.dtypes = []
                    line = fiof.readline()
                    while(line.startswith(' Col')):
                        splitline = line.split()
                        name = splitline[-2]
                        self.names.append(name)
                        dtype = dtypeConverter[splitline[-1]]
                        self.dtypes.append(dtype)
                        self.datacols.append((name, dtype))
                        prev = fiof.tell()
                        line = fiof.readline()
                    fiof.seek(prev)
                    break

                line_counter += 1
                if line_counter > ABORTLINENO:
                    raise IOError("Invalid fio file: Found no data "
                                  "after %s lines" % ABORTLINENO)

            self.data = numpy.loadtxt(fiof,
                                      dtype={'names': tuple(self.names),
                                             'formats': tuple(self.dtypes)},
                                      comments="!")

            # ToDo: read only last line of file,
            # which contains end of acquisition timestamp.

        self.parameter = {}

        # parse parameter section:
        try:
            for line in self.parameterssection.splitlines():
                param, value = line.split(' = ')
                self.parameter[param] = value
        except Exception:
            logger1.warning("Cannot parse parameter section %s",
                            self.parameterssection)

        # parse default sardana comments: username and start time
        try:
            commentlines = self.commentsection.splitlines()
            if len(commentlines) >= 2:
                self.title = commentlines[0]
                l2 = commentlines[1]
                acqpos = l2.lower().find("acq")

                self.user = l2[:acqpos][4:].strip()
                self.start_time = l2[acqpos+len("Acquisition started at"):].strip()
                commentlines = commentlines[2:]
            self.comments = "\n".join(commentlines[2:])

        except Exception:
            logger1.warning("Cannot parse default comment section %s",
                            self.commentsection)
            self.comments = self.commentsection
            self.user = ""
            self.start_time = ""
            self.title = ""


class FioH5(commonh5.File):
    """This class reads a FIO file and exposes it as a *h5py.File*.

    It inherits :class:`silx.io.commonh5.Group` (via :class:`commonh5.File`),
    which implements most of its API.
    """

    def __init__(self, filename, order=1):
        """
        :param filename: Path to FioFile in filesystem
        :type filename: str
        """
        if isinstance(filename, io.IOBase):
            # see https://github.com/silx-kit/silx/issues/858
            filename = filename.name

        fiof = FioFile(filename)  # reads complete file

        attrs = {"NX_class": to_h5py_utf8("NXroot"),
                 "file_time": to_h5py_utf8(
                         datetime.datetime.now().isoformat()),
                 "file_name": to_h5py_utf8(filename),
                 "creator": to_h5py_utf8("silx fioh5 %s" % silx_version)}
        commonh5.File.__init__(self, filename, attrs=attrs)

        if fiof.scanno is not None:
            scan_key = "%s.%s" % (fiof.scanno, int(order))
        else:
            scan_key = os.path.splitext(os.path.basename(filename))[0]

        scan_group = FioScanGroup(scan_key, parent=self, scan=fiof)
        self.add_node(scan_group)


class FioScanGroup(commonh5.Group):
    def __init__(self, scan_key, parent, scan):
        """

        :param parent: parent Group
        :param str scan_key: Scan key (e.g. "1.1")
        :param scan: FioFile object
        """
        if hasattr(scan, 'user'):
            userattr = to_h5py_utf8(scan.user)
        else:
            userattr = to_h5py_utf8('')
        commonh5.Group.__init__(self, scan_key, parent=parent,
                                attrs={"NX_class": to_h5py_utf8("NXentry"),
                                       "user": userattr})

        # 'title', 'start_time' and 'user' are defaults
        # in Sardana created files:
        if hasattr(scan, 'title'):
            title = scan.title
        else:
            title = scan_key  # use scan number as default title
        self.add_node(SpecH5NodeDataset(name="title",
                                        data=to_h5py_utf8(title),
                                        parent=self))

        if hasattr(scan, 'start_time'):
            start_time = scan.start_time
            self.add_node(SpecH5NodeDataset(name="start_time",
                                            data=to_h5py_utf8(start_time),
                                            parent=self))

        self.add_node(SpecH5NodeDataset(name="comments",
                                        data=to_h5py_utf8(scan.comments),
                                        parent=self))

        self.add_node(FioInstrumentGroup(parent=self, scan=scan))
        self.add_node(FioMeasurementGroup(parent=self, scan=scan))


class FioMeasurementGroup(commonh5.Group):
    def __init__(self, parent, scan):
        """

        :param parent: parent Group
        :param scan: FioFile object
        """
        commonh5.Group.__init__(self, name="measurement", parent=parent,
                                      attrs={"NX_class": to_h5py_utf8("NXcollection"), })

        for label in scan.names:
            safe_label = label.replace("/", "%")
            self.add_node(SpecH5NodeDataset(name=safe_label,
                                            data=scan.data[label],
                                            parent=self))


class FioInstrumentGroup(commonh5.Group):
    def __init__(self, parent, scan):
        """

        :param parent: parent Group
        :param scan: FioFile object
        """
        commonh5.Group.__init__(self, name="instrument", parent=parent,
                                      attrs={"NX_class": to_h5py_utf8("NXinstrument")})

        self.add_node(FioParameterGroup(parent=self, scan=scan))
        self.add_node(FioFileGroup(parent=self, scan=scan))
        self.add_node(SpecH5NodeDataset(name="comment",
                                        data=to_h5py_utf8(scan.comments),
                                        parent=self))


class FioFileGroup(commonh5.Group):
    def __init__(self, parent, scan):
        """

        :param parent: parent Group
        :param scan: FioFile object
        """
        commonh5.Group.__init__(self, name="fiofile", parent=parent,
                                      attrs={"NX_class": to_h5py_utf8("NXcollection")})

        self.add_node(SpecH5NodeDataset(name="comments",
                                        data=to_h5py_utf8(scan.commentsection),
                                        parent=self))

        self.add_node(SpecH5NodeDataset(name="parameter",
                                        data=to_h5py_utf8(scan.parameterssection),
                                        parent=self))


class FioParameterGroup(commonh5.Group):
    def __init__(self, parent, scan):
        """

        :param parent: parent Group
        :param scan: FioFile object
        """
        commonh5.Group.__init__(self, name="parameter", parent=parent,
                                      attrs={"NX_class": to_h5py_utf8("NXcollection")})

        for label in scan.parameter:
            safe_label = label.replace("/", "%")
            self.add_node(SpecH5NodeDataset(name=safe_label,
                                            ata=to_h5py_utf8(scan.parameter[label]),
                                            parent=self))

