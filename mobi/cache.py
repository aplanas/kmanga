# -*- coding: utf-8 -*-
#
# (c) 2016 Alberto Planas <aplanas@gmail.com>
#
# This file is part of KManga.
#
# KManga is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KManga is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with KManga.  If not, see <http://www.gnu.org/licenses/>.

import collections
from datetime import datetime
import fcntl
import hashlib
import os
import shelve


class LockFile(object):
    """Class to create a POSIX lock based on a file."""

    # Store the number for locks for the same process
    lockers = 0

    def __init__(self, filename):
        self.filename = filename
        self._lck = None

    def lock(self):
        # The lock is adquired per process.  If one process get two
        # times the lock, the first unlock will not release the lock,
        # but will do the second one.
        if not LockFile.lockers:
            self._lck = open(self.filename, 'w')
            fcntl.flock(self._lck.fileno(), fcntl.LOCK_EX)
        LockFile.lockers += 1
        return self

    def unlock(self):
        if LockFile.lockers == 0:
            raise Exception('Unlock without lock')
        if LockFile.lockers == 1:
            fcntl.flock(self._lck.fileno(), fcntl.LOCK_UN)
            self._lck.close()
            self._lck = None
        LockFile.lockers -= 1

    def __enter__(self):
        return self.lock()

    def __exit__(self, *exc_info):
        self.unlock()


class MobiCache(collections.MutableMapping):
    """Cache for `.mobi` documents.

    This cache avoid the creation of new MOBI documents previously
    created.

    The `key` is expected to be an URL, and the value assigned is
    expected to be a list of MOBI file paths.

    key = 'url'
    value = [
        'tests/fixtures/cache/mobi1.1.mobi',
        'tests/fixtures/cache/mobi1.2.mobi'
    ]

    Can only be used to recover the MOBI content and the URL, for the
    rest of the information (name, issue number, manga, etc) we need
    to consult the database.

    Important note, the path of the mobi file will change once is
    stored in the cache.  So, for example:

    >>> cache['url'] = ['store/mobi1.mobi']
    >>> cache['url']
    ([('mobi1.mobi', 'cache/<md5_of(url)>')], <creation_date>)

    """

    # Configuration variables
    SLOTS = 4096            # Number of slots in the cache file
    NCLEAN = 1024           # Number of slots to remove when limit reached

    def __init__(self, mobi_store):
        self.mobi_store = mobi_store

        # Create the cache directory if needed
        cache = os.path.join(mobi_store, 'cache')
        if not os.path.exists(cache):
            os.makedirs(cache)

        # Create the index database if needed
        index = os.path.join(cache, 'index.db')
        self.index = shelve.open(index, 'c')

        # Create the data directory if needed
        self.data = os.path.join(cache, 'data')
        if not os.path.exists(self.data):
            os.makedirs(self.data)

        self.lck = os.path.join(mobi_store, 'cache', 'index.lck')

    def __data_file(self, key):
        """Return the full path of the data file."""
        name = hashlib.md5(key).hexdigest()
        return os.path.join(self.data, name)

    def __getitem__(self, key):
        with LockFile(self.lck):
            # The value is composed of two components:
            #   (list_of_tuples_of_names_and_paths, creation_date)
            return self.index[key]

    def __setitem__(self, key, value):
        with LockFile(self.lck):
            # Makes sure that the element is not there anymore.
            if key in self:
                del self[key]

            # Create the links into the data store and create the
            # values stored in the index database.
            data_file_prefix = self.__data_file(key)
            value_cache = []
            for i, full_path in enumerate(value):
                name = os.path.basename(full_path)
                data_file = '%s-%02d' % (data_file_prefix, i)
                os.link(full_path, data_file)
                value_cache.append((name, data_file))

            # Store the value in the index database.  The value is
            # composed by the list of the mobi names and the paths of
            # the mobi file in the data cache directory, and the UTC
            # time when was stored.
            now = datetime.utcnow()
            self.index[key] = (value_cache, now)

    def __delitem__(self, key):
        with LockFile(self.lck):
            for _, data_file in self[key][0]:
                os.unlink(data_file)
            del self.index[key]

    def __iter__(self):
        with LockFile(self.lck):
            for key in self.index.keys():
                yield key

    def __len__(self):
        return len(self.index)

    def clean(self, ttl):
        """Remove entries older than `ttl` seconds."""
        now = datetime.utcnow()
        # The last part of the value is the `ttl`
        to_delete = (
            k for k, v in self.index.iteritems()
            if (now - v[-1]).seconds > ttl
        )
        for key in to_delete:
            del self[key]

    def free(self):
        """If the cache is too big, remove a fix number of elements."""
        if len(self) > MobiCache.SLOTS:
            elements = [(k, v[-1]) for k, v in self.index.iteritems()]
            elements = sorted(elements, key=lambda x: x[-1])
            for key, _ in elements[:MobiCache.NCLEAN]:
                del self[key]
