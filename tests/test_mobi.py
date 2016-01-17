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

import os
import unittest
import shutil
import xml.dom.minidom

from mobi import Container, MangaMobi
from mobi.mobi import WIDTH, HEIGHT


_xml_pretty = lambda x: xml.dom.minidom.parseString(x).toprettyxml(indent='  ')


class Info(object):
    def __init__(self, **info):
        self.__dict__.update(info)


class TestContainer(unittest.TestCase):

    def setUp(self):
        shutil.copytree('tests/fixtures/container01', 'tests/fixtures/dummy')
        self.container = Container('tests/fixtures/dummy')
        # Count the number of current pages as a side effect
        self.container.npages()
        # There is a cover.jpg in the container
        self.container.has_cover = True

    def tearDown(self):
        self.container.clean()

    def test_create_new(self):
        container = Container('tests/fixtures/empty')
        container.create()
        self.assertTrue(os.path.exists('tests/fixtures/empty'))
        container.clean()
        self.assertFalse(os.path.exists('tests/fixtures/empty'))

    def test_create(self):
        with self.assertRaises(ValueError):
            self.container.create(clean=False)
        self.assertTrue(os.path.exists('tests/fixtures/dummy/cover.jpg'))
        self.container.create(clean=True)
        self.assertFalse(os.path.exists('tests/fixtures/dummy/cover.jpg'))

    def test_add_image(self):
        self.container.add_image('tests/fixtures/images/width-small.jpg')
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/006.jpg'))

        self.container.add_image('tests/fixtures/images/width-small.jpg',
                                 as_link=True)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/007.jpg'))

        self.container.add_image('tests/fixtures/images/width-small.jpg',
                                 adjust=Container.ROTATE)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/008.jpg'))

        self.container.add_image(
            'tests/fixtures/images/height-large-horizontal.jpg',
            adjust=Container.ROTATE)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/009_rotate.jpg'))

        self.container.add_image('tests/fixtures/images/width-small-bw.png',
                                 adjust=Container.ROTATE)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/010.png'))

        self.assertEqual(self.container._npages, 11)
        self.assertEqual(self.container.npages(), 11)

    def test_add_images(self):
        pass

    def test_set_cover(self):
        os.unlink('tests/fixtures/dummy/cover.jpg')
        self.container.set_cover('tests/fixtures/images/width-small.jpg')
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/cover.jpg'))

        os.unlink('tests/fixtures/dummy/cover.jpg')
        self.container.set_cover('tests/fixtures/images/width-small.jpg',
                                 as_link=True)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/cover.jpg'))

        self.container.set_cover(
            'tests/fixtures/images/height-large-horizontal.jpg',
            adjust=Container.ROTATE)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/cover.jpg'))

        os.unlink('tests/fixtures/dummy/cover.jpg')
        self.container.set_cover('tests/fixtures/images/width-small-bw.png',
                                 adjust=Container.ROTATE)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/cover.jpg'))

    def test_get_image_info(self):
        info = self.container.get_image_info()
        self.assertEqual(len(info), 6)
        e1 = ('images/000.jpg', (800, 1280), 12547, None)
        self.assertEqual(info[0], e1)
        e5 = ('images/005.jpg', (800, 1280), 12547, None)
        self.assertEqual(info[-1], e5)

        self.container.add_image(
            'tests/fixtures/images/height-large-horizontal.jpg',
            adjust=Container.ROTATE)
        info = self.container.get_image_info()
        e6 = ('images/006_rotate.jpg', (800, 1920), 33336, Container.ROTATE)
        self.assertEqual(info[-1], e6)

        info2 = self.container.get_image_info()
        self.assertEqual(info, info2)

    def test_get_image_mime_type(self):
        self.assertEqual(
            self.container.get_image_mime_type(0),
            'image/jpeg')

    def test_container_get_path(self):
        with self.assertRaises(ValueError):
            self.container.get_image_path(10)

        self.assertEqual(self.container.get_image_path(1),
                         'tests/fixtures/dummy/images/001.jpg')
        self.assertEqual(self.container.get_image_path(1, relative=True),
                         'images/001.jpg')

        # Duplicate the third image
        os.link('tests/fixtures/dummy/images/002.jpg',
                'tests/fixtures/dummy/images/002.png')
        with self.assertRaises(ValueError):
            self.container.get_image_path(2)

        # Remove the third image
        os.unlink('tests/fixtures/dummy/images/002.jpg')
        os.unlink('tests/fixtures/dummy/images/002.png')
        with self.assertRaises(ValueError):
            self.container.get_image_path(2)

        self.assertEqual(self.container.get_cover_path(),
                         'tests/fixtures/dummy/cover.jpg')
        self.assertEqual(self.container.get_cover_path(relative=True),
                         'cover.jpg')

        self.assertEqual(self.container.get_content_opf_path(),
                         'tests/fixtures/dummy/content.opf')
        self.assertEqual(self.container.get_content_opf_path(relative=True),
                         'content.opf')

        self.assertEqual(self.container.get_page_path(1),
                         'tests/fixtures/dummy/html/page-001.html')
        self.assertEqual(self.container.get_page_path(1, relative=True),
                         'html/page-001.html')

        self.assertEqual(self.container.get_toc_ncx_path(),
                         'tests/fixtures/dummy/toc.ncx')
        self.assertEqual(self.container.get_toc_ncx_path(relative=True),
                         'toc.ncx')

        self.assertEqual(self.container.get_nav_path(),
                         'tests/fixtures/dummy/nav.xhtml')
        self.assertEqual(self.container.get_nav_path(relative=True),
                         'nav.xhtml')

        self.assertEqual(self.container.get_style_css_path(),
                         'tests/fixtures/dummy/css/style.css')
        self.assertEqual(self.container.get_style_css_path(relative=True),
                         'css/style.css')

    def test_get_size(self):
        self.assertTrue(self.container.get_size(), 75282)

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
            if name.endswith('horizontal.jpg'):
                self.assertTrue(img.size[0] < img.size[1])
            else:
                self.assertEqual(img, None)

            with self.assertRaises(ValueError):
                self.container.adjust_image(img_path, 'ERROR')

    def _test_container_split(self, has_cover):
        self.container.has_cover = has_cover
        containers = self.container.split(12547*2)
        self.assertTrue(len(containers) == 3)
        for c in containers:
            self.assertTrue(c.get_size() <= 12547*2)
            self.assertTrue(len(c.get_image_info()) == 2)
            self.assertTrue(c.get_cover_path())
            c.clean()

    def test_split_with_cover(self):
        self._test_container_split(has_cover=True)

    def test_split_without_cover(self):
        self._test_container_split(has_cover=False)


class TestMangaMobi(unittest.TestCase):

    def setUp(self):
        shutil.copytree('tests/fixtures/container01', 'tests/fixtures/dummy')
        self.container = Container('tests/fixtures/dummy')
        # Count the number of current pages as a side effect
        self.container.npages()
        # There is a cover.jpg in the container
        self.container.has_cover = True
        self.info = Info(title='title', language='en', publisher='publisher',
                         author='author', reading_direction='horizontal-rl')
        self.mangamobi = MangaMobi(self.container, self.info,
                                   kindlegen='bin/kindlegen')

    def tearDown(self):
        self.container.clean()

    def _test_create(self, has_cover):
        self.container.has_cover = has_cover
        full_path = self.mangamobi.create()
        self.assertEqual(full_path, 'tests/fixtures/dummy/title.mobi')
        self.assertTrue(os.path.exists(full_path))

    def test_create_with_cover(self):
        self._test_create(has_cover=True)

    def test_create_without_cover(self):
        self._test_create(has_cover=False)

    def test_content_opf(self):
        self.mangamobi.content_opf(identifier='id')
        with open('tests/fixtures/dummy/content.opf') as f1:
            with open('tests/fixtures/dummy/content.opf.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_page_no_panel_view(self):
        self.mangamobi.page(0)
        page = 'tests/fixtures/dummy/html/page-000.html'
        with open(page) as f1:
            with open(page+'.no-panel-view.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_page_panel_view(self):
        self.container.add_image(
            'tests/fixtures/images/height-large-horizontal.jpg',
            adjust=Container.ROTATE)
        self.mangamobi.page(0)
        page = 'tests/fixtures/dummy/html/page-000.html'
        with open(page) as f1:
            with open(page+'.panel-view.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_toc_ncx(self):
        self.mangamobi.toc_ncx()
        with open('tests/fixtures/dummy/toc.ncx') as f1:
            with open('tests/fixtures/dummy/toc.ncx.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_nav(self):
        self.mangamobi.nav()
        with open('tests/fixtures/dummy/nav.xhtml') as f1:
            with open('tests/fixtures/dummy/nav.xhtml.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), unicode(f2.read()))

    def test_style_css(self):
        self.mangamobi.style_css()
        with open('tests/fixtures/dummy/css/style.css') as f1:
            with open('tests/fixtures/dummy/css/style.css.reference') as f2:
                self.assertEqual(f1.read(), f2.read())

    # def test_img_style(self):
    #     style = self.mangamobi._img_style((900, 1276))
    #     self.assertTrue('width:800px;height:1134px;' in style)
    #     self.assertTrue('margin-top:73px;margin-bottom:73px;' in style)
    #     self.assertTrue('margin-left:0px;margin-right:0px;' in style)
    #     style = self.mangamobi._img_style((1000, 702))
    #     self.assertTrue('width:800px;height:562px;' in style)
    #     self.assertTrue('margin-top:359px;margin-bottom:359px;' in style)
    #     self.assertTrue('margin-left:0px;margin-right:0px;' in style)
    #     style = self.mangamobi._img_style((800, 1280))
    #     self.assertTrue('width:800px;height:1280px;' in style)
    #     self.assertTrue('margin-top:0px;margin-bottom:0px;' in style)
    #     self.assertTrue('margin-left:0px;margin-right:0px;' in style)


if __name__ == '__main__':
    unittest.main()
