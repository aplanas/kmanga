# -*- coding: utf-8 -*-
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

import scrapy

from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


AJAX_SEARCH = 'http://bato.to/search_ajax?p=%d'


def _v2i(viewers):
    """Convert vievers to integer."""
    if 'k' in viewers:
        return int(1000 * float(viewers[:-1]))
    elif 'm' in viewers:
        return int(1000 * 1000 * float(viewers[:-1]))
    else:
        return int(viewers)


class Batoto(MangaSpider):
    name = 'batoto'
    allowed_domains = ['bato.to']

    # download_delay = 1

    def get_genres_url(self):
        return 'http://bato.to/search?advanced=1'

    def get_catalog_url(self):
        return AJAX_SEARCH % 1

    def get_lasts_url(self, sice):
        return 'http://bato.to/'

    def parse_genres(self, response):
        xp = '//div[@class="genre_buttons"]/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        xp = '//tr[not(@class) and not(@id)]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './td[1]/strong/a/@href'
            manga['url'] = item.xpath(xp).extract()
            # In Batoto there is not rank, but a combination of
            # rating, viewers and followers.
            xp = './td[3]/div/@title'
            rating = float(item.xpath(xp).re(r'([.\d]+)/5')[0])
            xp = './td[4]/text()'
            viewers = _v2i(item.xpath(xp).extract()[0])
            xp = './td[5]/text()'
            followers = int(item.xpath(xp).extract()[0])
            manga['rank'] = (rating + 0.1) * viewers * followers
            # URL Hack to avoid a redirection. This is used because
            # the download_delay is also added to the redirector.  The
            # other solution is to assign to request this:
            # scrapy.Request(manga['url'][0], self._parse_catalog_item)
            url = manga['url'][0].split('_/')[-1]
            url = 'http://bato.to/comic/_/comics/%s' % url
            request = scrapy.Request(url, self._parse_catalog_item)
            request.meta['manga'] = manga
            yield request

        # Next page
        xp = '//tr[@id="show_more_row"]/td/input/@onclick'
        next_page_number = response.xpath(xp).re(r'.*, (\d+)\)')
        if next_page_number:
            next_page_number = int(next_page_number[0]) + 1
            next_url = AJAX_SEARCH % next_page_number
            yield scrapy.Request(next_url, self.parse_catalog)

    def _parse_catalog_item(self, response):
        manga = response.meta['manga']
        # Name
        xp = '//h1[@class="ipsType_pagetitle"]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//td[contains(text(),"%s")]/following-sibling::td/.//text()'
        manga['alt_name'] = response.xpath(xp % 'Alt Names:').extract()
        # Year of release
        manga['release'] = None
        # Author
        manga['author'] = response.xpath(xp % 'Author:').extract()
        # Artist
        manga['artist'] = response.xpath(xp % 'Artist:').extract()
        # Reading direction
        manga['reading_direction'] = 'LR'
        # Status
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Genres
        manga['genres'] = response.xpath(xp % 'Genres:').extract()
        # Description
        manga['description'] = response.xpath(xp % 'Description:').extract()
        # Cover image
        xp = '//div[@class="ipsBox"]/div/div/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()
        # URL
        manga['url'] = response.url

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//tr[contains(@class,"chapter_row")]'
        for line in response.xpath(xp):
            issue = Issue()
            # Name
            xp = './td[1]/a/text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            issue['number'] = line.xpath(xp).re(r'Ch.(\d+)')
            # language
            xp = './td[2]/div/@title'
            issue['language'] = line.xpath(xp).extract()
            # Added
            # xp =
            # issue['added'] = line.xpath(xp).extract()
            # URL
            xp = './td[1]/a/@href'
            issue['url'] = line.xpath(xp).extract()
            manga['issues'].append(issue)
        yield manga

    def parse_lasts(self, since):
        pass

    def parse_manga(self, response, manga, issue):
        xp = '//select[@id="page_select"]/option/@value'
        for number, url in enumerate(response.xpath(xp).extract()):
            meta = (('manga', manga),
                    ('issue', issue),
                    ('number', number + 1),)
            yield scrapy.Request(url, self._parse_page, meta=meta)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//img[@id="comic_page"]/@src'
        url = response.xpath(xp).extract()
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=[urljoin(response.url, url[0])]
        )
        return issue_page
