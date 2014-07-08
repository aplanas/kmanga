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

from urlparse import urljoin

from scrapy.http import Request
from scrapy.selector import Selector

from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class Batoto(MangaSpider):
    name = 'batoto'
    allowed_domains = ['batoto.net']

    def get_genres_url(self):
        return 'http://www.batoto.net/search?advanced=1'

    get_catalog_url = get_genres_url

    def get_lasts_url(self, sice):
        return 'http://www.batoto.net/'

    def get_manga_url(self, manga, issue):
        return 'http://www.mangareader.net/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        sel = Selector(response)
        xp = '//div[@class="listeyan"]/ul/li/a/text()'
        genres = Genres()
        genres['names'] = sel.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        sel = Selector(response)
        xp = '//div[@class="mangaresultitem"]'
        for item in sel.xpath(xp):
            manga = Manga()
            # Rank
            xp = './/div[@class="c1"]/text()'
            manga['rank'] = item.xpath(xp).re(r'(\d+).')
            # Slug
            xp = './/div[@class="imgsearchresults"]/@style'
            manga['slug'] = item.xpath(xp).extract()[0].split('/')[-2]
            # URL
            xp = './/div[@class="manga_name"]//a/@href'
            manga['url'] = urljoin(response.url, item.xpath(xp).extract()[0])
            request = Request(manga['url'], self._parse_catalog_item)
            request.meta['manga'] = manga
            yield request

        # Next page
        xp = '//div[@id="sp"]/a[contains(text(), ">")]/@href'
        next_url = sel.xpath(xp).extract()
        if next_url:
            next_url = urljoin(response.url, next_url[0])
            # yield Request(next_url, self.parse_catalog)

    def _parse_catalog_item(self, response):
        sel = Selector(response)
        manga = response.meta['manga']
        # Name
        xp = '//h2[@class="aname"]/text()'
        manga['name'] = sel.xpath(xp).extract()
        # Alternate name
        xp = '//td[contains(text(),"%s")]/following-sibling::td/text()'
        manga['alt_name'] = sel.xpath(xp % 'Alternate Name:').extract()
        # Year or release
        manga['release'] = sel.xpath(xp % 'Year of Release:').extract()
        # Author
        manga['author'] = sel.xpath(xp % 'Author:').extract()
        # Artist
        manga['artist'] = sel.xpath(xp % 'Artist:').extract()
        # Reading direction
        rd = sel.xpath(xp % 'Reading Direction:').extract()
        manga['reading_direction'] = ('RL' if rd == 'Right to Left'
                                      else 'LR')
        # Status
        manga['status'] = sel.xpath(xp % 'Status:').extract()
        # Genres
        xp = '//span[@class="genretags"]/text()'
        manga['genres'] = sel.xpath(xp).extract()
        # Description
        # XXX TODO - Clean HTML tags and scape codes
        xp = '//div[@id="readmangasum"]/p/text()'
        manga['description'] = '\n'.join(sel.xpath(xp).extract())
        # Cover image
        xp = '//div[@id="mangaimg"]/img/@src'
        manga['image_urls'] = sel.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//table[@id="listing"]/tr[td]'
        for line in sel.xpath(xp):
            issue = Issue()
            # Name
            xp = './/a/text()'
            name_1 = line.xpath(xp).extract()
            xp = './/a/following-sibling::text()'
            name_2 = line.xpath(xp).extract()
            issue['name'] = name_1 + name_2
            # Number
            xp = './/a/text()'
            issue['number'] = line.xpath(xp).re(r'(\d+)')
            # Added
            xp = './td[2]/text()'
            issue['added'] = line.xpath(xp).extract()
            # URL
            xp = './/a/@href'
            url = line.xpath(xp).extract()
            issue['url'] = urljoin(response.url, url[0])
            manga['issues'].append(issue)
        yield manga

    def parse_lasts(self, since):
        pass

    def parse_manga(self, response, manga, issue):
        sel = Selector(response)
        xp = '//select[@id="pageMenu"]/option/@value'
        for number, url in enumerate(sel.xpath(xp).extract()):
            meta = (('manga', manga),
                    ('issue', issue),
                    ('number', number + 1),)
            yield Request(urljoin(response.url, url),
                          self._parse_page, meta=meta)

    def _parse_page(self, response):
        sel = Selector(response)
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//img[@id="img"]/@src'
        url = sel.xpath(xp).extract()[0]
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=[urljoin(response.url, url)]
        )
        return issue_page
