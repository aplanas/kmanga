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

import scrapy

from scraper.pipelines import convert_to_date
from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class MangaReader(MangaSpider):
    name = 'mangareader'
    allowed_domains = ['mangareader.net']

    def get_genres_url(self):
        return 'http://www.mangareader.net/popular'

    get_catalog_url = get_genres_url

    def get_latest_url(self, until):
        return 'http://www.mangareader.net/latest'

    def get_manga_url(self, manga, issue):
        return 'http://www.mangareader.net/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://www.mangareader.net/popular
        @returns items 1 1
        @returns request 0 0
        @scrapes names
        """

        xp = '//div[@class="listeyan"]/ul/li/a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://www.mangareader.net/popular/3660
        @returns items 0 0
        @returns request 30 40
        """

        xp = '//div[@class="mangaresultitem"]'
        for item in response.xpath(xp):
            manga = Manga()
            # Rank
            xp = './/div[@class="c1"]/text()'
            manga['rank'] = item.xpath(xp).re(r'(\d+).')
            manga['rank_order'] = 'ASC'
            # URL
            xp = './/div[@class="manga_name"]//a/@href'
            manga['url'] = response.urljoin(item.xpath(xp).extract()[0])
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'], self.parse_collection,
                                     meta=meta)
            yield request

        # Next page
        xp = '//div[@id="sp"]/a[contains(., ">")]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = response.urljoin(next_url[0])
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://www.mangareader.net/178/angel-densetsu.html
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
        xp = '//h2[@class="aname"]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//td[contains(text(),"%s")]/following-sibling::td/text()'
        _alt_name = response.xpath(xp % 'Alternate Name:')
        manga['alt_name'] = _alt_name.re(r'([^,;]+)')
        # Author
        manga['author'] = response.xpath(xp % 'Author:').extract()
        # Artist
        manga['artist'] = response.xpath(xp % 'Artist:').extract()
        # Reading direction
        rd = response.xpath(xp % 'Reading Direction:').extract()[0]
        manga['reading_direction'] = ('RL' if rd == 'Right to Left'
                                      else 'LR')
        # Status
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Genres
        xp = '//span[@class="genretags"]/text()'
        manga['genres'] = response.xpath(xp).extract()
        # Description
        xp = '//div[@id="readmangasum"]/p/text()'
        manga['description'] = '\n'.join(response.xpath(xp).extract())
        # Cover image
        xp = '//div[@id="mangaimg"]/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//table[@id="listing"]/tr[td]'
        for line in response.xpath(xp):
            issue = Issue(language='EN')
            # Name
            xp = './/a/text()'
            name_1 = line.xpath(xp).extract()
            xp = './/a/following-sibling::text()'
            name_2 = line.xpath(xp).extract()
            issue['name'] = name_1 + name_2
            # Number
            xp = './/a/text()'
            issue['number'] = line.xpath(xp).re(r'([.\d]+)$')
            # Order
            issue['order'] = len(manga['issues'])
            # Release
            xp = './td[2]/text()'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './/a/@href'
            url = line.xpath(xp).extract()
            issue['url'] = response.urljoin(url[0])
            manga['issues'].append(issue)
        yield manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://www.mangareader.net/latest
        @returns items 1 30
        @returns request 0 1
        @scrapes url name issues
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        xp = '//table[@class="updates"]/tr[@class="c2"]'
        for update in response.xpath(xp):
            # Check if is a new update
            xp = './/td[@class="c1"]/text()'
            update_date = update.xpath(xp).extract()
            update_date = convert_to_date(update_date[0])
            if update_date < until:
                return

            manga = Manga()
            # Name
            xp = './/a[@class="chapter"]/strong/text()'
            manga['name'] = update.xpath(xp).extract()
            # URL
            xp = './/a[@class="chapter"]/@href'
            url = update.xpath(xp).extract()
            manga['url'] = response.urljoin(url[0])

            # Parse the manga issues list
            manga['issues'] = []
            xp = './/a[@class="chaptersrec"]'
            for line in update.xpath(xp):
                issue = Issue(language='EN')
                # Name
                xp = 'text()'
                issue['name'] = line.xpath(xp).extract()
                # Number
                xp = 'text()'
                issue['number'] = line.xpath(xp).re(r'(\d+)$')
                # Order
                # This is only an estimation for now
                issue['order'] = issue['number']
                # Release
                issue['release'] = update_date
                # URL
                xp = '@href'
                url = line.xpath(xp).extract()
                issue['url'] = response.urljoin(url[0])
                manga['issues'].append(issue)
            yield manga

        # Next page
        xp = '//div[@id="latest"]/div[@id="sp"]/a[contains(., ">")]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = response.urljoin(next_url[0])
            meta = {'until': until}
            yield scrapy.Request(next_url, self.parse_latest, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//select[@id="pageMenu"]/option/@value'
        for number, url in enumerate(response.xpath(xp).extract()):
            meta = {
                'manga': manga,
                'issue': issue,
                'number': number + 1,
            }
            yield scrapy.Request(response.urljoin(url),
                                 self._parse_page, meta=meta)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//img[@id="img"]/@src'
        url = response.xpath(xp).extract()
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=[response.urljoin(url[0])]
        )
        return issue_page
