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

from datetime import date
import logging
import sys

import scrapy

logger = logging.getLogger(__name__)


class MangaSpider(scrapy.Spider):

    LOGIN_OK = 'login_ok'
    LOGIN_ERR = 'login_err'

    def __init__(self, *args, **kwargs):
        super(MangaSpider, self).__init__(*args, **kwargs)

        #
        # Parameters for MangaSpider childrens:
        #
        # - username:   (OPTIONAL) Username for login form.
        #
        # - password:   (OPTIONAL) Password for login form.
        #
        # - genres:     (OPTIONAL) If True, indicate that the spider
        #               needs to download the catalog of genres.  The
        #               spider knows where is this URL, but the `url`
        #               parameter can be used.
        #
        # - catalog:    (OPTIONAL) If True, indicate that the spider
        #               needs to download the catalog of mangas.  The
        #               spider also knows where is this URL, but the
        #               `url` parameter can be used.
        #
        # - collection: (OPTIONAL) If True, the spider will download
        #               the list of issues for one manga. Parameter
        #               `manga` is used to set the name of the manga.
        #               The spider can set the URL, but `url`
        #               parameter can be used.
        #
        # - latest:     (OPTIONAL) If the value is a date, the spider
        #               will download a catalog update until this
        #               date.
        #
        # - manga:      (OPTIONAL) Name of the manga pointed by `url`.
        #
        # - issue:      (OPTIONAL) Issue number of the manga pointed
        #               by `url`.
        #
        # - url:        (OPTIONAL) Initial URL for the spider.
        #
        # - dry_run:    (OPTIONAL) If True, the pipelines will ignore
        #               the items that comes from this spider.
        #

        error_msg = False

        _manga = 'manga' in kwargs and kwargs['manga']
        _issue = 'issue' in kwargs and (kwargs['issue'] is not None)
        _url = 'url' in kwargs and kwargs['url']
        if 'genres' in kwargs:
            self.start_urls = [self.url] if _url else [self.get_genres_url()]
            self._operation = 'genres'
        elif 'catalog' in kwargs:
            self.start_urls = [self.url] if _url else [self.get_catalog_url()]
            self._operation = 'catalog'
        elif 'collection' in kwargs and _manga:
            self.start_urls = [self.url] if _url \
                else [self.get_collection_url(self.manga)]
            self._operation = 'collection'
        elif 'latest' in kwargs:
            day, month, year = [int(x) for x in self.latest.split('-')]
            self.until = date(year=year, month=month, day=day)
            self.start_urls = [self.url] if _url \
                else [self.get_latest_url(self.until)]
            self._operation = 'latest'
        elif _manga and _issue:
            self.start_urls = [self.url] if _url \
                else [self.get_manga_url(self.manga, self.issue)]
            self._operation = 'manga'
        else:
            # To allow the check of the spider using scrapy, we need
            # to commend this line.
            # error_msg = True
            error_msg = False

        # Store user and password for login form
        self.username = 'username' in kwargs and kwargs['username']
        self.password = 'password' in kwargs and kwargs['password']

        # If this spider have login_url, this will become the first
        # URL, and `start_urls` will be `next_urls`.
        self._login = False
        try:
            login_url = self.get_login_url()
            if login_url:
                self.next_urls = self.start_urls
                self.start_urls = [login_url]
                self._login = True
        except NotImplementedError:
            pass

        _help = 'h' in kwargs or 'help' in kwargs
        if error_msg or _help:
            msg = ' '.join(('[-a user=USER -a password=PASSWD'
                            ' -a genres=1 -a url=URL]',
                            '[-a user=USER -a password=PASSWD'
                            ' -a catalog=1 -a url=URL]',
                            '[-a user=USER -a password=PASSWD'
                            ' -a collection=1 -a manga=name -a url=URL]',
                            '[-a user=USER -a password=PASSWD'
                            ' -a latest=DD-MM-YYYY -a url=URL]',
                            '[-a user=USER -a password=PASSWD'
                            ' -a manga=name -a issue=number -a url=URL]',
                            '[-a dry_run=1]'))
            print('scrapy crawl %s SPIDER' % msg)
            sys.exit(1)

    def parse(self, response):
        if self._login:
            return self.parse_login(response)

        if self._operation == 'genres':
            return self.parse_genres(response)

        if self._operation == 'catalog':
            return self.parse_catalog(response)

        if self._operation == 'collection':
            return self.parse_collection(response, self.manga)

        if self._operation == 'latest':
            return self.parse_latest(response, self.until)

        if self._operation == 'manga':
            return self.parse_manga(response, self.manga, self.issue)

    def get_login_url(self):
        raise NotImplementedError

    def get_genres_url(self):
        raise NotImplementedError

    def get_catalog_url(self):
        raise NotImplementedError

    def get_collection_url(self, manga):
        raise NotImplementedError

    def get_latest_url(self, until):
        raise NotImplementedError

    def get_manga_url(self, manga, issue):
        raise NotImplementedError

    def _check_login_params(self):
        required = {
            'username_field': 'Provide an username_field in the spider '
                              'declaration.',
            'password_field': 'Provide a password_field in the spider '
                              'declaration.',
            'username': 'Provide an username as a spider parameter.',
            'password': 'Provide a password as a spider parameter.',
            'login_check': 'Provide a login_check dict as a spider parameter.',
        }
        optionals = {
            # If the user specify `form_xpath`, we will try to find
            # the form, but if `form_url` is specified, this will
            # considered the `action` URL for the POST
            ('form_xpath', 'form_url'): 'Provide a form_xpath or form_url '
                                        'in the spider declaration.',
        }
        for attr, msg in required.items():
            if not hasattr(self, attr) or not getattr(self, attr):
                raise AttributeError(msg)
        for attrs, msg in optionals.items():
            if not any((hasattr(self, attr) and getattr(self, attr))
                       for attr in attrs):
                raise AttributeError(msg)

    def parse_login(self, response):
        self._check_login_params()
        self._login = False
        form_data = {
            self.username_field: self.username,
            self.password_field: self.password
        }
        if hasattr(self, 'form_xpath'):
            return scrapy.FormRequest.from_response(
                response,
                formxpath=self.form_xpath,
                formdata=form_data,
                callback=self.parse_after_login
            )
        elif hasattr(self, 'form_url'):
            return scrapy.FormRequest(
                self.form_url,
                formdata=form_data,
                callback=self.parse_after_login
            )

    def parse_after_login(self, response):
        login_ok = self.login_check.get(MangaSpider.LOGIN_OK, None)
        login_err = self.login_check.get(MangaSpider.LOGIN_ERR, None)
        body = response.body_as_unicode()
        if login_ok and login_err:
            is_logged = login_ok in body and login_err not in body
        elif login_ok:
            is_logged = login_ok in body
        elif login_err:
            is_logged = login_err not in body
        else:
            is_logged = False

        if is_logged:
            for url in self.next_urls:
                yield response.follow(url, self.parse)
        else:
            logger.error('Error during login in [%s]' % self.name)

    def parse_genres(self, response):
        # Return a list of `items.Genres` fully populated.
        raise NotImplementedError

    def parse_catalog(self, response):
        # Return a list of `items.Manga` fully populated. Is expected
        # to delegate the adquisition of the manga information to
        # `parse_collection`.
        #
        # In `parse_collection` is optional to return `rank` and
        # `rank_order` fields, so usually is here were this
        # information is retrieved.
        raise NotImplementedError

    def parse_collection(self, response, manga=None):
        # Return a single `items.Manga` fully or partially
        # populated. If `manga` is not None, this will use this
        # instance as a pre-populated instance.
        #
        # The fields `rank` and `rank_order` are optional, because
        # most sites don't publish the rank (number of views,
        # popularity, etc) in the manga view, that is where this
        # method read the data from, but in the 'latest' or 'full
        # list' view, that is where `parse_catalog` read from.
        #
        # Apart from that, the rest of the fields needs to be returned
        # (name, URL, etc) even if those are available in a different
        # view.
        raise NotImplementedError

    def parse_latest(self, response, until=None):
        # Return a list of `items.Manga` fully or partially populated.
        #
        # The manga information is completely ignored, and is only
        # used for the list of issues (`issues` field). Only the
        # issues that are new are updated, so deleted chapters are not
        # removed from the database during this processing (but in the
        # `parse_collection` one).
        #
        # But for convenience is recommended to delegate the manga
        # recovery to `parse_collection`, so the issue `order` field
        # is correct and not estimated.
        raise NotImplementedError

    def parse_manga(self, response, manga, issue):
        raise NotImplementedError
