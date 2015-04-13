#
# Copyright 2015 Rackspace, Inc
# All Rights Reserved
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
import os
import tempfile


FILE_PREFIX = "python-ironicclient"


def _seconds_since_modified(d):
    # TODO(mrda): Once we drop support for py26 we can just return
    # td.total_seconds() instead of calculating it ourselves.
    # Also, need to turn this back into an int for py3's division
    td = datetime.datetime.now() - datetime.datetime.fromtimestamp(d)
    return int((td.microseconds +
               (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6)


def _get_newest_file_and_cleanup(files):
    """Retrieve the newest file, and delete any old ones

    Return the most recently modified file from the list of files supplied,
    and delete all the others.
    """
    newest_file = None
    newest_file_mtime = None
    # If there's multiple cache files, use the newest
    for f in files:
        secs = _seconds_since_modified(os.path.getmtime(f))
        if newest_file is None or secs < newest_file_mtime:
            newest_file = f
            newest_file_mtime = secs

    # Delete all files but the newest
    for f in files:
        if f != newest_file:
            _delete_file(f)

    return newest_file


def _delete_file(filename):
    """Try and delete a file, suppress any errors."""
    try:
        os.unlink(filename)
    except Exception:
        pass


def _build_filename_prefix(host, port):
    """Build a filename based upon the hostname or address supplied."""
    return "%s-%s-%s-" % (FILE_PREFIX, host, port)


def save_data(host, port, data, dirname=None):
    """Save 'data' for a particular 'host' in the appropriate temp dir."""
    filename_prefix = _build_filename_prefix(host, port)
    # Note(mrda): We're using NamedtemporaryFile so as to avoid any races
    # surrounding ownership or simultaneous access.
    try:
        fd = tempfile.NamedTemporaryFile(prefix=filename_prefix,
                                         suffix='.txt', delete=False,
                                         dir=dirname)
        fd.write(data)
        fd.flush()
    except Exception:
        pass


def retrieve_data(host, port, expiry=600, dirname=None):
    """Retrieve the newest stored data stored for a particular 'host'."""
    filename_prefix = _build_filename_prefix(host, port)
    if dirname is None:
        # TODO(mrda): Is there an ironicclient's temp dir from config?
        dir_to_search = tempfile.gettempdir()
    else:
        dir_to_search = dirname
    filename_pattern = dir_to_search + os.sep + filename_prefix + '*'
    files = glob.glob(filename_pattern)
    if files:
        f = _get_newest_file_and_cleanup(files)
        if _seconds_since_modified(os.path.getmtime(f)) > expiry:
            # Too old to use
            _delete_file(f)
        else:
            # Try and open and return the first line in the file.
            # If we can't due to permissions or other errors, just fall
            # through and return nothing
            try:
                with open(f, 'r') as fd:
                    return fd.read()
            except Exception:
                pass
