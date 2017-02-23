# -*- coding: utf-8 -*-
#
# (c) 2017 Alberto Planas <aplanas@gmail.com>
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
import urlparse

import scrapy

from scraper.items import Genres
from scraper.items import Manga
from scraper.items import Issue
from scraper.items import IssuePage

from .mangaspider import MangaSpider


class SubMangaOrg(MangaSpider):
    name = 'submangaorg'
    allowed_domains = ['submanga.org']

    def get_genres_url(self):
        return 'http://submanga.org/mangas'

    def get_catalog_url(self):
        return 'http://submanga.org/mangas?yearMin=0&yearMax=3000'\
               '&language=all&order=view&chapters=all&status=all'

    def get_collection_url(self, manga):
        return 'http://submanga.org/%s' % manga

    def get_latest_url(self, until):
        return 'http://submanga.org'

    def get_manga_url(self, manga, issue):
        return 'http://submanga.org/%s/%d' % (manga, int(issue))

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://submanga.org/mangas
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//a[@class="list-group-item category"]/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://submanga.org/mangas
        @returns items 0
        @returns request 1 37
        """

        # Get the page number from the URL
        qs = urlparse.urlparse(response.url).query
        qs = urlparse.parse_qs(qs)
        page = int(qs['page'][0]) if 'page' in qs else 0

        xp = '//div[contains(@class, "item_manga")]'
        for order, item in enumerate(response.xpath(xp)):
            manga = Manga()
            # URL
            xp = 'a/@href'
            manga['url'] = item.xpath(xp).extract_first()
            # Rank
            manga['rank'] = page * 6 * 6 + order + 1
            # Rank order
            manga['rank_order'] = 'ASC'
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'], self.parse_collection,
                                     meta=meta)
            yield request

        # Next page
        xp = '//ul[@class="pagination"]/li/a[@rel="next"]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            next_url = response.urljoin(next_url)
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://submanga.org/bloody-cross
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
        xp = '//a[@class="btn-link text-semibold text-mint"][2]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//span[contains(text(), "%s")]/following-sibling::text()'
        title = u'Títulos alternativos:'
        manga['alt_name'] = response.xpath(xp % title).re(r'([^,;]+)')
        # Author
        manga['author'] = response.xpath(xp % 'Autor:').extract()
        # Artist
        manga['artist'] = manga['author']
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status (Finalizado / En curso)
        xp = '//span[@class="text-2x text-thin"]/text()'
        manga['status'] = response.xpath(xp).extract()
        # Genres
        xp = '//span[contains(text(), "Generos:")]/following-sibling::a/text()'
        manga['genres'] = response.xpath(xp).extract()
        # Description
        xp = '//p[@class="text-justify"]/text()'
        manga['description'] = response.xpath(xp).extract()
        # Cover image
        xp = '//img[@class="img-cover-m"]/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//table[@id="caps-list"]//tr'
        lines = response.xpath(xp)
        for line in lines:
            xp = 'td[3]/a/img/@alt'
            langs = line.xpath(xp).extract()
            for lang in langs:
                issue = Issue(language=lang)
                # Name
                xp = 'td[2]/a/text()'
                issue['name'] = line.xpath(xp).extract()
                # Number
                xp = 'td[1]/a/text()'
                issue['number'] = line.xpath(xp).extract_first()
                # Order
                issue['order'] = int(issue['number'])
                # Release
                xp = 'td[4]/a/span/text()'
                issue['release'] = line.xpath(xp).extract()
                # URL
                xp = 'td[1]/a/@href'
                url = line.xpath(xp).extract_first()
                issue['url'] = '%s/%s' % (url, lang)
                manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://submanga.org
        @returns items 0
        @returns request 5 10
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//div[@class="timeline-entry"]//a/@href'
        for url in response.xpath(xp).extract():
            manga = Manga(url=url)
            meta = {'manga': manga}
            request = scrapy.Request(url, self.parse_collection, meta=meta)
            yield request

    def parse_manga(self, response, manga, issue):
        xp = '//script'
        base_url = response.xpath(xp).re_first(r'baseUrl: "(.*)",')
        pages = int(response.xpath(xp).re_first(r'chapter_pages: \'(.*)\''))

        for number in range(pages):
            number = number + 1
            url = '%s/%s' % (base_url, '%s.jpg' % number)
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number,
                image_urls=[url]
            )
            yield issue_page
