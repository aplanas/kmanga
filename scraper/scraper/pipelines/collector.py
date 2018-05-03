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

import logging

from mobi.cache import IssueCache

logger = logging.getLogger(__name__)


class CollectorPipeline(object):
    def __init__(self, issues_store, images_store):
        self.issues_store = issues_store
        self.images_store = images_store
        self.items = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings['ISSUES_STORE'], settings['IMAGES_STORE'])

    def process_item(self, item, spider):
        # Bypass the pipeline if called with dry-run parameter.
        if hasattr(spider, 'dry_run'):
            return item

        # Recover the `stats` from the crawler
        self.stats = spider.crawler.stats

        if spider._operation == 'manga':
            key = spider.url
            if key not in self.items:
                self.items[key] = []
            self.items[key].append(item)
        return item

    def close_spider(self, spider):
        # If there is a 503 error, the parse() method of mangaspider
        # is never called and the attribute is not set.  This can be
        # used as an indication of error in the download.
        if hasattr(spider, '_operation'):
            if spider._operation == 'manga':
                return self.collect(spider)

    def collect(self, spider):
        # Signalize as an error the missing self.items, probably there
        # is a hidden bug in the spider.
        if not self.items:
            logger.error('Items are empty, please check [%s]' % spider)
            return

        cache = IssueCache(self.issues_store, self.images_store)
        for url, images in self.items.items():
            cache[url] = images
