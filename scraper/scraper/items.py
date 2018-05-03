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

# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

import scrapy


class Genres(scrapy.Item):
    names = scrapy.Field()


class Manga(scrapy.Item):
    name = scrapy.Field()
    alt_name = scrapy.Field()
    author = scrapy.Field()
    artist = scrapy.Field()
    reading_direction = scrapy.Field()
    status = scrapy.Field()
    genres = scrapy.Field()
    rank = scrapy.Field()
    rank_order = scrapy.Field()
    description = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
    issues = scrapy.Field()
    url = scrapy.Field()


class Issue(scrapy.Item):
    name = scrapy.Field()
    number = scrapy.Field()
    order = scrapy.Field()
    language = scrapy.Field()
    release = scrapy.Field()
    url = scrapy.Field()


class IssuePage(scrapy.Item):
    manga = scrapy.Field()
    issue = scrapy.Field()
    number = scrapy.Field()
    image_urls = scrapy.Field()
    images = scrapy.Field()
