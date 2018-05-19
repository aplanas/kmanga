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

import glob
import os
import re
import shutil
import subprocess
import uuid
import xml.etree.cElementTree as ET

from PIL import Image
from PIL import ImageFilter
from PIL import ImageOps

KINDLEGEN = '../bin/kindlegen'
GENERATOR = 'kmanga'
# We need to maintain the rest of the images with the same aspect ratio
WIDTH = 800    # 1200
HEIGHT = 1280  # 1920

# Reading directions
HORIZONTAL_LR = 'horizontal-lr'
HORIZONTAL_RL = 'horizontal-rl'
VERTICAL_LR = 'vertical-lr'
VERTICAL_RL = 'vertical-rl'

CSS = """
html{color:#000;background:#FFF;}body,div,dl,dt,dd,ul,ol,li,h1,h2,h3,h4,h5,h6,pre,code,form,fieldset,legend,input,textarea,p,blockquote,th,td{margin:0;padding:0;}table{border-collapse:collapse;border-spacing:0;}fieldset,img{border:0;}address,caption,cite,code,dfn,em,strong,th,var{font-style:normal;font-weight:normal;}li{list-style:none;}caption,th{text-align:left;}h1,h2,h3,h4,h5,h6{font-size:100%;font-weight:normal;}q:before,q:after{content:'';}abbr,acronym{border:0;font-variant:normal;}sup{vertical-align:text-top;}sub{vertical-align:text-bottom;}input,textarea,select{font-family:inherit;font-size:inherit;font-weight:inherit;}input,textarea,select{*font-size:100%;}legend{color:#000;}

#fs {
  position: relative;
  width: 100%;
  height: 100%;
}

#fs a {
  display: block;
  width: 100%;
  height: 100%;
}

#fs div, img {
  position: absolute;
}

.fs-panel {
  position: absolute;
  display: none;
  overflow: hidden;
  top: 0%;
  left: 0%;
  width: 100%;
  height: 100%;
}

#reg-tr {
  top: 0%;
  left: 50%;
  width: 50%;
  height: 50%;
}

#reg-tr-mt img {
  position: absolute;
  top: 0%;
  right: 0%;
}

#reg-tl {
  top: 0%;
  left: 0%;
  width: 50%;
  height: 50%;
}

#reg-tl-mt img {
  position: absolute;
  top: 0%;
  left: 0%;
}

#reg-br {
  top: 50%;
  left: 50%;
  width: 50%;
  height: 50%;
}

#reg-br-mt img {
  position: absolute;
  bottom: 0%;
  right: 0%;
}

#reg-bl {
  top: 50%;
  left: 0%;
  width: 50%;
  height: 50%;
}

#reg-bl-mt img {
  position: absolute;
  bottom: 0%;
  left: 0%;
}
"""


class Container(object):
    # Values for 'adjust' parameter
    RESIZE = 'resize'
    RESIZE_CROP = 'resize_crop'
    ROTATE = 'rotate'
    # SPLIT = 'split'

    # Bit mask for filter parameter
    FILTER_MARGIN = 0b01
    FILTER_FOOTER = 0b10

    MIN_MARGIN = 0.01
    MAX_MARGIN = 0.2

    def __init__(self, path):
        self.path = path
        self.has_cover = False
        # Store information about images.  This information can be
        # recreated from the container.
        # (img_path, (size_x, size_y), img_size, adjust)
        self._image_info = []
        self._npages = 0

    def create(self, clean=False):
        """Create an empty container."""
        if os.path.exists(self.path):
            if clean:
                self.clean()
            else:
                raise ValueError('Container %s is not empty' % self.path)
        os.makedirs(self.path)
        os.mkdir(os.path.join(self.path, 'css'))
        os.mkdir(os.path.join(self.path, 'html'))
        os.mkdir(os.path.join(self.path, 'images'))

    def clean(self):
        """Remove the container directoy and all the content."""
        shutil.rmtree(self.path)

    def add_image(self, image, adjust=None, _filter=None, as_link=False):
        """Add an image into the container."""
        order = self._npages
        img_dir = os.path.join(self.path, 'images')
        img_name = '%03d%s' % (order, os.path.splitext(image)[1])
        img_dst = os.path.join(img_dir, img_name)

        img, adjusted = self.adjust_image(image, adjust)

        # Add the last part of the name, that describe the kind of
        # transformation
        if adjusted:
            img_dst, img_dst_ext = os.path.splitext(img_dst)
            img_dst = '%s_%s%s' % (img_dst, adjust, img_dst_ext)

        # Remove the margin and/or the footer.  First we check for the
        # footer filter, and we apply the margin filter to the result.
        #
        # XXX TODO - If one of the filter is called, we consider the
        # image adjusted (changed), event if the bounding box was
        # exactly the full image (so not change)
        if _filter and _filter & Container.FILTER_FOOTER:
            img = self.filter_footer(img)
            adjusted = True
        if _filter and _filter & Container.FILTER_MARGIN:
            img = self.filter_margin(img)
            adjusted = True

        if as_link and not adjusted:
            os.link(image, img_dst)
        elif adjusted:
            img.save(img_dst)
        else:
            shutil.copyfile(image, img_dst)
        self._npages += 1
        self._image_info = []

    def add_images(self, images, adjust=None, _filter=None, as_link=False):
        """Add a list of images into the container."""
        for image in images:
            self.add_image(image, adjust=adjust, _filter=_filter,
                           as_link=as_link)

    def set_image_adjust(self, number, adjust):
        """Set the adjustment postfix in a image."""
        if adjust:
            images = self.get_image_info()
            current_adjust = images[number][-1]
            if current_adjust:
                msg = 'Image %s already contains an adjustment'
                raise ValueError(msg % number)

            # `get_image_info` provides relative path, to get the
            # absolute path we can call `get_image_path` or build the
            # full path using the container path
            img_path = images[number][0]
            img_path = os.path.join(self.path, img_path)
            img_dst, img_dst_ext = os.path.splitext(img_path)
            img_dst = '%s_%s%s' % (img_dst, adjust, img_dst_ext)
            # Rename the file to attach the new adjustment mark
            os.rename(img_path, img_dst)

            # We just change the adjustment, disable the cache
            self._image_info = []

    def set_cover(self, image, adjust=None, as_link=False):
        """Add an image as image cover."""
        cover_path = self.get_cover_path()

        img, adjusted = self.adjust_image(image, adjust)
        if not adjusted and image.endswith('.png'):
            # If the image is a PNG, we read it to store it in JPG
            # format in the next section.
            img = Image.open(image)
            adjusted = True

        if as_link and not adjusted:
            os.link(image, cover_path)
        elif adjusted:
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(cover_path)
        else:
            shutil.copyfile(image, cover_path)
        self.has_cover = True

    def npages(self):
        """Return the total number of pages / images."""
        if not self._npages:
            img_path = os.path.join(self.path, 'images')
            files = [f for f in os.listdir(img_path)
                     if f.endswith(('jpg', 'png'))]
            self._npages = len(files)
        return self._npages

    def _get_adjust(self, img_path):
        """Return the kind of transformation done in a image."""
        adjusts = (Container.RESIZE, Container.RESIZE_CROP, Container.ROTATE)
        for adjust in adjusts:
            if adjust in img_path:
                return adjust

    def get_image_info(self):
        """Get the list of (img_path, (size_x, size_y), img_size, adjust)."""
        if not self._image_info:
            img_path = os.path.join(self.path, 'images')
            files = [os.path.join('images', f)
                     for f in os.listdir(img_path)
                     if f.endswith(('jpg', 'png'))]
            for file_ in sorted(files):
                file_path = os.path.join(self.path, file_)
                adjust = self._get_adjust(file_)
                self._image_info.append(
                    (file_, Image.open(file_path).size,
                     os.path.getsize(file_path), adjust))
        return self._image_info

    def get_image_path(self, number, relative=False):
        """Get the path of an image."""
        if number > self.npages():
            raise ValueError('Page number not found')
        # With glob we need to use the absolute path
        img_glob = os.path.join(self.path, 'images', '%03d*' % number)
        imgs_path = glob.glob(img_glob)
        if not imgs_path:
            raise ValueError('Page number not found in JPG or PNG format')
        if len(imgs_path) > 1:
            raise ValueError('Multiple page found for the same page number')
        img_path = imgs_path[0]
        if relative:
            # Remove the path and the first '/'
            img_path = img_path[len(self.path)+1:]
        return img_path

    def get_image_mime_type(self, number):
        """Get image MIME type."""
        image_path = self.get_image_path(number)
        _, ext = os.path.splitext(image_path.lower())
        mime_type = {
            '.jpg': 'image/jpeg',
            '.png': 'image/png',
        }
        return mime_type[ext]

    def _get_path(self, file_path, relative):
        if not relative:
            file_path = os.path.join(self.path, file_path)
        return file_path

    def get_cover_path(self, relative=False):
        """Get the path of the cover image."""
        return self._get_path('cover.jpg', relative)

    def get_content_opf_path(self, relative=False):
        """Get the path for content.opf."""
        return self._get_path('content.opf', relative)

    def get_page_path(self, number, relative=False):
        """Get the path for page-XXX.html."""
        return self._get_path(
            os.path.join('html', 'page-%03d.html' % number), relative)

    def get_toc_ncx_path(self, relative=False):
        """Get the path for the toc.ncx."""
        return self._get_path('toc.ncx', relative)

    def get_nav_path(self, relative=False):
        """Get the path for the nav.xhtml."""
        return self._get_path('nav.xhtml', relative)

    def get_style_css_path(self, relative=False):
        """Get the path of the CSS file."""
        return self._get_path(os.path.join('css', 'style.css'), relative)

    def get_size(self):
        """Get the size of the images in bytes."""
        return sum(i[2] for i in self.get_image_info())

    def adjust_image(self, image, adjust):
        """Adjust an image and return None or an Image instance."""
        adjusted = False

        img = Image.open(image)
        if adjust == Container.RESIZE:
            # RESIZE adjust the longest size of the image to size of a
            # page. The net result is:
            #
            #   new_width <= WIDTH
            #   new_height <= HEIGHT
            #
            width, height = img.size
            ratio = min(WIDTH/width, HEIGHT/height)
            width, height = int(ratio*width+0.5), int(ratio*height+0.5)
            resample = Image.BICUBIC if ratio > 1 else Image.ANTIALIAS
            img = img.resize((width, height), resample)
            adjusted = True
        elif adjust == Container.RESIZE_CROP:
            # RESIZE_CROP resize first the image as RESIZE, and create
            # a new white image of page size, and paste the image in
            # the new one.  Used to adjust the cover image without
            # losing the aspect ratio.
            size = img.size
            mode = img.mode

            # Resize the current image
            width, height = size
            ratio = min(WIDTH/width, HEIGHT/height)
            width, height = int(ratio*width+0.5), int(ratio*height+0.5)
            resample = Image.BICUBIC if ratio > 1 else Image.ANTIALIAS
            resized_img = img.resize((width, height), resample)

            # Create a new white image and paste the resized image
            x, y = (WIDTH - width) // 2, (HEIGHT - height) // 2
            img = Image.new(mode, (WIDTH, HEIGHT), '#ffffff')
            img.paste(resized_img, (x, y))
            adjusted = True
        elif adjust == Container.ROTATE:
            # ROTATE check first if the image is widther than heigher,
            # and rotate the image in this case.  Used for double page
            # images.
            width, height = img.size
            if width / height > 1.0:
                img = img.transpose(Image.ROTATE_270)
                adjusted = True
        # elif adjust == Container.SPLIT:
        #     pass
        elif adjust:
            raise ValueError('Value for adjust not found')

        return img, adjusted

    def bbox(self, img):
        """Return the bounding box of an image inside some ranges."""
        margin = Container.MIN_MARGIN / 2
        min_margin = [int(margin*i+0.5) for i in img.size]

        margin = Container.MAX_MARGIN / 2
        max_margin = [int(margin*i+0.5) for i in img.size]

        bbox = img.getbbox()
        bbox = (
            max(0, min(max_margin[0], bbox[0]-min_margin[0])),
            max(0, min(max_margin[1], bbox[1]-min_margin[1])),
            min(img.size[0],
                max(img.size[0]-max_margin[0], bbox[2]+min_margin[0])),
            min(img.size[1],
                max(img.size[1]-max_margin[1], bbox[3]+min_margin[1])),
        )
        return bbox

    def filter_footer(self, img):
        """Filter to remove the hight quality footer for an image."""
        # Some sites like MangaFox add an extra footer in the original
        # image.  This footer remove importan space in the Kindle, and
        # we need to remove it.
        #
        # The algorithm use as a leverage the normal noise present in
        # an scanned image, that is higher than the one in the footer.
        # This means that this filter will only work in medium quality
        # scanners, but possibly not in high quality ones.
        #
        # The process is like this:
        #
        #   1.- Binarize the image, moving the noise at the same level
        #       that the real information.
        #
        #   2.- Use a MinFilter of size 3 to a big mass of pixels that
        #       containg high frequency data.  That usually means
        #       pixels surrounded with blanks.
        #
        #   3.- Do a Gaussian filter to lower more the high frequency
        #       data, moving the mass close arround the pixel.  This
        #       will lower more the pixels surrounded with gaps.
        #
        #   4.- Discard the pixels with low mass.
        #
        _img = ImageOps.invert(img.convert(mode='L'))
        _img = _img.point(lambda x: x and 255)
        _img = _img.filter(ImageFilter.MinFilter(size=3))
        _img = _img.filter(ImageFilter.GaussianBlur(radius=5))
        _img = _img.point(lambda x: (x >= 48) and x)
        # If the image is white, we do not have bbox
        return img.crop(_img.getbbox()) if _img.getbbox() else img

    def filter_margin(self, img):
        """Filter to remove empty margins in an image."""
        # This filter is based on a simple Gaussian with a threshold
        _img = ImageOps.invert(img.convert(mode='L'))
        _img = _img.filter(ImageFilter.GaussianBlur(radius=3))
        _img = _img.point(lambda x: (x >= 16) and x)
        # If the image is white, we do not have bbox
        return img.crop(self.bbox(_img)) if _img.getbbox() else img

    def split(self, size, clean=False):
        """Split the container in volumes of same size."""
        current_size = self.get_size()
        nvolumes = 1 + current_size // size
        volume_size = 1 + current_size // nvolumes

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
            # Transmit the adjustment from the original container
            for i in range(begin, end):
                adjust = images[i][-1]
                container.set_image_adjust(i - begin, adjust)
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
        self.style_css()
        self.content_opf()
        for i in range(self.container.npages()):
            self.page(i)
        self.toc_ncx()
        self.nav()
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
        """Generate the content OPF."""
        package = ET.Element('package', {
            'xmlns': 'http://www.idpf.org/2007/opf',
            'version': '3.0',
            'unique-identifier': 'dtb:uid',
        })

        metadata = ET.SubElement(package, 'metadata', {
            'xmlns:dc': 'http://purl.org/dc/elements/1.1/',
            'xmlns:opf': 'http://www.idpf.org/2007/opf',
        })

        # Kindle specific metadata
        metas = (
            ('fixed-layout', 'true'),
            ('orientation-lock', 'none'),
            # XXX TODO - Detect the original resolution
            ('original-resolution', '%dx%d' % (WIDTH, HEIGHT)),
            # This is decided by KindleGen
            # ('RegionMagnification', 'true'),
            ('book-type', 'comic'),
            ('primary-writing-mode', self.info.reading_direction),
            ('zero-gutter', 'true'),
            ('zero-margin', 'true'),
            ('generator', GENERATOR),
            ('cover', 'cover-image'),
        )
        for name, content in metas:
            ET.SubElement(metadata, 'meta', {
                'name': name,
                'content': content,
            })

        # EPUB3 metadata
        ET.SubElement(metadata, 'meta', {
            'property': 'rendition:layout'
        }).text = 'pre-paginated'
        ET.SubElement(metadata, 'meta', {
            'property': 'rendition:orientation'
        }).text = 'auto'

        # eBook content metadata
        ET.SubElement(metadata, 'dc:title').text = self.info.title
        ET.SubElement(metadata, 'dc:creator', {
            'opf:role': 'aut',
            'opf:file-as': self.info.author,
        }).text = self.info.author
        ET.SubElement(metadata, 'dc:creator', {
            'opf:role': 'ill',
        }).text = self.info.author
        ET.SubElement(metadata, 'dc:publisher').text = self.info.publisher
        ET.SubElement(metadata, 'dc:rights').text = 'Original Authors'
        ET.SubElement(metadata, 'dc:language').text = self.info.language

        # XXX TODO - We do not add a timestamp in the document
        # ET.SubElement(metadata, 'dc:date', {
        #     'opf:event': 'creation',
        # }).text = '2015-12-31'
        # ET.SubElement(metadata, 'dc:date', {
        #     'opf:event': 'publication',
        # }).text = '2015'
        # ET.SubElement(metadata, 'dc:date', {
        #     'opf:event': 'modification',
        # }).text = '2015-12-31'

        ET.SubElement(metadata, 'dc:identifier', {
            'id': 'BookId',
        }).text = 'Version 1.0'
        ET.SubElement(metadata, 'dc:identifier', {
            'id': 'PrimaryId',
            'opf:scheme': 'ISBN',
        }).text = 'NONE'
        identifier = identifier if identifier else str(uuid.uuid1())
        ET.SubElement(metadata, 'dc:identifier', {
            'id': 'dtb:uid',
        }).text = identifier

        ET.SubElement(metadata, 'dc:type').text = 'preview'
        subject = 'COMICS & GRAPHIC NOVELS / Manga / General'
        ET.SubElement(metadata, 'dc:subject').text = subject

        ET.SubElement(metadata, 'dc:description').text = self.info.title

        manifest = ET.SubElement(package, 'manifest')
        # Add the NCX item
        ET.SubElement(manifest, 'item', {
            'id': 'ncx',
            'href': self.container.get_toc_ncx_path(relative=True),
            'media-type': 'application/x-dtbncx+xml',
        })
        # Add the CSS style item
        ET.SubElement(manifest, 'item', {
            'id': 'layout-styles',
            'href': self.container.get_style_css_path(relative=True),
            'media-type': 'text/css',
        })
        # Add HTML page items
        pages = [(self.container.get_page_path(n, relative=True),
                  'page-%03d' % n, 'application/xhtml+xml')
                 for n in range(self.container.npages())]
        for href, id_, media_type in pages:
            ET.SubElement(manifest, 'item', {
                'id': id_,
                'href': href,
                'media-type': media_type,
            })
        # Add the cover image item
        ET.SubElement(manifest, 'item', {
            'id': 'cover-image',
            'href': self.container.get_cover_path(relative=True),
            'media-type': 'image/jpeg',
            'properties': 'cover-image',
        })
        # Add image items
        images = [(self.container.get_image_path(n, relative=True),
                   'image-%03d' % n, self.container.get_image_mime_type(n))
                  for n in range(self.container.npages())]
        for href, id_, media_type in images:
            ET.SubElement(manifest, 'item', {
                'id': id_,
                'href': href,
                'media-type': media_type,
            })

        # Spine
        spine = ET.SubElement(package, 'spine', {'toc': 'ncx'})
        for idref in range(self.container.npages()):
            ET.SubElement(spine, 'itemref', {
                'idref': 'page-%03d' % idref,
                'linear': 'yes',
            })

        # Guide
        guide = ET.SubElement(package, 'guide')
        ET.SubElement(guide, 'reference', {
            'type': 'text',
            'title': 'Beginning',
            'href': self.container.get_page_path(0, relative=True),
        })

        tree = ET.ElementTree(package)
        with open(self.container.get_content_opf_path(), 'w') as f:
            tree.write(f, encoding='unicode', xml_declaration=True)

    def _use_panel_view(self):
        """Evaluate if PanelView is used."""
        # We want to use PanelView only in the case that there is a
        # rotated image, because in this case we need to control the
        # zoom order for the four regions of a page.
        # image_info = self.container.get_image_info()
        # return any(info[-1] == Container.ROTATE for info in image_info)
        # XXX TODO - Since firmware 5.8.5 Virtual Panels feature seems
        # to be disabled, and the only way to zoom in a area (as far
        # as I tested) is via Panel View.  Meanwhile I research this
        # topic, I need to backup in Panel View.
        return True

    def _img_scaled_size(self, size, scale=1.0):
        width, height = size
        ratio = min(WIDTH/width, HEIGHT/height)
        width, height = int(scale*ratio*width+0.5), int(scale*ratio*height+0.5)
        return width, height

    def _img_style_size(self, size, scale=1.0):
        width, height = self._img_scaled_size(size, scale)
        style = 'width:%dpx;height:%dpx;' % (width, height)
        return style

    def _img_style_margin(self, size):
        width, height = self._img_scaled_size(size)
        mtop, mleft = (HEIGHT - height) // 2, (WIDTH - width) // 2
        mbottom, mright = (HEIGHT - height) - mtop, (WIDTH - width) - mleft
        style = 'margin-top:%dpx;margin-bottom:%dpx;' % (mtop, mbottom)
        style += 'margin-left:%dpx;margin-right:%dpx;' % (mleft, mright)
        return style

    def _get_regions(self, number):
        """Get the region names and order for a page."""
        order = {
            HORIZONTAL_LR: (
                ('tl', 1), ('tr', 2), ('bl', 3), ('br', 4),
            ),
            HORIZONTAL_RL: (
                ('tl', 2), ('tr', 1), ('bl', 4), ('br', 3),
            ),
            VERTICAL_LR: (
                ('tl', 1), ('tr', 3), ('bl', 2), ('br', 4),
            ),
            VERTICAL_RL: (
                ('tl', 3), ('tr', 1), ('bl', 4), ('br', 2),
            ),
            'rotate_%s' % HORIZONTAL_LR: (
                ('tl', 2), ('tr', 1), ('bl', 4), ('br', 3),
            ),
            'rotate_%s' % HORIZONTAL_RL: (
                ('tl', 4), ('tr', 3), ('bl', 2), ('br', 1),
            ),
            'rotate_%s' % VERTICAL_LR: (
                ('tl', 2), ('tr', 1), ('bl', 4), ('br', 3),
            ),
            'rotate_%s' % VERTICAL_RL: (
                ('tl', 4), ('tr', 3), ('bl', 2), ('br', 1),
            ),
        }
        _, _, _, adjust = self.container.get_image_info()[number]
        rd = self.info.reading_direction
        if not adjust:
            return order[rd]
        elif adjust == Container.ROTATE:
            return order['rotate_%s' % rd]
        else:
            raise ValueError('Adjust type is not ROTATE: %s' % adjust)

    def page(self, number):
        """Generate the content of a page."""
        use_panel_view = self._use_panel_view()

        html = ET.Element('html')

        head = ET.SubElement(html, 'head')
        ET.SubElement(head, 'meta', {
            'name': 'generator',
            'content': GENERATOR,
        })
        ET.SubElement(head, 'title').text = str(number)
        ET.SubElement(head, 'link', {
            'href': '../%s' % self.container.get_style_css_path(relative=True),
            'rel': 'stylesheet',
            'type': 'text/css',
        })

        img_path, img_size, _, adjust = self.container.get_image_info()[number]
        body = ET.SubElement(html, 'body')
        if use_panel_view:
            div_fs = ET.SubElement(body, 'div', {
                'id': 'fs'
            })
            div = ET.SubElement(div_fs, 'div')
        else:
            div = ET.SubElement(body, 'div')

        size = self._img_style_size(img_size)
        margin = self._img_style_margin(img_size)
        ET.SubElement(div, 'img', {
            'src': '../%s' % img_path,
            'style': size + margin,
        })

        if use_panel_view:
            regions = self._get_regions(number)
            for region in regions:
                label, order = region
                div_reg = ET.SubElement(div_fs, 'div', {
                    'id': 'reg-%s' % label
                })
                json_data = '{"targetId": "%s", "ordinal": %d}' % (
                    'reg-%s-mt' % label,
                    order,
                )
                ET.SubElement(div_reg, 'a', {
                    'class': 'app-amzn-magnify',
                    'data-app-amzn-magnify': json_data,
                })
                div_mt = ET.SubElement(div_fs, 'div', {
                    'id': 'reg-%s-mt' % label,
                    'class': 'fs-panel',
                })
                ET.SubElement(div_mt, 'img', {
                    'src': '../%s' % img_path,
                    'style': self._img_style_size(img_size, scale=1.8),
                })

        tree = ET.ElementTree(html)
        with open(self.container.get_page_path(number), 'w') as f:
            print('<!DOCTYPE html>', file=f)
            tree.write(f, encoding='unicode', xml_declaration=False)

    def toc_ncx(self):
        """Generate the logical table of content."""
        ncx = ET.Element('ncx', {
            'version': '2005-1',
            'xml:lang': 'en',
            'xmlns': 'http://www.daisy.org/z3986/2005/ncx/',
        })

        head = ET.SubElement(ncx, 'head')
        metas = (
            ('dtb:uid', self.info.title),
            ('dtb:depth', '1'),
            ('dtb:totalPageCount', '0'),
            ('dtb:maxPageNumber', '0'),
            # ('generated', 'true'),
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
            print('<?xml version="1.0" encoding="UTF-8"?>', file=f)
            print('<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" '
                  '"http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">', file=f)
            tree.write(f, encoding='unicode', xml_declaration=False)

    def nav(self):
        """Generate the navigation file."""
        html = ET.Element('html', {
            'xmlns': 'http://www.w3.org/1999/xhtml',
            'xml:lang': 'en',
            'lang': 'en',
            'xmlns:epub': 'http://www.idpf.org/2007/ops',
        })

        head = ET.SubElement(html, 'head')
        ET.SubElement(head, 'title').text = self.info.title
        ET.SubElement(head, 'meta', {
            'http-equiv': 'Content-Type',
            'content': 'text/html; charset=utf-8',
        })

        body = ET.SubElement(html, 'body')
        landmarks = ET.SubElement(body, 'nav', {
            'epub:type': 'landmarks'
        })
        ol = ET.SubElement(landmarks, 'ol')
        ET.SubElement(ET.SubElement(ol, 'li'), 'a', {
            'epub:type': 'bodymatter',
            'href': self.container.get_page_path(0, relative=True),
        }).text = 'Beginning'

        toc = ET.SubElement(body, 'nav', {
            'epub:type': 'toc'
        })
        ol = ET.SubElement(toc, 'ol')

        for n in range(self.container.npages()):
            ET.SubElement(ET.SubElement(ol, 'li'), 'a', {
                'href': self.container.get_page_path(n, relative=True)
            }).text = 'Page-%03d' % n

        tree = ET.ElementTree(html)
        with open(self.container.get_nav_path(), 'w') as f:
            print('<?xml version="1.0" encoding="UTF-8"?>', file=f)
            tree.write(f, encoding='unicode', xml_declaration=False)

    def style_css(self):
        """Generate the CSS."""
        with open(self.container.get_style_css_path(), 'w') as f:
            print(CSS, file=f)
