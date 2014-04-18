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

from urlparse import urljoin

from scrapy.http import Request
from scrapy.selector import Selector

from fansite.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class SubManga(MangaSpider):
    name = 'submanga'
    allowed_domains = ['submanga.com']

    def get_genres_url(self):
        return 'http://submanga.com/series/g'

    def get_catalog_url(self):
        return 'http://submanga.com/series'

    def get_lasts_url(self, sice):
        return 'http://submanga.com'

    def get_manga_url(self, manga, issue):
        return 'http://submanga.com/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        pass

    def parse_catalog(self, response):
        pass

    def _parse_catalog_item(self, response):
        pass

    def parse_lasts(self, since):
        pass

    def _parse_page(self, response):
        pass

    def parse_manga(self, response):
        pass
