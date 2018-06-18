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
from scraper.pipelines import convert_to_number
from scraper.items import Genres, Manga, Issue, IssuePage
from .mangaspider import MangaSpider


class MangaDex(MangaSpider):
    name = 'mangadex'
    allowed_domains = ['mangadex.org']
    # Less that 500 hits every 10 minutes
    download_delay = 0.8

    def get_genres_url(self):
        return 'https://mangadex.org/search'

    def get_catalog_url(self):
        # Some order options:
        #  /0/ Order by last update (asc)
        #  /1/ Order by last update (desc)
        #  /2/ Order by name (asc)
        #  /3/ Order by name (desc)
        #  /4/ Order by comments (asc)
        #  /5/ Order by comments (desc)
        #  /6/ Order by rank (asc)
        #  /7/ Order by rank (desc)
        #  /8/ Order by views (asc)
        #  /9/ Order by views (desc)
        #  /10/ Order by follows (asc)
        #  /11/ Order by follows (desc)
        return 'https://mangadex.org/titles/2/1/'

    def get_latest_url(self, until):
        return 'https://mangadex.org/'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url https://mangadex.org/search
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//div[@class="checkbox"]/label/span/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url https://mangadex.org/titles/2/1
        @returns items 0
        @returns request 40
        """

        xp = '//div[@class="row"]/div'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './/a[@class="manga_title"]/@href'
            url = item.xpath(xp).extract_first()
            manga['url'] = response.urljoin(url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

        # Next page
        xp = '//ul[@class="pagination"]/li[@class="active"]' \
            '/following-sibling::li[@class="paging"]/a/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url https://mangadex.org/manga/39/one-piece
        @returns items 0
        @returns request 1
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # URL
        manga['url'] = response.url
        # Name
        xp = '//h3[@class="panel-title"]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//th[contains(text(),"%s")]' \
            '/following-sibling::td/descendant-or-self::*/text()'
        manga['alt_name'] = response.xpath(xp % 'Alt name(s):').extract()
        # Author
        manga['author'] = response.xpath(xp % 'Author:').re(r'([^,]+),?')
        # Artist
        manga['artist'] = response.xpath(xp % 'Artist:').re(r'([^,]+),?')
        # Reading direction
        xp = '//h3[@class="panel-title"]/img/@alt'
        manga['reading_direction'] = response.xpath(xp).extract_first()
        # Status
        xp = '//th[contains(text(),"%s")]' \
            '/following-sibling::td/descendant-or-self::*/text()'
        manga['status'] = response.xpath(xp % 'Pub. status:').extract_first()
        # Genres
        demographic = response.xpath(xp % 'Demographic:').extract()
        genres = response.xpath(xp % 'Genres:').extract()
        manga['genres'] = demographic + genres
        # Rank
        rank = response.xpath(xp % 'Rating:').extract_first()
        manga['rank'] = 100 * convert_to_number(rank)
        # Rank order
        manga['rank_order'] = 'DESC'
        # Description
        manga['description'] = response.xpath(xp % 'Description:').extract()
        # Cover image
        xp = '//img[@class="border-radius"]/@src'
        url = response.xpath(xp).extract_first()
        manga['image_urls'] = [response.urljoin(url)]

        # Information needed to deduce the issue order
        xp = '//p[@class="text-center"]/text()'
        chapters = response.xpath(xp).re_first(r'of (.*) chapters')
        if chapters:
            chapters = convert_to_number(chapters, as_int=True)
        else:
            xp = '//tr[contains(@id,"chapter_")]'
            chapters = len(response.xpath(xp))

        # If the manga is empty (is frequent in MangaDex), end the
        # processing
        if not chapters:
            return

        # Parse the manga issues list
        manga['issues'] = []
        meta = {
            'manga': manga,
            'chapters': chapters,
        }
        url = response.url + '/chapters/1'
        return response.follow(url, self._parse_issues, meta=meta)

    def _parse_issues(self, response):
        """Generate the list of issues for a manga

        @url https://mangadex.org/manga/39/one-piece
        @returns items 1
        @returns request 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres rank rank_order description image_urls
        @scrapes issues
        """
        manga = response.meta['manga']
        chapters = response.meta['chapters']

        xp = '//tr[contains(@id,"chapter_")]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue()
            # Name
            xp = './/a/text()'
            issue['name'] = line.xpath(xp).extract_first()
            # Number
            xp = './/a/@data-chapter-num'
            issue['number'] = line.xpath(xp).extract()
            # Order
            issue['order'] = chapters - len(manga['issues'])
            # Language
            xp = './/img/@title'
            issue['language'] = line.xpath(xp).extract()
            # Release
            xp = './/time/@datetime'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './/a/@href'
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)

        # Next page
        xp = '//ul[@class="pagination"]/li[@class="active"]' \
            '/following-sibling::li[@class="paging"]/a/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            meta = {
                'manga': manga,
                'chapters': chapters,
            }
            return response.follow(next_url, self._parse_issues, meta=meta)
        else:
            return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url https://mangadex.org/
        @returns items 0
        @returns request 120
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//a[@class="manga_title"]/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            manga = Manga(url=url)
            meta = {'manga': manga}
            request = response.follow(url, self.parse_collection, meta=meta)
            yield request

        # Check the oldest update date
        xp = '//time/@datetime'
        update_date = response.xpath(xp).extract()[-1].strip()
        update_date = convert_to_date(update_date)
        if update_date < until:
            return

        # Next page
        xp = '//ul[@class="pagination"]/li[@class="active"]' \
            '/following-sibling::li[@class="paging"]/a/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self._parse_issues, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//select[@id="jump_page"]/option/@value'
        pages = response.xpath(xp).extract()
        if pages:
            for number in pages:
                meta = {
                    'manga': manga,
                    'issue': issue,
                    'number': int(number),
                }
                yield response.follow(number, self._parse_page, meta=meta)
        else:
            meta = {
                'manga': manga,
                'issue': issue,
            }
            yield response.follow(response.url,
                                  self._parse_webtoon, meta=meta)

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

    def _parse_webtoon(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']

        xp = '//img[@class="webtoon"]/@src'
        for number, url in enumerate(response.xpath(xp).extract()):
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number,
                image_urls=url
            )
            yield issue_page
