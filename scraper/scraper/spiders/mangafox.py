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

from scraper.pipelines import convert_to_date
from scraper.items import Genres, Manga, Issue, IssuePage
from .mangaspider import MangaSpider


class Mangafox(MangaSpider):
    name = 'mangafox'
    allowed_domains = ['fanfox.net']

    def get_genres_url(self):
        return 'http://fanfox.net/search.php'

    def get_catalog_url(self):
        return 'http://fanfox.net/directory/'

    def get_latest_url(self, until):
        return 'http://fanfox.net/releases/'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://fanfox.net/search.php
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//ul[@id="genres"]//a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://fanfox.net/directory/
        @returns items 0
        @returns request 30 45
        """

        xp = '//ul[@class="list"]/li'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './/a[@class="title"]/@href'
            url = item.xpath(xp).extract_first()
            manga['url'] = response.urljoin(url)
            # Rank
            xp = './/p[@class="info"]/label/text()'
            manga['rank'] = item.xpath(xp).re(r'(\d+)')
            # Rank order
            manga['rank_order'] = 'ASC'
            meta = {'manga': manga}
            yield response.follow(manga['url'], self.parse_collection,
                                  meta=meta)

        # Next page
        xp = '//a[span[@class="next"]]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://fanfox.net/manga/a_bias_girl/
        @returns items 1
        @returns request 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description image_urls issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # Check if manga is licensed
        xp = '//div[@class="warning" and contains(text(),"has been licensed")]'
        if response.xpath(xp).extract():
            return

        # URL
        manga['url'] = response.url
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
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://fanfox.net/releases/
        @returns items 0
        @returns request 20 100
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//h3[@class="title"]/a/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            manga = Manga(url=url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

        # Check the oldest update date
        xp = '//em/text()'
        update_date = response.xpath(xp).extract()[-1]
        update_date = convert_to_date(update_date)
        if update_date < until:
            return

        # Next page
        xp = '//a[span[@class="next"]]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            meta = {'until': until}
            yield response.follow(next_url, self.parse_latest, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//form[@id="top_bar"]//select[@class="m"]/option/@value'
        for number in response.xpath(xp).extract():
            if number != '0':
                meta = {
                    'manga': manga,
                    'issue': issue,
                    'number': int(number),
                }
                yield response.follow('%s.html' % number,
                                      self._parse_page, meta=meta)

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
