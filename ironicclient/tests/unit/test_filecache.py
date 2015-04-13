#
# Copyright 2012 Rackspace, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
import datetime
import glob
import mock
import operator
import os
import six
import tempfile
import time

from ironicclient.common import filecache
from ironicclient.tests.unit import utils


class FileCacheTest(utils.BaseTestCase):

    def setUp(self):
        super(FileCacheTest, self).setUp()

    def test__seconds_since_modified(self):
        delta = 10
        currsecs = time.mktime(datetime.datetime.now().timetuple())
        self.assertEqual(delta, filecache._seconds_since_modified(
            currsecs-delta))

    @mock.patch.object(filecache, '_delete_file', autospec=True)
    @mock.patch.object(os.path, 'getmtime', autospec=True)
    def test__get_newest_file_and_cleanup_one(self, mock_getmtime,
                                              mock_deletefile):
        filename = 'spam'
        mock_getmtime.return_value = 10
        files = [filename]
        self.assertEqual(filename,
                         filecache._get_newest_file_and_cleanup(files))
        self.assertEqual(0, mock_deletefile.call_count)
        mock_getmtime.assert_called_once_with(filename)

    @mock.patch.object(filecache, '_delete_file', autospec=True)
    @mock.patch.object(os.path, 'getmtime', autospec=True)
    @mock.patch.object(filecache, '_seconds_since_modified', autospec=True)
    def test__get_newest_file_and_cleanup_many(self, mock_secssincemod,
                                               mock_getmtime, mock_deletefile):
        d = {
            "eggs": 10,
            "spam": 5,
            "ham": 30,
            "guido": 7,
            }
        files = [x for x in d]
        most_recent = min(six.iteritems(d), key=operator.itemgetter(1))[0]

        def test_secssincemod(fn):
            return d[fn]

        def test_getmtime(fn):
            return fn

        mock_secssincemod.side_effect = test_secssincemod
        mock_getmtime.side_effect = test_getmtime

        self.assertEqual(most_recent,
                         filecache._get_newest_file_and_cleanup(files))
        self.assertEqual(len(d)-1, mock_deletefile.call_count)
        self.assertEqual(len(d), mock_getmtime.call_count)

    # Note(mrda): Can't autospec os.unlink
    @mock.patch.object(os, 'unlink')
    def test__delete_file(self, mock_u):
        mock_u.side_effect = Exception("foo")
        filecache._delete_file('somefile')
        self.assertEqual(1, mock_u.call_count)

    @mock.patch.object(tempfile, 'NamedTemporaryFile', autospec=True)
    def test_save_data_success(self, mock_ntf):
        host = "fred"
        port = 6789
        data = "lemming"
        dirname = "/var/openstack"
        filecache.save_data(host, port, data, dirname)
        prefix = filecache._build_filename_prefix(host, port)
        mock_ntf.assert_called_once_with(prefix=prefix, suffix=mock.ANY,
                                         delete=False, dir=dirname)

    @mock.patch.object(tempfile, 'NamedTemporaryFile', autospec=True)
    def test_save_data_fail(self, mock_ntf):
        mock_ntf.side_effect = Exception("foo")
        host = "fred"
        port = 6789
        data = "lemming"
        prefix = filecache._build_filename_prefix(host, port)
        filecache.save_data(host, port, data)
        mock_ntf.assert_called_once_with(prefix=prefix, suffix=mock.ANY,
                                         delete=False, dir=mock.ANY)

    @mock.patch.object(os.path, 'getmtime', autospec=True)
    @mock.patch.object(filecache, '_seconds_since_modified', autospec=True)
    @mock.patch.object(filecache, '_delete_file', autospec=True)
    @mock.patch.object(filecache, '_get_newest_file_and_cleanup',
                       autospec=True)
    @mock.patch.object(glob, 'glob', autospec=True)
    def test_retrieve_data_old_file(self, mock_glob, mock_gnfac,
                                    mock_deletefile, mock_ssm,
                                    mock_ospg):
        host = "localhost"
        port = 6789
        dirname = "/var/openstack/tmp"

        prefix = filecache._build_filename_prefix(host, port)
        globpattern = dirname + os.sep + prefix + '*'

        filelist = ['fred', 'wilma', 'barney', 'betty']
        mock_glob.return_value = filelist

        mock_gnfac.return_value = filelist[2]
        mock_ospg.return_value = mock.ANY
        mock_ssm.return_value = 1000

        self.assertEqual(None,
                         filecache.retrieve_data(host, port, dirname=dirname))
        mock_glob.assert_called_once_with(globpattern)
        mock_gnfac.assert_called_once_with(filelist)
        mock_deletefile.assert_called_once_with(filelist[2])
