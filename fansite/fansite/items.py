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

from scrapy.item import Item, Field


class Genres(Item):
    names = Field()


class Manga(Item):
    name = Field()
    alt_name = Field()
    slug = Field()
    release = Field()
    author = Field()
    artist = Field()
    reading_direction = Field()
    status = Field()
    genres = Field()
    rank = Field()
    description = Field()
    image_urls = Field()
    images = Field()
    issues = Field()
    url = Field()


class Issue(Item):
    name = Field()
    number = Field()
    added = Field()
    url = Field()


class IssuePage(Item):
    manga = Field()
    issue = Field()
    number = Field()
    image_urls = Field()
    images = Field()
