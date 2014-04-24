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

import itertools
import os
import shutil
import subprocess
import uuid
import xml.etree.cElementTree as ET

from PIL import Image

from kindlestrip import SRCSStripper

KINDLEGEN = '../bin/kindlegen'
GENERATOR = 'kmanga'
WIDTH = 800
HEIGHT = 1280


class Container(object):
    def __init__(self, path):
        self.path = path
        self.image_info = None
        self.has_cover = False
        self._npages = 0

    def create(self):
        """Create an empty container."""
        if os.path.exists(self.path):
            raise ValueError('Container %s is not empty' % self.path)
        os.makedirs(os.path.join(self.path, 'html/images'))

    def clean(self):
        """Remove the container directoy and all the content."""
        os.removedirs(self.path)

    # def add_image(self, image):
    #     """Add a new PIL image into the container."""
    #     pass

    # def add_images(self, images):
    #     """Add a list of PIL images into the container."""
    #     for image in images:
    #         self.add_image(image)

    def add_image_file(self, image, order, as_link=False):
        """Add an image into the container."""
        img_dir = os.path.join(self.path, 'html/images')
        img_name = '%03d%s' % (order, os.path.splitext(image)[1])
        img_dst = os.path.join(img_dir, img_name)
        if as_link:
            os.link(image, img_dst)
        else:
            shutil.copyfile(image, img_dst)
        self._npages += 1

    def add_image_files(self, images, as_link=False):
        """Add a list of images into the container."""
        for order, image in enumerate(images):
            self.add_image_file(image, order, as_link)

    def set_cover_file(self, image, as_link=False):
        """Add an image as image cover."""
        cover_path = self.get_cover_path()
        if as_link:
            os.link(image, cover_path)
        else:
            shutil.copyfile(image, cover_path)
        self.has_cover = True

    def npages(self):
        """Return the total number of pages / images."""
        if not self._npages:
            images_path = os.path.join(self.path, 'html', 'images')
            files = [f for f in os.listdir(images_path) if f.endswith('jpg')]
            self._npages = len(files)
        return self._npages

    def get_image_info(self):
        """Get the list of (image_path, (size_x, size_y))."""
        if not self.image_info:
            html_path = os.path.join(self.path, 'html')
            images_path = os.path.join(self.path, 'html', 'images')
            files = [os.path.join('images', f)
                     for f in os.listdir(images_path) if f.endswith('jpg')]
            self.image_info = [(f, Image.open(os.path.join(html_path, f)).size)
                               for f in sorted(files)]
        return self.image_info

    def get_image_path(self, number, relative=False):
        """Get the path an image."""
        image_path = os.path.join('html', 'images', '%03d.jpg' % number)
        if not relative:
            image_path = os.path.join(self.path, image_path)
        return image_path

    def get_cover_path(self, relative=False):
        """Get the path of the cover image."""
        # XXX TODO -- The cover image can be of a different type
        image_path = 'cover.jpg'
        if not relative:
            image_path = os.path.join(self.path, image_path)
        return image_path

    def get_content_opf_path(self):
        """Get the path for content.opf."""
        return os.path.join(self.path, 'content.opf')

    def get_page_path(self, number, relative=False):
        """Get the path for page-XXX.html."""
        page_path = os.path.join('html', 'page-%03d.html' % number)
        if not relative:
            page_path = os.path.join(self.path, page_path)
        return page_path

    def get_toc_ncx_path(self):
        """Get the path for the toc.ncx."""
        return os.path.join(self.path, 'toc.ncx')


class MangaMobi(object):
    def __init__(self, container, info):
        self.container = container
        self.info = info

    def create(self):
        """Create the mobi file calling kindlegen."""
        self.content_opf()
        for i in range(len(self.info.pages)):
            self.page(i)
        self.toc_ncx()
        if not self.container.has_cover:
            cover = self.container.get_image_path(0)
            self.container.set_cover_file(cover)
        subprocess.call([KINDLEGEN, self.container.get_content_opf_path(),
                         '-o', 'tmp.mobi'])

        # Remove the SRCS section.
        tmp_name = os.path.join(self.container.path, 'tmp.mobi')
        name = '%s.mobi' % self.info.title.replace(' ', '_')
        full_name = os.path.join(self.container.path, name)
        with open(tmp_name, 'rb') as with_srcs:
            with open(full_name, 'wb') as without_srcs:
                stripper = SRCSStripper(with_srcs.read())
                without_srcs.write(stripper.get_result())
        return name, full_name

    def content_opf(self, identifier=None):
        """Generate and return the content OPF."""
        identifier = identifier if identifier else str(uuid.uuid1())
        package = ET.Element('package', {
            'version': '2.0',
            'unique-identifier': identifier,
            'xmlns': 'http://www.idpf.org/2007/opf',
        })

        metadata = ET.SubElement(package, 'metadata', {
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:opf': 'http://www.idpf.org/2007/opf',
        })

        ET.SubElement(metadata, 'dc:title').text = self.info.title
        ET.SubElement(metadata, 'dc:language').text = self.info.language
        ET.SubElement(metadata, 'dc:creator', {
            'opf:role': 'aut',
            'opf:file-as': self.info.author,
        }).text = self.info.author
        ET.SubElement(metadata, 'dc:publisher').text = self.info.publisher

        metas = (
            ('book-type', 'comic'),
            ('zero-gutter', 'true'),
            ('zero-margin', 'true'),
            ('fixed-layout', 'true'),
            ('generator', GENERATOR),
            # XXX WARNING - Maybe I can fix to 'portrait'
            ('orientation-lock', 'none'),
            # XXX TODO - Detect the read direction
            ('primary-writing-mode', 'horizontal-rl'),
            ('region-mag', 'false'),
            # XXX TODO - Detect the original resolution
            ('original-resolution', '%dx%d' % (WIDTH, HEIGHT)),
            ('cover', 'cover-image'),
        )
        for name, content in metas:
            ET.SubElement(metadata, 'meta', {
                'name': name,
                'content': content,
            })

        manifest = ET.SubElement(package, 'manifest')
        items = (
            ('toc.ncx', 'ncx', 'application/x-dtbncx+xml'),
            ('cover.jpg', 'cover-image', 'image/jpg'),
        )
        pages = [(self.container.get_page_path(n, relative=True),
                  'page-%03d' % n, 'application/xhtml+xml')
                 for n in range(self.container.npages())]

        for href, id_, media_type in itertools.chain(items, pages):
            ET.SubElement(manifest, 'item', {
                'id': id_,
                'href': href,
                'media-type': media_type,
            })

        spine = ET.SubElement(package, 'spine', {'toc': 'ncx'})
        for idref in range(self.container.npages()):
            ET.SubElement(spine, 'itemref', {
                'idref': 'page-%03d' % idref,
                'linear': 'yes',
            })

        tree = ET.ElementTree(package)
        with open(self.container.get_content_opf_path(), 'w') as f:
            tree.write(f, encoding='utf-8', xml_declaration=True)

    def _img_style(self, size):
        width, height = size
        ratio = min((WIDTH/float(width), HEIGHT/float(height)))
        width, height = int(ratio*width+0.5), int(ratio*height+0.5)
        assert width <= WIDTH and height <= HEIGHT, 'Scale error'
        style = 'width:%dpx;height:%dpx;' % (width, height)

        mtop, mleft = (HEIGHT - height) / 2, (WIDTH - width) / 2
        mbottom, mright = (HEIGHT - height) - mtop, (WIDTH - width) - mleft
        style += 'margin-top:%dpx;margin-bottom:%dpx;' % (mtop, mbottom)
        style += 'margin-left:%dpx;margin-right:%dpx;' % (mleft, mright)
        return style

    def page(self, number):
        """Generate and return the content of a page."""
        html = ET.Element('html')

        head = ET.SubElement(html, 'head')
        ET.SubElement(head, 'meta', {
            'name': 'generator',
            'content': GENERATOR,
        })
        title = ET.SubElement(head, 'title')
        title.text = str(number)

        body = ET.SubElement(html, 'body')
        div = ET.SubElement(body, 'div')

        img_path, img_size = self.container.get_image_info()[number]
        ET.SubElement(div, 'img', {
            'style': self._img_style(img_size),
            'src': img_path,
        })

        tree = ET.ElementTree(html)
        with open(self.container.get_page_path(number), 'w') as f:
            print >>f, '<!DOCTYPE html>'
            tree.write(f, encoding='utf-8', xml_declaration=False)

    def toc_ncx(self):
        """Generate and return the logical table of content."""
        ncx = ET.Element('ncx', {
            'version': '2005-1',
            'xml:lang': 'en-US',
            'xmlns': 'http://www.daisy.org/z3986/2005/ncx/'
        })

        head = ET.SubElement(ncx, 'head')
        metas = (
            ('dtb:uid', self.info.title),
            ('dtb:depth', '2'),
            ('dtb:totalPageCount', '0'),
            ('dtb:maxPageNumber', '0'),
            ('generated', 'true'),
        )
        for name, content in metas:
            ET.SubElement(head, 'meta', {
                'name': name,
                'content': content,
            })

        doc_title = ET.SubElement(ncx, 'docTitle')
        ET.SubElement(doc_title, 'text').text = self.info.title

        doc_author = ET.SubElement(ncx, 'docAuthor')
        ET.SubElement(doc_author, 'text').text = self.info.author

        nav_map = ET.SubElement(ncx, 'navMap')
        # XXX TODO - Add cover and copyright pages
        for n in range(self.container.npages()):
            nav_point = ET.SubElement(nav_map, 'navPoint', {
                'playOrder': str(n+1),
                'id': 'toc-%03d' % n,
            })
            nav_label = ET.SubElement(nav_point, 'navLabel')
            ET.SubElement(nav_label, 'text').text = 'Page-%03d' % n
            ET.SubElement(nav_point, 'content', {
                'src': self.container.get_page_path(n, relative=True)
            })

        tree = ET.ElementTree(ncx)
        with open(self.container.get_toc_ncx_path(), 'w') as f:
            print >>f, '<?xml version="1.0" encoding="UTF-8"?>'
            print >>f, '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">'
            tree.write(f, encoding='utf-8', xml_declaration=False)
