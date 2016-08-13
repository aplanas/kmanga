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
import urllib

import scrapy

from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class KissManga(MangaSpider):
    name = 'kissmanga'
    allowed_domains = ['kissmanga.com']
    vhost_ip = '93.174.95.110'

    def get_genres_url(self):
        return 'http://kissmanga.com/AdvanceSearch'

    def get_catalog_url(self):
        return 'http://kissmanga.com/MangaList'

    def get_latest_url(self, until):
        return 'http://kissmanga.com'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://kissmanga.com/AdvanceSearch
        @returns items 1 1
        @returns request 0 0
        @scrapes names
        """

        xp = '//a[@name="aGenre"]/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://kissmanga.com/MangaList?page=200
        @returns items 0 0
        @returns request 25 30
        """

        xp = '//table[@class="listing"]/tr/td[1]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = 'a/@href'
            manga['url'] = response.urljoin(item.xpath(xp).extract()[0])
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'], self.parse_collection,
                                     meta=meta)
            yield request

        # Next page
        xp = '//ul[@class="pager"]/li/a[contains(., "Next")]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = response.urljoin(next_url[0])
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://kissmanga.com/Manga/Naruto
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
        xp = '//div[@class="barContent"]//a[@class="bigChar"]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//span[@class="info" and contains(text(), "%s")]' \
             '/following-sibling::a/text()'
        manga['alt_name'] = response.xpath(xp % 'Other name:').extract()
        # Author
        manga['author'] = response.xpath(xp % 'Author:').extract()
        # Artist
        manga['artist'] = manga['author']
        # Genres
        manga['genres'] = response.xpath(xp % 'Genres:').extract()
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status
        xp = '//span[@class="info" and contains(text(), "%s")]' \
             '/following-sibling::text()[1]'
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Rank
        manga['rank'] = response.xpath(xp % 'Views:').re(r'(\d+).')
        manga['rank_order'] = 'DESC'
        # Description
        xp = '//p[span[@class="info" and contains(text(), "%s")]]'\
             '/following-sibling::p[1]/text()'
        manga['description'] = response.xpath(xp % 'Summary:').extract()
        # Cover image
        xp = '//div[@id="rightside"]//img/@src'
        url = response.xpath(xp).extract()
        manga['image_urls'] = [response.urljoin(url[0])]

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//table[@class="listing"]/tr[td]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language='EN')
            # Name
            xp = './/a/text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            xp = './/a/text()'
            number = line.xpath(xp).re(
                r'(?:[Vv]ol.[.\d]+)?\s*'
                r'(?:[Cc]h.|[Ee]p.|[Cc]haper|[Pp]art.)?(\d[.\d]+)')
            issue['number'] = number[0] if len(number) > 1 else number
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = './td[2]/text()'
            issue['release'] = line.xpath(xp).re(r'\d{1,2}/\d{1,2}/\d{4}')
            # URL
            xp = './/a/@href'
            url = line.xpath(xp).extract()
            issue['url'] = response.urljoin(url[0])
            manga['issues'].append(issue)
        yield manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://kissmanga.com/
        @returns items 0 0
        @returns request 5 10
        @scrapes url name issues
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # XXX TODO - we ignore the `until` date, and make a full parse
        # of the initial scroll panel (that contain old entries)
        xp = '//div[@class="items"]/div'
        for update in response.xpath(xp):
            manga = Manga()
            # Name
            xp = './/a/text()'
            manga['name'] = update.xpath(xp).extract()
            # URL
            xp = './/a/@href'
            url = update.xpath(xp).extract()
            manga['url'] = response.urljoin(url[0])

            # Parse the manga issues list
            request = scrapy.Request(manga['url'], self.parse_collection,
                                     meta={'manga': manga})
            yield request

    def parse_manga(self, response, manga, issue):
        issue_pages = []
        xp = '//script'
        images = response.xpath(xp).re(r'lstImages.push\("(.*)"\);')
        for number, url in enumerate(images):
            url = urllib.unquote(url)
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number + 1,
                image_urls=[url]
            )
            issue_pages.append(issue_page)
        return issue_pages
