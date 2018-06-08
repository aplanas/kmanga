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
import re

from scraper.items import Genres, Manga, Issue, IssuePage
from .mangaspider import MangaSpider


NEXT_PAGE = 'https://bato.to/browse?page=%s'


class Batoto(MangaSpider):
    name = 'batoto'
    allowed_domains = ['bato.to']

    def get_genres_url(self):
        return 'https://bato.to/browse'

    def get_catalog_url(self):
        return 'https://bato.to/browse'

    def get_latest_url(self, until):
        return 'https://bato.to/latest'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url https://bato.to/browse
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//script'
        genres = Genres()
        genres_json = response.xpath(xp).re_first(r'"genres":\[[^\]]+\]')
        genres['names'] = re.findall(r'"name":"([^"]+)"', genres_json)
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url https://bato.to/browse?page=2
        @returns items 0
        @returns request 50 70
        """

        xp = '//div[@id="series-list"]//div[@class="item-text"]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './a/@href'
            url = item.xpath(xp).extract_first()
            manga['url'] = response.urljoin(url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

        # Next page
        re_ = r'@click="onClickPage\((.*)\)"'
        next_page_number = re.findall(re_, response.body_as_unicode())[-1]
        if next_page_number:
            next_url = NEXT_PAGE % next_page_number
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url https://bato.to/series/68329
        @returns items 1
        @returns request 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres rank rank_order description image_urls
        @scrapes issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # URL
        manga['url'] = response.url
        # Name
        xp = '//h3[@class="item-title"]/a/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//div[@class="pb-2 alias-set hairlines-fade-bottom"]/text()'
        manga['alt_name'] = response.xpath(xp).extract_first().split('/')
        # Author
        xp = '//div[@class="attr-item"]/b[contains(text(),"%s")]' \
            '/following-sibling::span/*/text()'
        manga['author'] = response.xpath(xp % 'Authors:').extract_first()
        # Artist
        manga['artist'] = response.xpath(xp % 'Authors:').extract()[1:]
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status
        xp = '//div[@class="attr-item"]/b[contains(text(),"%s")]' \
            '/following-sibling::span/text()'
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Genres
        genres = response.xpath(xp % 'Genres:').extract()[-1]
        manga['genres'] = genres.split('/')
        # Rank
        rank = response.xpath(xp % 'Rank:').extract_first()
        manga['rank'] = rank.split(',')[0]
        # Rank order
        manga['rank_order'] = 'ASC'
        # Description
        xp = '//pre/text()'
        manga['description'] = response.xpath(xp).extract()
        # Cover image
        xp = '//img[@class="shadow-6"]/@src'
        url = response.xpath(xp).extract_first()
        manga['image_urls'] = [response.urljoin(url)]

        # Get language from the title flag
        xp = '//div[@class="mt-4 title-set"]/span/@class'
        language = response.xpath(xp).extract_first()
        language = language.split()[-1]

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//div[@class="main"]/div'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language=language)
            # Name
            xp = './a//text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            xp = './a/b/text()'
            issue['number'] = line.xpath(xp).re(r'Ch.(\d+)')
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = './/i/text()'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './a/@href'
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url https://bato.to/latest
        @returns items 0
        @returns request 60
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//a[@class="item-title"]/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            manga = Manga(url=url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

    def parse_manga(self, response, manga, issue):
        images = re.findall(r'"(\d+)":"([^"]+)"', response.body_as_unicode())
        for number, url in images:
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number,
                image_urls=[url]
            )
            yield issue_page
