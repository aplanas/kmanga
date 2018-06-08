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


class MangaReader(MangaSpider):
    name = 'mangareader'
    allowed_domains = ['mangareader.net']

    def get_genres_url(self):
        return 'https://www.mangareader.net/popular'

    get_catalog_url = get_genres_url

    def get_latest_url(self, until):
        return 'https://www.mangareader.net/latest'

    def get_manga_url(self, manga, issue):
        return 'https://www.mangareader.net/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        """Generate the list of genres.

        @url https://www.mangareader.net/popular
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//div[@class="listeyan"]/ul/li/a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url https://www.mangareader.net/popular/3660
        @returns items 0
        @returns request 30 40
        """

        xp = '//div[@class="mangaresultitem"]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './/div[@class="manga_name"]//a/@href'
            manga['url'] = response.urljoin(item.xpath(xp).extract_first())
            # Rank
            xp = './/div[@class="c1"]/text()'
            manga['rank'] = item.xpath(xp).re(r'(\d+).')
            # Rank order
            manga['rank_order'] = 'ASC'
            meta = {'manga': manga}
            yield response.follow(manga['url'], self.parse_collection,
                                  meta=meta)

        # Next page
        xp = '//div[@id="sp"]/a[contains(., ">")]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url https://www.mangareader.net/178/angel-densetsu.html
        @returns items 1
        @returns request 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description image_urls issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # URL
        manga['url'] = response.url
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
        rd = response.xpath(xp % 'Reading Direction:').extract_first()
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
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url https://www.mangareader.net/latest
        @returns items 0
        @returns request 25 100
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//a[@class="chapter"]/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            manga = Manga(url=url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

        # Check the oldest update date
        xp = '//td[@class="c1"]/text()'
        update_date = response.xpath(xp).extract()[-1]
        update_date = convert_to_date(update_date)
        if update_date < until:
            return

        # Next page
        xp = '//div[@id="latest"]/div[@id="sp"]/a[contains(., ">")]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            meta = {'until': until}
            yield response.follow(next_url, self.parse_latest, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//select[@id="pageMenu"]/option/@value'
        for number, url in enumerate(response.xpath(xp).extract()):
            meta = {
                'manga': manga,
                'issue': issue,
                'number': number + 1,
            }
            yield response.follow(url, self._parse_page, meta=meta)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//img[@id="img"]/@src'
        url = response.xpath(xp).extract_first()
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=[response.urljoin(url)]
        )
        return issue_page
