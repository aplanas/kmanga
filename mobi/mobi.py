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
import re
import shutil
import subprocess
import uuid
import xml.etree.cElementTree as ET

from PIL import Image

KINDLEGEN = '../bin/kindlegen'
GENERATOR = 'kmanga'
WIDTH = 800
HEIGHT = 1280


class Container(object):
    # Values for 'adjust' parameter
    RESIZE = 'resize'
    RESIZE_CROP = 'resize_crop'
    ROTATE = 'rotate'
    # SPLIT = 'split'

    def __init__(self, path):
        self.path = path
        self.has_cover = False
        self._image_info = []
        self._npages = 0

    def create(self, clean=False):
        """Create an empty container."""
        if os.path.exists(self.path):
            if clean:
                self.clean()
            else:
                raise ValueError('Container %s is not empty' % self.path)
        os.makedirs(os.path.join(self.path, 'html/images'))

    def clean(self):
        """Remove the container directoy and all the content."""
        shutil.rmtree(self.path)

    def add_image(self, image, order, adjust=None, as_link=False):
        """Add an image into the container."""
        img_dir = os.path.join(self.path, 'html/images')
        img_name = '%03d%s' % (order, os.path.splitext(image)[1])
        img_dst = os.path.join(img_dir, img_name)

        img_adjusted = self.adjust_image(image, adjust)

        if as_link and not img_adjusted:
            os.link(image, img_dst)
        elif img_adjusted:
            img_adjusted.save(img_dst)
        else:
            shutil.copyfile(image, img_dst)
        self._npages += 1
        self._image_info = []

    def add_images(self, images, adjust=None, as_link=False):
        """Add a list of images into the container."""
        for order, image in enumerate(images):
            self.add_image(image, order, adjust, as_link)

    def set_cover(self, image, adjust=None, as_link=False):
        """Add an image as image cover."""
        cover_path = self.get_cover_path()

        img_adjusted = self.adjust_image(image, adjust)

        if as_link and not img_adjusted:
            os.link(image, cover_path)
        elif img_adjusted:
            if img_adjusted.mode != 'RGB':
                img_adjusted = img_adjusted.convert('RGB')
            img_adjusted.save(cover_path)
        else:
            shutil.copyfile(image, cover_path)
        self.has_cover = True

    def npages(self):
        """Return the total number of pages / images."""
        if not self._npages:
            images_path = os.path.join(self.path, 'html', 'images')
            files = [f for f in os.listdir(images_path)
                     if f.endswith(('jpg', 'png'))]
            self._npages = len(files)
        return self._npages

    def get_image_info(self):
        """Get the list of (image_path, (size_x, size_y), image_size)."""
        if not self._image_info:
            html_path = os.path.join(self.path, 'html')
            images_path = os.path.join(self.path, 'html', 'images')
            files = [os.path.join('images', f)
                     for f in os.listdir(images_path)
                     if f.endswith(('jpg', 'png'))]
            for file_ in sorted(files):
                file_path = os.path.join(html_path, file_)
                self._image_info.append(
                    (file_, Image.open(file_path).size,
                     os.path.getsize(file_path)))
        return self._image_info

    def _get_image_path(self, number, ext, relative=False):
        """Get the path an image."""
        image_path = os.path.join('html', 'images',
                                  '%03d.%s' % (number, ext))
        if not relative:
            image_path = os.path.join(self.path, image_path)
        return image_path

    def get_image_path(self, number, relative=False):
        """Get the path an image."""
        # First try with the JPG extension, if not, is a PNG
        image_path = self._get_image_path(number, 'jpg', relative)
        if not os.path.isfile(image_path):
            image_path = self._get_image_path(number, 'png', relative)
        return image_path

    def get_cover_path(self, relative=False):
        """Get the path of the cover image."""
        # XXX TODO - The cover image can be of a different type
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

    def get_size(self):
        """Get the size of the images in bytes."""
        return sum(i[2] for i in self.get_image_info())

    def adjust_image(self, image, adjust):
        """Adjust an image and return None or an Image instance."""
        if not adjust:
            return None

        img = Image.open(image)
        if adjust == Container.RESIZE:
            # RESIZE adjust the longest size of the image to size of a
            # page. The net result is:
            #
            #   new_width <= WIDTH
            #   new_height <= HEIGHT
            #
            width, height = img.size
            ratio = min((WIDTH/float(width), HEIGHT/float(height)))
            width, height = int(ratio*width+0.5), int(ratio*height+0.5)
            resample = Image.BICUBIC if ratio > 1 else Image.ANTIALIAS
            img = img.resize((width, height), resample)
        elif adjust == Container.RESIZE_CROP:
            # RESIZE_CROP resize first the image as RESIZE, and create
            # a new white image of page size, and paste the image in
            # the new one.  Used to adjust the cover image without
            # losing the aspect ratio.
            size = img.size
            mode = img.mode

            # Resize the current image
            width, height = size
            ratio = min((WIDTH/float(width), HEIGHT/float(height)))
            width, height = int(ratio*width+0.5), int(ratio*height+0.5)
            resample = Image.BICUBIC if ratio > 1 else Image.ANTIALIAS
            resized_img = img.resize((width, height), resample)

            # Create a new white image and paste the resized image
            x, y = (WIDTH - width) / 2, (HEIGHT - height) / 2
            img = Image.new(mode, (WIDTH, HEIGHT), '#ffffff')
            img.paste(resized_img, (x, y))
        elif adjust == Container.ROTATE:
            # ROTATE check first if the image is widther than heigher,
            # and rotate the image in this case.  Used for double page
            # images.
            width, height = img.size
            if float(width) / float(height) > 1.0:
                img = img.transpose(Image.ROTATE_270)
        # elif adjust == Container.SPLIT:
        #     pass

        return img

    def split(self, size, clean=False):
        """Split the container in volumes of same size."""
        current_size = self.get_size()
        nvolumes = 1 + current_size / size
        volume_size = 1 + current_size / nvolumes

        containers = [Container('%s_V%02d' % (self.path, i+1))
                      for i in range(nvolumes)]
        images = self.get_image_info()
        containers_used, begin = 0, 0
        for container in containers:
            end, current_size = begin, 0

            if end >= len(images):
                break

            while current_size <= volume_size and end < len(images):
                end += 1
                current_size = sum(i[2] for i in images[begin:end])

            image_slice = [self.get_image_path(i) for i in range(begin, end)]
            container.create(clean)
            container.add_images(image_slice, as_link=True)
            if self.has_cover:
                container.set_cover(self.get_cover_path(), as_link=True)
            containers_used += 1
            begin = end

        return containers[:containers_used]


class MangaMobi(object):
    def __init__(self, container, info, kindlegen=None):
        self.container = container
        self.info = info
        self.kindlegen = kindlegen if kindlegen else KINDLEGEN

    def create(self):
        """Create the mobi file calling kindlegen."""
        self.content_opf()
        for i in range(self.container.npages()):
            self.page(i)
        self.toc_ncx()
        if not self.container.has_cover:
            cover = self.container.get_image_path(0)
            self.container.set_cover(cover, adjust=Container.RESIZE_CROP)

        name = '%s.mobi' % re.sub(r'[^\w]', '_', self.info.title)
        subprocess.call([self.kindlegen, self.container.get_content_opf_path(),
                         '-dont_append_source',
                         '-o', name])

        full_name = os.path.join(self.container.path, name)
        return full_name

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
            ('primary-writing-mode', self.info.reading_direction),
            ('region-mag', 'false'),
            # XXX TODO - Detect the original resolution
            ('original-resolution', '%dx%d' % (WIDTH, HEIGHT)),
        )
        for name, content in metas:
            ET.SubElement(metadata, 'meta', {
                'name': name,
                'content': content,
            })

        manifest = ET.SubElement(package, 'manifest')
        # Add the TOC item
        ET.SubElement(manifest, 'item', {
            'id': 'ncx',
            'href': 'toc.ncx',
            'media-type': 'application/x-dtbncx+xml',
        })
        # Add the cover image item
        ET.SubElement(manifest, 'item', {
            'id': 'cimage',
            'href': 'cover.jpg',
            'media-type': 'image/jpeg',
            'properties': 'cover-image',
        })

        pages = [(self.container.get_page_path(n, relative=True),
                  'page-%03d' % n, 'application/xhtml+xml')
                 for n in range(self.container.npages())]
        for href, id_, media_type in pages:
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

        img_path, img_size, _ = self.container.get_image_info()[number]
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
            print >>f, '<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" ' \
                       '"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">'
            tree.write(f, encoding='utf-8', xml_declaration=False)
