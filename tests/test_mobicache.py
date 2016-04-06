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

import hashlib
from multiprocessing import Process
import os
import unittest
import shutil
import time

from mobi.cache import LockFile
from mobi.cache import MobiCache


def write_file(fname, text, lock):
    # We need to sleep, to guarantee that the start of the process
    # happends before adquiring the lock
    time.sleep(0.1)
    with LockFile(lock):
        with open(fname, 'a') as f:
            f.write(text)


class TestLockFile(unittest.TestCase):
    LOCK = 'tests/fixtures/cache/lock.lck'
    FNAME = 'tests/fixtures/cache/test.txt'

    def setUp(self):
        self.lock = LockFile(TestLockFile.LOCK)

    def tearDown(self):
        for fname in (TestLockFile.LOCK, TestLockFile.FNAME):
            if os.path.exists(fname):
                os.unlink(fname)

    def test_lock_unclock(self):
        self.lock.lock()
        self.assertTrue(os.path.exists(TestLockFile.LOCK))
        self.lock.unlock()
        self.assertTrue(os.path.exists(TestLockFile.LOCK))

    def test_unlock(self):
        with self.assertRaises(Exception):
            self.lock.unlock()

    def test_multilocks(self):
        self.lock.lock()
        self.assertEqual(self.lock.lockers, 1)
        self.lock.lock()
        self.assertEqual(self.lock.lockers, 2)
        self.lock.unlock()
        self.assertEqual(self.lock.lockers, 1)
        self.lock.unlock()
        self.assertEqual(self.lock.lockers, 0)
        with self.assertRaises(Exception):
            self.lock.unlock()

    def test_context(self):
        with self.lock as lock:
            self.assertEqual(lock.lockers, 1)
            self.assertEqual(LockFile._local.lockers, 1)
        self.assertEqual(lock.lockers, 0)

    def test_lock(self):
        p = Process(target=write_file,
                    args=(self.FNAME, 'process', self.LOCK))
        p.start()
        with self.lock:
            # Give time to `write_file` to try to run
            time.sleep(0.5)
            with open(self.FNAME, 'a') as f:
                f.write('parent')
        p.join()
        # We expect to find the text 'parentprocess'
        self.assertEqual(open(self.FNAME).read(), 'parentprocess')


class TestMobiCache(unittest.TestCase):

    def setUp(self):
        self.cache = MobiCache('tests/fixtures/tmp')

    def tearDown(self):
        shutil.rmtree('tests/fixtures/tmp')

    def test_cache(self):
        self.cache['url1'] = ['tests/fixtures/cache/mobi1.mobi']
        self.cache['url2'] = [
            'tests/fixtures/cache/mobi2.1.mobi',
            'tests/fixtures/cache/mobi2.2.mobi'
        ]
        self.cache['url3'] = ['tests/fixtures/cache/mobi3.mobi']
        self.assertTrue(len(self.cache) == 3)

        md5 = hashlib.md5('url1').hexdigest()
        self.assertEqual(
            self.cache['url1'][0],
            [('mobi1.mobi', 'tests/fixtures/tmp/cache/data/%s-00' % md5)]
        )

        for key in self.cache:
            self.assertTrue(key in ('url1', 'url2', 'url3'))
            v = self.cache[key]
            if key in ('url1', 'url3'):
                self.assertTrue(len(v[0]) == 1)
            else:
                self.assertTrue(len(v[0]) == 2)
        del self.cache['url1']
        self.assertTrue(len(self.cache) == 2)
        self.assertTrue('url1' not in self.cache)
        self.assertTrue('url2' in self.cache)
        self.assertTrue('url3' in self.cache)


if __name__ == '__main__':
    unittest.main()
