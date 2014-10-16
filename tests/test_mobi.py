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
import shutil
import xml.dom.minidom

from mobi import Container, MangaMobi
from mobi.mobi import WIDTH, HEIGHT
from scraper.pipelines import MobiCache


_xml_pretty = lambda x: xml.dom.minidom.parseString(x).toprettyxml(indent='  ')


class Info(object):
    def __init__(self, **info):
        self.__dict__.update(info)


class TestMangaMobi(unittest.TestCase):

    def setUp(self):
        shutil.copytree('tests/fixtures/container01', 'tests/fixtures/dummy')
        self.container = Container('tests/fixtures/dummy')
        self.info = Info(title='title', language='en', publisher='publisher',
                         author='author')
        self.mangamobi = MangaMobi(self.container, self.info)

    def tearDown(self):
        self.container.clean()

    def test_container_get_image_info(self):
        info = self.container.get_image_info()
        self.assertEqual(len(info), 6)
        e1 = ('images/000.jpg', (800, 1280), 12547)
        self.assertEqual(info[0], e1)
        e5 = ('images/005.jpg', (800, 1280), 12547)
        self.assertEqual(info[-1], e5)

    def test_container_get_X_path(self):
        self.assertEqual(self.container.get_content_opf_path(),
                         'tests/fixtures/dummy/content.opf')
        self.assertEqual(self.container.get_page_path(1),
                         'tests/fixtures/dummy/html/page-001.html')
        self.assertEqual(self.container.get_toc_ncx_path(),
                         'tests/fixtures/dummy/toc.ncx')

    def test_mangamobi_content_opf(self):
        self.mangamobi.content_opf(identifier='id')
        with open('tests/fixtures/dummy/content.opf') as f1:
            with open('tests/fixtures/dummy/content.opf.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_mangamobi_toc_ncx(self):
        self.mangamobi.toc_ncx()
        with open('tests/fixtures/dummy/toc.ncx') as f1:
            with open('tests/fixtures/dummy/toc.ncx.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_img_style(self):
        style = self.mangamobi._img_style((900, 1276))
        self.assertTrue('width:800px;height:1134px;' in style)
        self.assertTrue('margin-top:73px;margin-bottom:73px;' in style)
        self.assertTrue('margin-left:0px;margin-right:0px;' in style)
        style = self.mangamobi._img_style((1000, 702))
        self.assertTrue('width:800px;height:562px;' in style)
        self.assertTrue('margin-top:359px;margin-bottom:359px;' in style)
        self.assertTrue('margin-left:0px;margin-right:0px;' in style)
        style = self.mangamobi._img_style((800, 1280))
        self.assertTrue('width:800px;height:1280px;' in style)
        self.assertTrue('margin-top:0px;margin-bottom:0px;' in style)
        self.assertTrue('margin-left:0px;margin-right:0px;' in style)

    def test_adjust_image(self):
        for name in ('width-small.jpg', 'width-large.jpg',
                     'height-small.jpg', 'height-large.jpg',
                     'height-small-horizontal.jpg',
                     'height-large-horizontal.jpg'):
            img_path = 'tests/fixtures/images/%s' % name
            img = self.container.adjust_image(img_path, Container.RESIZE)
            self.assertTrue(img.size[0] <= WIDTH and img.size[1] <= HEIGHT)
            self.assertTrue(img.size[0] == WIDTH or img.size[1] == HEIGHT)

            img = self.container.adjust_image(img_path, Container.RESIZE_CROP)
            self.assertTrue(img.size[0] == WIDTH and img.size[1] == HEIGHT)

            img = self.container.adjust_image(img_path, Container.ROTATE)
            self.assertTrue(img.size[0] < img.size[1])

    def test_size(self):
        self.assertTrue(self.container.get_size(), 75282)

    def test_split(self):
        containers = self.container.split(12547*2)
        self.assertTrue(len(containers) == 3)
        for c in containers:
            self.assertTrue(c.get_size() <= 12547*2)
            self.assertTrue(len(c.get_image_info()) == 2)
            self.assertTrue(c.get_cover_path())
            c.clean()


class TestMobiCache(unittest.TestCase):

    def setUp(self):
        self.cache = MobiCache('tests/fixtures/cache/cache')

    def tearDown(self):
        shutil.rmtree('tests/fixtures/cache/cache')

    def test_cache(self):
        self.cache[('spider', 'mobi', '1')] = [
            ('mobi1.mobi', 'tests/fixtures/cache/mobi1.mobi')]
        self.cache[('spider', 'mobi', '2')] = [
            ('mobi2.1.mobi', 'tests/fixtures/cache/mobi2.1.mobi'),
            ('mobi2.2.mobi', 'tests/fixtures/cache/mobi2.2.mobi')]
        self.cache[('spider', 'mobi', '3')] = [
            ('mobi3.mobi', 'tests/fixtures/cache/mobi3.mobi')]
        self.assertTrue(len(self.cache) == 3)
        for key in self.cache:
            self.assertTrue(len(key) == 3)
        del self.cache[('spider', 'mobi', '1')]
        self.assertTrue(len(self.cache) == 2)
        self.assertTrue(('spider', 'mobi', '1') not in self.cache)
        self.assertTrue(('spider', 'mobi', '2') in self.cache)


if __name__ == '__main__':
    unittest.main()
