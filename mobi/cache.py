# -*- coding: utf-8 -*-
#
# (c) 2018 Alberto Planas <aplanas@gmail.com>
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
import threading


class LockFile(object):
    """Class to create a POSIX lock based on a file."""

    # Store the number for locks for the same process
    _local = threading.local()

    def __init__(self, filename):
        self.filename = filename
        self._lck = None

    @property
    def lockers(self):
        try:
            return LockFile._local.lockers
        except AttributeError:
            LockFile._local.lockers = 0
            return LockFile._local.lockers

    @lockers.setter
    def lockers(self, value):
        LockFile._local.lockers = value

    # @lockers.deleter
    # def lockers(self):
    #     del LockFile._local.lockers

    def lock(self):
        # The lock is adquired per process.  If one process get two
        # times the lock, the first unlock will not release the lock,
        # but will do the second one.
        if not self.lockers:
            self._lck = open(self.filename, 'w')
            fcntl.flock(self._lck.fileno(), fcntl.LOCK_EX)
        self.lockers += 1
        return self

    def unlock(self):
        if not self.lockers:
            raise Exception('Unlock without lock')
        if self.lockers == 1:
            fcntl.flock(self._lck.fileno(), fcntl.LOCK_UN)
            self._lck.close()
            self._lck = None
        self.lockers -= 1

    def __enter__(self):
        return self.lock()

    def __exit__(self, *exc_info):
        self.unlock()


class DB(object):
    """Small wrapper over a Shelve to use the LockFile."""

    # Store the number of times that was open
    _local = threading.local()
    _local.openers = 0
    _local.db = None

    def __init__(self, dbname):
        self.dbname = dbname
        self.lck = dbname + '.lck'

    @property
    def openers(self):
        try:
            return DB._local.openers
        except AttributeError:
            DB._local.openers = 0
            return DB._local.openers

    @openers.setter
    def openers(self, value):
        DB._local.openers = value

    # @openers.deleter
    # def openers(self):
    #     del DB._local.openers

    @property
    def db(self):
        try:
            return DB._local.db
        except AttributeError:
            DB._local.db = None
            return DB._local.db

    @db.setter
    def db(self, value):
        DB._local.db = value

    # @db.deleter
    # def db(self):
    #     del DB._local.db

    def open(self):
        # In a similar way that happends with LockFile, openers is
        # unique per process (unless comes from a fork after this was
        # initialized)
        if not self.openers:
            self._lck = LockFile(self.lck)
            self._lck.lock()
            self.db = shelve.open(self.dbname, 'c')
        self.openers += 1
        return self.db

    def close(self):
        if not self.openers:
            raise Exception('Close without open')
        if self.openers == 1:
            self.db.close()
            self._lck.unlock()
            self._lck = None
            self.db = None
        self.openers -= 1

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc_info):
        self.close()


class Cache(collections.MutableMapping):
    """Generic class for cache."""

    # Configuration variables
    slots = 4096            # Number of slots in the cache file
    nclean = 1024           # Number of slots to remove when limit reached
    dbname = 'cache.dbm'    # Name of the database file

    def __init__(self, store):
        self.store = store

        # Create the cache directory if needed
        if not os.path.exists(store):
            os.makedirs(store)

        # Name of the cache database
        self.cache = os.path.join(store, self.dbname)

    def __getitem__(self, key):
        with DB(self.cache) as db:
            # The value is composed of two components:
            #   (value, creation_date)
            return db[key]

    def __setitem__(self, key, value):
        with DB(self.cache) as db:
            now = datetime.utcnow()
            db[key] = (value, now)

    def __delitem__(self, key):
        with DB(self.cache) as db:
            del db[key]

    def __iter__(self):
        with DB(self.cache) as db:
            for key in db:
                yield key

    def __len__(self):
        with DB(self.cache) as db:
            return len(db)

    def clean(self, ttl):
        """Remove entries older than `ttl` seconds."""
        now = datetime.utcnow()
        # The last part of the value is the `ttl`
        to_delete = (
            k for k, v in self.items()
            if (now - v[-1]).seconds > ttl
        )
        for key in to_delete:
            del self[key]

    def free(self):
        """If the cache is too big, remove a fix number of elements."""
        if len(self) > self.slots:
            elements = [(k, v[-1]) for k, v in self.items()]
            elements = sorted(elements, key=lambda x: x[-1])
            for key, _ in elements[:self.nclean]:
                del self[key]


class IssueCache(Cache):
    """Cache for issues."""

    def __init__(self, store, images_store):
        super(IssueCache, self).__init__(store)
        self.images_store = images_store

    def __setitem__(self, key, value):
        """Refresh the time for the stored images."""
        super(IssueCache, self).__setitem__(key, value)

        for i in value:
            if i['images']:
                image_path = i['images'][0]['path']
                image_path = os.path.join(self.images_store, image_path)
                # Set the current (atime, mtime) to `now`
                os.utime(image_path, None)

    def is_valid(self, url):
        """Check if URL is in the cache and the images are in the store."""
        if url not in self:
            return False

        # Ignore the creation date from the cache.
        images, _ = self[url]
        for i in images:
            if i['images']:
                image_path = i['images'][0]['path']
                image_path = os.path.join(self.images_store, image_path)
                if not os.path.isfile(image_path):
                    return False
        return True


class MobiCache(Cache):
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

    dbname = 'index.dbm'

    def __init__(self, store):
        super(MobiCache, self).__init__(store)

        # Create the data directory if needed
        self.data = os.path.join(store, 'data')
        if not os.path.exists(self.data):
            os.makedirs(self.data)

    def __data_file(self, key):
        """Return the full path of the data file."""
        # hashlib.md5 do not accept unicode
        key = key.encode('utf-8')
        name = hashlib.md5(key).hexdigest()
        return os.path.join(self.data, name)

    def __setitem__(self, key, value):
        with DB(self.cache):
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
            super(MobiCache, self).__setitem__(key, value_cache)

    def __delitem__(self, key):
        with DB(self.cache):
            for _, data_file in self[key][0]:
                os.unlink(data_file)
            super(MobiCache, self).__delitem__(key)
