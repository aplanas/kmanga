# -*- coding: utf-8; -*-
#
# (c) 2015 Alberto Planas <aplanas@gmail.com>
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

import mock

from scraper.middlewares import SmartProxy


class Proxy(object):
    def __init__(self, proxy):
        self.proxy = proxy


class TestSmartProxy(unittest.TestCase):

    def setUp(self):
        self.proxy = SmartProxy()

    def tearDown(self):
        self.proxy = None

    def test_process_request_skip(self):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()
        self.proxy.process_request(request_mock, spider_mock)

        spider_mock._operation = 'no-manga'
        self.proxy.process_request(request_mock, spider_mock)

        request_mock.meta = {'proxy': 'proxy'}
        spider_mock._operation = 'manga'
        self.proxy.process_request(request_mock, spider_mock)

    @mock.patch('scraper.middlewares.needs_proxy')
    def test_process_request_skip2(self, needs_proxy):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()

        request_mock.meta = {}
        spider_mock._operation = 'manga'
        spider_mock.name = 'spider'
        needs_proxy.return_value = False
        self.proxy.process_request(request_mock, spider_mock)

        needs_proxy.assert_called_once_with('spider')

    @mock.patch('scraper.middlewares.Proxy')
    @mock.patch('scraper.middlewares.needs_proxy')
    def test_process_request_proxy(self, needs_proxy, proxy):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()

        request_mock.meta = {}
        spider_mock._operation = 'manga'
        spider_mock.name = 'spider'
        needs_proxy.return_value = True

        order_by = mock.Mock(**{'first.return_value': Proxy('myproxy')})
        filter_ = mock.Mock(**{'order_by.return_value': order_by})
        proxy.objects = mock.Mock(**{'filter.return_value': filter_})

        self.proxy.process_request(request_mock, spider_mock)

        self.assertTrue('proxy' in request_mock.meta)
        self.assertEqual(request_mock.meta['proxy'], 'http://myproxy')

    @mock.patch('scraper.middlewares.Proxy')
    @mock.patch('scraper.middlewares.needs_proxy')
    def test_process_request_no_proxy(self, needs_proxy, proxy):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()

        request_mock.meta = {}
        spider_mock._operation = 'manga'
        spider_mock.name = 'spider'
        needs_proxy.return_value = True

        order_by = mock.Mock(**{'first.return_value': None})
        filter_ = mock.Mock(**{'order_by.return_value': order_by})
        proxy.objects = mock.Mock(**{'filter.return_value': filter_})

        self.proxy.process_request(request_mock, spider_mock)

        self.assertTrue('proxy' not in request_mock.meta)

    def test_process_exception_skip(self):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()
        request_mock.meta = {}
        self.proxy.process_exception(request_mock, None, spider_mock)

    @mock.patch('scraper.middlewares.Proxy')
    def test_process_exception(self, proxy):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()
        request_mock.meta = {'proxy': 'http://myproxy'}
        self.proxy.process_exception(request_mock, None, spider_mock)

        self.assertTrue('proxy' not in request_mock.meta)

    @mock.patch('scraper.middlewares.Proxy')
    def test_process_exception_error(self, proxy):
        request_mock = mock.Mock()
        spider_mock = mock.Mock()
        request_mock.meta = {'proxy': 'http://myproxy'}

        proxy.DoesNotExist = Exception
        proxy.objects = mock.Mock(**{'get.side_effect': proxy.DoesNotExist()})
        self.proxy.process_exception(request_mock, None, spider_mock)

        self.assertTrue('proxy' not in request_mock.meta)
