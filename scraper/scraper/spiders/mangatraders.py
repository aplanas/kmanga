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

import scrapy

from scraper.pipelines import convert_to_date
from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


class MangaTraders(MangaSpider):
    name = 'mangatraders'
    allowed_domains = ['mangatraders.biz']

    form_url = 'http://mangatraders.biz/auth/process.login.php'
    username_field = 'EmailAddress'
    password_field = 'Password'
    login_check = {
        MangaSpider.LOGIN_ERR: 'Incorrect Password'
    }

    def get_login_url(self):
        # This URL doen't contains the form, but will be requested in
        # any case.  The action URL is in the field `form_url`
        return 'http://mangatraders.biz/auth/#login'

    def get_genres_url(self):
        return 'http://mangatraders.biz/search/'

    def get_catalog_url(self):
        return 'http://mangatraders.biz/directory/'

    def get_latest_url(self, until):
        return 'http://mangatraders.biz/'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://mangatraders.biz/search/
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//div[contains(@class, "genres")]/a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://mangatraders.biz/directory/
        @returns items 0
        @returns request 27
        """

        # XXX TODO - 'directory' have some missing manga, the ones
        # that start with symbols.  Use the AJAX version from
        # 'explore'
        xp = '//a[@class="btn btn-default"]/@href'
        for next_url in response.xpath(xp).extract():
            next_url = response.urljoin(next_url)
            yield scrapy.Request(next_url, self._parse_catalog)

    def _parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://mangatraders.biz/directory/?q=B
        @returns items 0
        @returns request 50 100
        """

        xp = '//a[@class="ttip"]/@href'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './td[1]/strong/a/@href'
            manga['url'] = item.xpath(xp).extract_first()
            meta = {'manga': manga}
            request = scrapy.Request(manga['url'], self.parse_collection,
                                     meta=meta)
            yield request

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://mangatraders.biz/series/ShingekiNoKyojin
        @returns items 0
        @returns request 1
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            # This URL is of '/series/' type, we need to change it as
            # a '/manga/' type later.
            manga = Manga(url=response.url)

        # XXX TODO - For now we only publish manga that can be read
        # online, instead of offering the volumes that are in ZIP
        # format.

        # The URL used is the '/series/' type.  We need to use the
        # '/manga/' type as a primary key (needed to allow the update
        # of the last chapters from the main page)
        xp = '//div[contains(@class, "startReading")]/a/@href'
        url = response.xpath(xp).extract_first()
        if url:
            url = response.urljoin(url)
            meta = {'manga': manga}
            request = scrapy.Request(url, self._parse_collection,
                                     meta=meta)
            return request

    def _parse_collection(self, response):
        """Generate the list of issues for a manga

        @url http://mangatraders.biz/manga/Shingeki-No-Kyojin
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
        xp = '//h1/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//div/b[contains(text(),"%s")]/following-sibling::text()'
        manga['alt_name'] = response.xpath(
            xp % 'Alternate Name(s):').re(r'([^,]+)')
        # Author
        xp = '//div/b[contains(text(),"%s")]/following-sibling::*/text()'
        manga['author'] = response.xpath(xp % 'Author(s):').extract()
        # Artist
        manga['artist'] = manga['author']
        # Reading direction
        manga['reading_direction'] = response.xpath(
            xp % 'Type:').extract_first()
        # Status
        manga['status'] = response.xpath(xp % 'Status:').extract_first()
        # Genres
        xp = '//div/b[contains(text(),"%s")]/following-sibling::*/text()'
        manga['genres'] = response.xpath(xp % 'Genre(s):').extract()
        # Rank order
        manga['rank_order'] = 'DESC'
        # Description
        xp = '//div[@class="description"]/text()'
        manga['description'] = response.xpath(xp).extract()
        # Cover image
        xp = '//div[contains(@class,"leftImage")]/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//a[@class="chapterLink"]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language='EN')
            # Name
            xp = './span/text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            issue['number'] = line.xpath(xp).re(r'([.\d]+)$')
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = './time/@datetime'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './@href'
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)

        # Rank
        url = response.urljoin('subscribe.button.php')
        xp = '//input[@class="IndexName"]/@value'
        index_name = response.xpath(xp).extract_first()
        form_data = {'IndexName': index_name}
        meta = {'manga': manga}
        yield scrapy.FormRequest(url, self._parse_subscribe,
                                 formdata=form_data, meta=meta)

    def _parse_subscribe(self, response):
        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            # This is not correct at all, but we can use this to allow
            # the testing for this contract
            manga = Manga(url=response.url)

        xp = '//span[@id="numSubscribe"]/@alt'
        manga['rank'] = response.xpath(xp).extract_first()
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://mangatraders.biz/
        @returns items 0
        @returns request 25 100
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `_parse_collection` (via `_parse_latest` indirection)
        xp = '//a[@class="latestSeries"]/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            request = scrapy.Request(url, self._parse_latest)
            yield request

        # Check the oldest update date
        xp = '//time[@class="timeago"]/@datetime'
        update_date = response.xpath(xp).extract()[-1].strip()
        update_date = convert_to_date(update_date)
        if update_date < until:
            return

        # XXX TODO - move to the next page via 'Show More'

    def _parse_latest(self, response):
        # Recover the URL of type '/manga/'
        xp = '//a[@class="list-link"]/@href'
        url = response.urljoin(response.xpath(xp).extract_first())
        manga = Manga(url=url)
        meta = {'manga': manga}
        request = scrapy.Request(url, self._parse_collection, meta=meta)
        return request

    def parse_manga(self, response, manga, issue):
        # Generate a whole-chapter URL.  The JavaScript code generate
        # the URL from scratch.  We take a shortcut removing the
        # `page` suffix.
        url = response.url
        url = url.replace('-page-1.html', '.html')
        meta = {
            'manga': manga,
            'issue': issue,
        }
        request = scrapy.Request(url, self._parse_manga, meta=meta)
        return request

    def _parse_manga(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']

        xp = '//div[@class="fullchapimage"]/img/@src'
        for number, url in enumerate(response.xpath(xp).extract()):
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number+1,
                image_urls=[url]
            )
            yield issue_page
