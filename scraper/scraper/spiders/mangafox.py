# -*- coding: utf-8 -*-
#
# (c) 2016 Alberto Planas <aplanas@gmail.com>
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
from urlparse import urljoin

import scrapy

from scraper.pipelines import convert_to_date
from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class Mangafox(MangaSpider):
    name = 'mangafox'
    allowed_domains = ['mangafox.me']

    def get_genres_url(self):
        return 'http://mangafox.me/search.php'

    def get_catalog_url(self):
        return 'http://mangafox.me/directory/'

    def get_latest_url(self, until):
        return 'http://mangafox.me/releases/'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://mangafox.me/search.php
        @returns items 1 1
        @returns request 0 0
        @scrapes names
        """

        xp = '//ul[@id="genres"]//a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://mangafox.me/directory/
        @returns items 0 0
        @returns request 30 45
        """

        xp = '//ul[@class="list"]/li'
        for item in response.xpath(xp):
            manga = Manga()
            # Rank
            xp = './/p[@class="info"]/label/text()'
            manga['rank'] = item.xpath(xp).re('(\d+)')
            manga['rank_order'] = 'ASC'
            # URL
            xp = './/a[@class="title"]/@href'
            manga['url'] = item.xpath(xp).extract()
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'][0], self.parse_collection,
                                     meta=meta)
            yield request

        # Next page
        xp = '//a[span[@class="next"]]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = urljoin(response.url, next_url[0])
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://mangafox.me/manga/shingeki_no_kyojin/
        @returns items 1 1
        @returns request 0 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # Name
        xp = '//title/text()'
        manga['name'] = response.xpath(xp).re(r'(.*) - Read')
        # Alternate name
        xp = '//div[@id="title"]/h3//text()'
        manga['alt_name'] = response.xpath(xp).extract()
        # Author
        xp = '//div[@id="title"]//tr[2]/td[2]/a/text()'
        manga['author'] = response.xpath(xp).extract()
        # Artist
        xp = '//div[@id="title"]//tr[2]/td[3]/a/text()'
        manga['artist'] = response.xpath(xp).extract()
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status
        xp = './/div[@class="data"][1]/span/text()'
        manga['status'] = response.xpath(xp).re(r'\w+')
        # Genres
        xp = '//div[@id="title"]//tr[2]/td[4]/a/text()'
        manga['genres'] = response.xpath(xp).extract()
        # Description
        xp = '//div[@id="title"]/p[@class="summary"]/text()'
        manga['description'] = response.xpath(xp).extract()
        # Cover image
        xp = '//div[@class="cover"]/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//ul[@class="chlist"]/li'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language='EN')
            # Name
            xp = '(.//h3|.//h4)/a/text()'
            name_1 = line.xpath(xp).extract()
            xp = '(.//h3|.//h4)/span[@class="title nowrap"]/text()'
            name_2 = line.xpath(xp).extract()
            issue['name'] = name_1 + name_2
            # Number
            xp = '(.//h3|.//h4)/a/text()'
            issue['number'] = line.xpath(xp).re(r'.*?([.\d]+)$')
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = './/span[@class="date"]/text()'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './/a[@class="tips"]/@href'
            issue['url'] = line.xpath(xp).extract()
            manga['issues'].append(issue)
        yield manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://mangafox.me/releases/
        @returns items 1 100
        @returns request 0 1
        @scrapes url name issues
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        xp = '//ul[@id="updates"]/li/div'
        for update in response.xpath(xp):
            manga = Manga()
            # Name
            xp = './/h3/a/text()'
            manga['name'] = update.xpath(xp).extract()
            # URL
            xp = './/h3/a//@href'
            manga['url'] = update.xpath(xp).extract()

            # Parse the manga issues list
            manga['issues'] = []
            xp = './/dt'
            for line in update.xpath(xp):
                # Check if is a new update
                xp = './/em/text()'
                update_date = update.xpath(xp).extract()
                update_date = convert_to_date(update_date[0])
                if update_date < until:
                    return

                issue = Issue(language='EN')
                # Name
                xp = './/span//text()'
                issue['name'] = line.xpath(xp).extract()
                # Number
                xp = './/span/a/text()'
                issue['number'] = line.xpath(xp).re(r'(\d+)$')
                # Order
                # This is only an estimation for now
                issue['order'] = issue['number']
                # Release
                issue['release'] = update_date
                # URL
                xp = './/span/a/@href'
                url = line.xpath(xp).extract()
                issue['url'] = urljoin(response.url, url[0])
                manga['issues'].append(issue)
            yield manga

        # Next page
        xp = '//a[span[@class="next"]]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = urljoin(response.url, next_url[0])
            meta = {'until': until}
            yield scrapy.Request(next_url, self.parse_latest, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//form[@id="top_bar"]//select[@class="m"]/option/@value'
        for number in response.xpath(xp).extract():
            if number != '0':
                meta = {
                    'manga': manga,
                    'issue': issue,
                    'number': int(number),
                }
                url = response.urljoin('%s.html' % number)
                yield scrapy.Request(url, self._parse_page, meta=meta)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//img[@id="image"]/@src'
        url = response.xpath(xp).extract()
        if url:
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number,
                image_urls=url
            )
            return issue_page
