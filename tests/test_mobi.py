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

import hashlib
import os
import unittest
from unittest.mock import patch
import shutil
import xml.dom.minidom

from PIL import Image
from PIL import ImageOps

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

        self.container.add_image('tests/fixtures/images/width-small.jpg',
                                 _filter=Container.FILTER_FOOTER)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/011.jpg'))

        self.container.add_image('tests/fixtures/images/width-small.jpg',
                                 _filter=Container.FILTER_MARGIN)
        self.assertTrue(
            os.path.exists('tests/fixtures/dummy/images/012.jpg'))

        self.assertEqual(self.container._npages, 13)
        self.assertEqual(self.container.npages(), 13)

    def test_add_images(self):
        pass

    @patch('mobi.mobi.Container.get_image_info')
    @patch('mobi.mobi.os.rename')
    def test_set_image_adjust(self, rename, get_image_info):
        self.container.set_image_adjust(0, None)
        get_image_info.assert_not_called()
        rename.assert_not_called()

        get_image_info.return_value = [['some_path', Container.ROTATE]]
        with self.assertRaises(ValueError):
            self.container.set_image_adjust(0, Container.ROTATE)

        get_image_info.return_value = [['some_path', None]]
        self.container.set_image_adjust(0, Container.ROTATE)
        rename.assert_called_with('tests/fixtures/dummy/some_path',
                                  'tests/fixtures/dummy/some_path_rotate')

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
            img, adjusted = self.container.adjust_image(img_path,
                                                        Container.RESIZE)
            self.assertTrue(adjusted)
            self.assertTrue(img.size[0] <= WIDTH and img.size[1] <= HEIGHT)
            self.assertTrue(img.size[0] == WIDTH or img.size[1] == HEIGHT)

            img, adjusted = self.container.adjust_image(img_path,
                                                        Container.RESIZE_CROP)
            self.assertTrue(adjusted)
            self.assertTrue(img.size[0] == WIDTH and img.size[1] == HEIGHT)

            img, adjusted = self.container.adjust_image(img_path,
                                                        Container.ROTATE)
            if name.endswith('horizontal.jpg'):
                self.assertTrue(adjusted)
                self.assertTrue(img.size[0] < img.size[1])
            else:
                self.assertFalse(adjusted)

            with self.assertRaises(ValueError):
                self.container.adjust_image(img_path, 'ERROR')

    def test_bbox(self):
        images = (
            ('width-small.jpg', (68, 192, 732, 1728)),
            ('width-large.jpg', (106, 128, 1094, 1152)),
            ('height-small.jpg', (30, 96, 370, 864)),
            ('height-large.jpg', (68, 192, 732, 1728)),
            ('height-small-horizontal.jpg', (96, 30, 864, 370)),
            ('height-large-horizontal.jpg', (192, 68, 1728, 732)),
            ('text-small.jpg', (0, 0, 800, 1858)),
            ('width-small-noise.jpg', (0, 0, 800, 1920)),
            ('width-large-noise.jpg', (10, 0, 1200, 1280)),
            ('height-large-noise.jpg', (4, 6, 796, 1728)),
            ('height-large-horizontal-noise.jpg', (16, 28, 1919, 788)),
        )
        for name, bbox in images:
            img_path = 'tests/fixtures/images/%s' % name
            img = Image.open(img_path)
            img = ImageOps.invert(img.convert(mode='L'))
            self.assertEqual(self.container.bbox(img), bbox)

    def test_filter_footer(self):
        images = (
            ('width-small.jpg', (648, 763),
             'd6ff04c9afeefa6f7b5fb1cf577e1a61'),
            ('width-large.jpg', (964, 503),
             '28cbf1700856063b657a532504efcb98'),
            ('height-small.jpg', (400, 960),
             'a1a08286b17d2935f346e53ed0675445'),
            ('height-large.jpg', (647, 758),
             '451a474981384d0030bf616c7452600c'),
            ('height-small-horizontal.jpg', (960, 400),
             'f2b3b2c73e5f8003167f1adfc657c5dc'),
            ('height-large-horizontal.jpg', (759, 648),
             '20d9dfaeed99c28f5c00bf9bec3019f2'),
            ('text-small.jpg', (799, 1760),
             '6d50fe4dd14c8fb3fe4d96e21abbef43'),
            ('width-small-noise.jpg', (800, 1914),
             'ca4a3eec0479b0de3c52014564310f29'),
            ('width-large-noise.jpg', (1186, 1280),
             '822b85eaf9f9fdd752c676f0157a2831'),
            ('height-large-noise.jpg', (788, 1327),
             '89c171ef1978dabf1d5325675dc76359'),
            ('height-large-horizontal-noise.jpg', (1883, 752),
             '00c10d9ca786eb96a0fe380327cf23d1'),
        )
        for name, size, hexdigest in images:
            img_path = 'tests/fixtures/images/%s' % name
            img = Image.open(img_path)
            img = self.container.filter_footer(img)
            self.assertEqual(img.size, size)
            self.assertEqual(hashlib.md5(img.tobytes()).hexdigest(), hexdigest)

    def test_filter_margin(self):
        images = (
            ('width-small.jpg', (660, 1536),
             '8309e0001bb633b82942b97637826780'),
            ('width-large.jpg', (984, 1024),
             '234480946116d1f82957cff78072d756'),
            ('height-small.jpg', (332, 768),
             '7438aa170cd8d620de280d997eb49582'),
            ('height-large.jpg', (660, 1536),
             '7c6f3076c7fcea309291af04570ce172'),
            ('height-small-horizontal.jpg', (768, 332),
             'd61247f58d4344c8715643f6029ac1f6'),
            ('height-large-horizontal.jpg', (1536, 660),
             'bdb979e21e59ff55dd55e6a9063396e2'),
            ('text-small.jpg', (660, 1661),
             'c61078de88e5d750f7ceb2ad335da888'),
            ('width-small-noise.jpg', (727, 1727),
             'a40432cb92359f56adb8e7b94230fdf9'),
            ('width-large-noise.jpg', (1100, 1146),
             '7a8257b6694fc6e7cd1f1775f4d46d09'),
            ('height-large-noise.jpg', (660, 1536),
             '6070649b3641cbfde7991313180890f0'),
            ('height-large-horizontal-noise.jpg', (1536, 660),
             '31344c6a937660e52294eb04cdaa0979'),
        )
        for name, size, hexdigest in images:
            img_path = 'tests/fixtures/images/%s' % name
            img = Image.open(img_path)
            img = self.container.filter_margin(img)
            self.assertEqual(img.size, size)
            self.assertEqual(hashlib.md5(img.tobytes()).hexdigest(), hexdigest)

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
                self.assertEqual(_xml_pretty(f1.read()), f2.read())

    # XXX TODO - Since firmware 5.8.5 Virtual Panels feature seems
    # to be disabled, and the only way to zoom in a area (as far
    # as I tested) is via Panel View.  Meanwhile I research this
    # topic, this test will not work.
    # def test_page_no_panel_view(self):
    #     self.mangamobi.page(0)
    #     page = 'tests/fixtures/dummy/html/page-000.html'
    #     with open(page) as f1:
    #         with open(page+'.no-panel-view.reference') as f2:
    #             self.assertEqual(_xml_pretty(f1.read()), f2.read())

    def test_page_panel_view(self):
        self.container.add_image(
            'tests/fixtures/images/height-large-horizontal.jpg',
            adjust=Container.ROTATE)
        self.mangamobi.page(0)
        page = 'tests/fixtures/dummy/html/page-000.html'
        with open(page) as f1:
            with open(page+'.panel-view.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), f2.read())

    def test_toc_ncx(self):
        self.mangamobi.toc_ncx()
        with open('tests/fixtures/dummy/toc.ncx') as f1:
            with open('tests/fixtures/dummy/toc.ncx.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), f2.read())

    def test_nav(self):
        self.mangamobi.nav()
        with open('tests/fixtures/dummy/nav.xhtml') as f1:
            with open('tests/fixtures/dummy/nav.xhtml.reference') as f2:
                self.assertEqual(_xml_pretty(f1.read()), f2.read())

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
