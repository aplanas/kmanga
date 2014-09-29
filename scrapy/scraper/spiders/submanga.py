# -*- coding: utf-8 -*-
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

import scrapy

from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class SubManga(MangaSpider):
    name = 'submanga'
    allowed_domains = ['submanga.com']

    def get_genres_url(self):
        return 'http://submanga.com/series/g'

    def get_catalog_url(self):
        return 'http://submanga.com/series'

    def get_collection_url(self, manga):
        return 'http://submanga.com/%s' % manga

    def get_lastest_url(self, until):
        return 'http://submanga.com'

    def get_manga_url(self, manga, issue):
        return 'http://submanga.com/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        pass

    def parse_catalog(self, response):
        pass

    def parse_collection(self, response, manga):
        pass

    def parse_lastest(self, response, until):
        pass

    def parse_manga(self, response, manga, issue):
        pass
