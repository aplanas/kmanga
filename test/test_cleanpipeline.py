# -*- coding: utf-8; -*-
#
# (c) 2014 Alberto Planas <aplanas@gmail.com>
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

import unittest

from scraper.pipelines import CleanBasePipeline


class TestCleanBasePipeline(unittest.TestCase):

    def setUp(self):
        self.clean = CleanBasePipeline()

    def tearDown(self):
        self.clean = None

    def test_as_str(self):
        self.assertEqual(self.clean._as_str([u' ', u' ']), u'')
        self.assertEqual(self.clean._as_str([u' ', u'a']), u'a')
        self.assertEqual(self.clean._as_str([u' 5', u' 0'], separator=''),
                         u'50')
