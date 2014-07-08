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

from datetime import date

import scrapy


class MangaSpider(scrapy.Spider):

    def __init__(self, *args, **kwargs):
        super(MangaSpider, self).__init__(*args, **kwargs)

        error_msg = False

        if 'genres' in kwargs:
            self.start_urls = [self.get_genres_url()]
        elif 'catalog' in kwargs:
            self.start_urls = [self.get_catalog_url()]
        elif 'lasts' in kwargs:
            day, month, year = [int(x) for x in self.lasts.split('-')]
            since = date(year=year, month=month, day=day)
            self.start_urls = [self.get_lasts_url(since)]
        elif 'manga' in kwargs and 'issue' in kwargs:
            self.start_urls = [self.get_manga_url(self.manga, self.issue)]
        else:
            error_msg = True

        self.from_email = kwargs.get('from', None)
        try:
            self.to_email = kwargs['to']
        except:
            error_msg = True

        if error_msg:
            msg = ' '.join(('[-a genres=1]',
                            '[-a catalog=1]',
                            '[-a manga=name -a issue=number]',
                            '[-a lasts=DD-MM-YYYY]',
                            '[-a from=email]',
                            '-a to=email'))
            print 'scrapy crawl SPIDER', msg
            exit(1)

    def set_crawler(self, crawler):
        """Intercept the method to configure update the settings."""
        # Store the parameters as a settings configuration, so
        # pipelines can read the parameters too.
        super(MangaSpider, self).set_crawler(crawler)
        if self.from_email:
            self.settings.overrides['MAIL_FROM'] = self.from_email
        self.settings.overrides['MAIL_TO'] = self.to_email

    def parse(self, response):
        if hasattr(self, 'genres'):
            return self.parse_genres(response)

        if hasattr(self, 'catalog'):
            return self.parse_catalog(response)

        if hasattr(self, 'lasts'):
            day, month, year = [int(x) for x in self.lasts.split('-')]
            since = date(year=year, month=month, day=day)
            return self.parse_lasts(response, since)

        if hasattr(self, 'manga') and hasattr(self, 'issue'):
            return self.parse_manga(response, self.manga, self.issue)

    def get_genres_url(self):
        raise NotImplementedError

    def get_catalog_url(self):
        raise NotImplementedError

    def get_lasts_url(self, since):
        raise NotImplementedError

    def get_manga_url(self, manga, issue):
        raise NotImplementedError

    def parse_genres(self, response):
        raise NotImplementedError

    def parse_catalog(self, response):
        raise NotImplementedError

    def parse_lasts(self, response, since):
        raise NotImplementedError

    def parse_manga(self, response, manga, issue):
        raise NotImplementedError
