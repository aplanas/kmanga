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

from scraper.pipelines import convert_to_date
from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class SubMangaCom(MangaSpider):
    name = 'submangacom'
    allowed_domains = ['submanga.com']

    def get_genres_url(self):
        return 'http://submanga.com/series/g'

    def get_catalog_url(self):
        return 'http://submanga.com/series'

    def get_collection_url(self, manga):
        return 'http://submanga.com/%s' % manga

    def get_latest_url(self, until):
        return 'http://submanga.com'

    def get_manga_url(self, manga, issue):
        return 'http://submanga.com/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://submanga.com/series/g
        @returns items 1 1
        @returns request 0 0
        @scrapes names
        """

        xp = '//div[@class="container"]//td/a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://submanga.com/series
        @returns items 0 0
        @returns request 13000 15000
        """

        xp = '//div[@class="container"]//tr[td[not(@colspan)]]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = 'td/a/@href'
            manga['url'] = item.xpath(xp).extract()
            # Rank
            xp = 'td/a/b/text()'
            manga['rank'] = item.xpath(xp).re(r'([.\d]+).')
            manga['rank_order'] = 'ASC'
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'][0], self.parse_collection,
                                     meta=meta)
            yield request

        # Next page
        xp = '//div[@id="paginacion"]//li[@class="next"]/a/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = response.urljoin(next_url[0])
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://submanga.com/Soul_Eater
        @returns items 1 1
        @returns request 1 1
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # Submanga returns a 404 page as a normal page (200)
        xp = '//title/text()'
        title = response.xpath(xp).extract()
        if title[0] == u'404 \u2014 submanga.com':
            return

        # Name
        xp = '//div[@class="well"]/h1/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        manga['alt_name'] = []  # manga['name']
        # Author
        xp = '//div[@class="well"]/' \
             'a[contains(@href, "http://submanga.com/autor/")]/text()'
        manga['author'] = response.xpath(xp).extract()
        # Artist
        xp = '//div[@class="well"]/' \
             'a[contains(@href, "http://submanga.com/revista/")]/text()'
        manga['artist'] = response.xpath(xp).extract()
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status
        manga['status'] = 'Ongoing'
        # Genres
        xp = '//div[@class="well"]/' \
             'a[contains(@href, "http://submanga.com/genero/")]/text()'
        manga['genres'] = response.xpath(xp).extract()
        # Description
        xp = '//div[@class="well"]/text()'
        description = response.xpath(xp).extract()
        manga['description'] = max((len(i), i) for i in description)[1]
        # Cover image
        xp = '//div[@class="well"]/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Full list of issues
        xp = '//ul[@class="nav nav-tabs"]/li[2]/a/@href'
        issues_url = response.xpath(xp).extract()
        meta = {'manga': manga}
        request = scrapy.Request(issues_url[0], self._parse_issues, meta=meta)
        return request

    def _parse_issues(self, response):
        """Generate the list of issues for a manga

        @url http://submanga.com/Soul_Eater/completa
        @returns items 100 200
        @returns request 0 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//table[@class="table table-striped table-hover"]/' \
             'tbody/tr[td[not(@colspan)]]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language='ES')
            # Name
            xp = 'td[1]/a/text()'
            name_1 = line.xpath(xp).extract()
            xp = 'td[1]/a/strong/text()'
            name_2 = line.xpath(xp).extract()
            issue['name'] = name_1 + name_2
            # Number
            issue['number'] = name_2
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # URL
            xp = 'td[1]/a/@href'
            issue['url'] = line.xpath(xp).extract()
            manga['issues'].append(issue)

        # Issues list will store the issues that we need to fill with
        # the release date.  Because is async (and not multithread),
        # there is not race condition every time we remove an element
        # from the list.  This means that when the last item is
        # removed, every issue have a release date and I can return
        # the manga item.
        issues = manga['issues'][:]
        requests = [
            scrapy.Request(
                i['url'][0],
                self._parse_issue_date, meta={
                    'manga': manga,
                    'issue': i,
                    'issues': issues,
                },
                errback=lambda err, _i=i: self._on_error_issue_date(err, meta={
                    'manga': manga,
                    'issue': _i,
                    'issues': issues,
                })) for i in manga['issues']
        ]
        return requests

    def _on_error_issue_date(self, err, meta):
        """Called when a 404 happends in a issue."""
        # Remove the issue in the manga and in the issues list.
        manga = meta['manga']
        issue = meta['issue']
        issues = meta['issues']

        manga['issues'].remove(issue)
        # In the issues list is empty, this is the last issue, so we
        # can return the manga item.
        issues.remove(issue)
        if not issues:
            return manga

    def _parse_issue_date(self, response):
        """Generate the list of issues for a manga

        @url http://submanga.com/Soul_Eater/1/6674
        @returns items 0 1
        @returns request 0 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description issues
        """
        manga = response.meta['manga']
        issue = response.meta['issue']
        issues = response.meta['issues']

        # Release
        xp = '//div[@class="well"]/text()'
        issue['release'] = response.xpath(xp).re(r'\d{2}/\d{2}/\d{4}')

        # In Submanga a 404 page returns a 200.  If we do not have
        # release date we can assume that is a 404 and drop the issue.
        if not issue['release']:
            manga['issues'].remove(issue)

        # In the issues list is empty, this is the last issue, so we
        # can return the manga item.
        issues.remove(issue)
        if not issues:
            return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://submanga.com
        @returns items 1 20
        @returns request 0 1
        @scrapes url name issues
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        if 'signal' in response.meta:
            signal = response.meta['signal']
        else:
            signal = {'continue': True}

        xp = '//table[@class="table table-striped table-hover"]/' \
             'tbody/tr[td[not(@colspan)]]'
        for line in response.xpath(xp):
            manga = Manga()
            # Name
            xp = 'td[1]/a/text()'
            manga['name'] = line.xpath(xp).extract()
            # URL
            xp = 'td[1]/a/@href'
            # Recover the URL from the issue address.
            url = line.xpath(xp).extract()[0]
            url = url.split('/')[3]
            url = 'http://submanga.com/%s' % url
            manga['url'] = url

            # Parse the manga issues list (single element)
            issue = Issue(language='ES')
            manga['issues'] = [issue]
            # Name
            xp = 'td[1]/a/text()'
            name_1 = line.xpath(xp).extract()
            xp = 'td[1]/a/strong/text()'
            name_2 = line.xpath(xp).extract()
            issue['name'] = name_1 + name_2
            # Number
            issue['number'] = name_2
            # Order
            # This is only an estimation for now
            issue['order'] = issue['number']
            # URL
            xp = 't[1]/a/@href'
            issue['url'] = line.xpath(xp).extract()

            meta = {
                'until': until,
                'signal': signal,
                'manga': manga,
            }
            request = scrapy.Request(issue['url'][0], self._parse_latest,
                                     meta=meta)
            yield request

        # Next page
        xp = '//div[@id="paginacion"]//li[@class="next"]/a/@href'
        next_url = response.xpath(xp).extract()
        if next_url and signal['continue']:
            next_url = next_url[0]
            meta = {
                'until': until,
                'signal': signal,
            }
            yield scrapy.Request(next_url, self.parse_latest, meta=meta)

    def _parse_latest(self, response):
        until = response.meta['until']
        signal = response.meta['signal']
        manga = response.meta['manga']

        # There is only a single issue
        issue = manga['issues'][0]

        # Release
        xp = '//div[@class="well"]/text()'
        update_date = response.xpath(xp).re(r'\d{2}/\d{2}/\d{4}')
        update_date = convert_to_date(update_date[0], dmy=True)
        issue['release'] = update_date

        if update_date < until:
            signal['continue'] = False
        else:
            return manga

    def parse_manga(self, response, manga, issue):
        xp = '//a[contains(@class, "lectora")]/@href'
        # Point to the first page
        url = response.xpath(xp).extract() + '/1'
        meta = {
            'manga': manga,
            'issue': issue,
        }
        return scrapy.Request(url[0], self._parse_page, meta=meta)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']

        # The page number is the last element in the URL
        number = response.url.split('/')[-1]

        xp = '//div[@id="paginadora"]/a/img/@src'
        url = response.xpath(xp).extract()
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=url
        )
        yield issue_page

        # Next page
        xp = '//li[@class="pagina"]/a/@href'
        next_url = response.xpath(xp).extract()[1]
        next_number = next_url.split('/')[-1]
        if int(next_number) == int(number) + 1:
            yield scrapy.Request(next_url, self._parse_page,
                                 meta=response.meta)
