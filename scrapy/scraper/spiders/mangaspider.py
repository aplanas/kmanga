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

from datetime import date

import scrapy


class MangaSpider(scrapy.Spider):

    def __init__(self, *args, **kwargs):
        super(MangaSpider, self).__init__(*args, **kwargs)

        #
        # Parameters for MangaSpider childrens:
        #
        # - genres: (OPTIONAL) If True, indicate that the spider needs
        #           to download the catalog of genres.  The spider
        #           knows where is this URL, but the `url` parameter
        #           can be used.
        # - catalog: (OPTIONAL) If True, indicate that the spider
        #            needs to download the catalog of mangas.  The
        #            spider also knows where is this URL, but the
        #            `url` parameter can be used.
        # - collection: (OPTIONAL) If True, the spider will download
        #               the list of issues for one manga. Parameter
        #               `manga` is used to set the name of the manga.
        #               The spider can set the URL, but `url`
        #               parameter can be used.
        # - lasts: (OPTIONAL) If the value is a date, the spider will
        #          download a catalog update until this date.
        # - manga: (OPTIONAL) Name of the manga pointed by `url`.
        # - issue: (OPTIONAL) Issue number of the manga pointed by `url`.
        # - url: (OPTIONAL) Initial URL for the spider.
        # - from: (OPTIONAL) Email address set in the FROM field.
        # - to: (OPTIONAL) Email address set in the TO field.
        #

        error_msg = False

        _url = 'url' in kwargs
        if 'genres' in kwargs:
            self.start_urls = [self.url] if _url else [self.get_genres_url()]
        elif 'catalog' in kwargs:
            self.start_urls = [self.url] if _url else [self.get_catalog_url()]
        elif 'collection' in kwargs and 'manga' in kwargs:
            self.start_urls = [self.url] if _url \
                else [self.get_collection_url()]
        elif 'lasts' in kwargs:
            day, month, year = [int(x) for x in self.lasts.split('-')]
            self.until = date(year=year, month=month, day=day)
            self.start_urls = [self.url] if _url \
                else [self.get_lasts_url(self.until)]
        elif 'manga' in kwargs and 'issue' in kwargs:
            self.start_urls = [self.url] if _url \
                else [self.get_manga_url(self.manga, self.issue)]
            self.from_email = kwargs.get('from', None)
            try:
                self.to_email = kwargs['to']
            except:
                error_msg = True
        else:
            error_msg = True

        _help = 'h' in kwargs or 'help' in kwargs
        if error_msg and _help:
            msg = ' '.join(('[-a genres=1 -a url=URL]',
                            '[-a catalog=1 -a url=URL]',
                            '[-a collection=1 -a manga=name -a url=URL]',
                            '[-a lasts=DD-MM-YYYY -a url=URL]',
                            '[-a manga=name -a issue=number -a url=URL'
                            ' -a from=email -a to=email]'))
            print 'scrapy crawl %s SPIDER' % msg
            exit(1)

    def set_crawler(self, crawler):
        """Intercept the method to configure update the settings."""
        # Store the parameters as a settings configuration, so
        # pipelines can read the parameters too.
        super(MangaSpider, self).set_crawler(crawler)
        if hasattr(self, 'from_email'):
            self.settings.overrides['MAIL_FROM'] = self.from_email
        if hasattr(self, 'to_email'):
            self.settings.overrides['MAIL_TO'] = self.to_email

    def parse(self, response):
        if hasattr(self, 'genres'):
            return self.parse_genres(response)

        if hasattr(self, 'catalog'):
            return self.parse_catalog(response)

        if all(hasattr(self, attr) for attr in ('collection', 'manga')):
            return self.parse_collection(response, self.manga)

        if hasattr(self, 'lasts'):
            return self.parse_lasts(response, self.since)

        if all(hasattr(self, attr) for attr in ('manga', 'issue', 'url')):
            return self.parse_manga(response, self.manga, self.issue)

    def get_genres_url(self):
        raise NotImplementedError

    def get_catalog_url(self):
        raise NotImplementedError

    def get_collection_url(self):
        raise NotImplementedError

    def get_lasts_url(self, until):
        raise NotImplementedError

    def get_manga_url(self, manga, issue):
        raise NotImplementedError

    def parse_genres(self, response):
        raise NotImplementedError

    def parse_catalog(self, response):
        raise NotImplementedError

    def parse_collection(self, response, manga):
        raise NotImplementedError

    def parse_lasts(self, response, until):
        raise NotImplementedError

    def parse_manga(self, response, manga, issue):
        raise NotImplementedError
