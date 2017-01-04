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
from scraper.pipelines import convert_to_number
from scraper.items import Genres, Manga, Issue, IssuePage

from .mangaspider import MangaSpider


AJAX_SEARCH = 'http://bato.to/search_ajax?p=%d'


class Batoto(MangaSpider):
    name = 'batoto'
    allowed_domains = ['bato.to']

    form_xpath = '//form[@id="login"]'
    username_field = 'ips_username'
    password_field = 'ips_password'
    login_check = {
        MangaSpider.LOGIN_ERR: 'Username or password incorrect.'
    }

    def get_login_url(self):
        login = 'app=core&module=global&section=login'
        return 'https://bato.to/forums/index.php?%s' % login

    def get_genres_url(self):
        return 'http://bato.to/search?advanced=1'

    def get_catalog_url(self):
        return AJAX_SEARCH % 1

    def get_latest_url(self, until):
        return 'http://bato.to/'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://bato.to/search?advanced=1
        @returns items 1 1
        @returns request 0 0
        @scrapes names
        """

        xp = '//div[@class="genre_buttons"]//text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://bato.to/search_ajax?p=200
        @returns items 0 0
        @returns request 30 40
        """

        def mb(x, default=0.0):
            return x[0] if x else default

        xp = '//tr[not(@class) and not(@id)]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = './td[1]/strong/a/@href'
            manga['url'] = item.xpath(xp).extract()
            # In Batoto there is not rank, but a combination of
            # rating, viewers and followers.
            xp = './td[3]/div/@title'
            rating = float(mb(item.xpath(xp).re(r'([.\d]+)/5')))
            xp = './td[4]/text()'
            viewers = convert_to_number(item.xpath(xp).extract()[0])
            xp = './td[5]/text()'
            followers = convert_to_number(item.xpath(xp).extract()[0])
            manga['rank'] = (rating + 0.1) * viewers * followers
            manga['rank_order'] = 'DESC'
            # URL Hack to avoid a redirection. This is used because
            # the download_delay is also added to the redirector.
            # This makes the spider a bit faster, but we still needs
            # to update the real URL in the `parse_collection` side.
            url = manga['url'][0].split('_/')[-1]
            url = 'http://bato.to/comic/_/comics/%s' % url
            # Also use this URL in the Item to avoid duplicates.
            manga['url'] = url
            meta = {'manga': manga}
            request = scrapy.Request(url, self.parse_collection, meta=meta)
            yield request

        # Next page
        xp = '//tr[@id="show_more_row"]/td/input/@onclick'
        next_page_number = response.xpath(xp).re(r'.*, (\d+)\)')
        if next_page_number:
            next_page_number = int(next_page_number[0]) + 1
            next_url = AJAX_SEARCH % next_page_number
            yield scrapy.Request(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://bato.to/comic/_/comics/angel-densetsu-r460
        @returns items 1 1
        @returns request 0 0
        @scrapes url name alt_name author artist reading_direction
        @scrapes status genres description issues
        """

        if 'manga' in response.meta:
            manga = response.meta['manga']
        else:
            manga = Manga(url=response.url)

        # URL
        # Batoto can have different URLs for comics (_/comics/,
        # _/sp/), so here we update the manga with the real one.
        manga['url'] = response.url
        # Name
        xp = '//h1[@class="ipsType_pagetitle"]/text()'
        manga['name'] = response.xpath(xp).extract()
        # Alternate name
        xp = '//td[contains(text(),"%s")]/following-sibling::td/*/text()'
        manga['alt_name'] = response.xpath(xp % 'Alt Names:').re(r'([^,;]+)')
        # Author
        manga['author'] = response.xpath(xp % 'Author:').extract()
        # Artist
        manga['artist'] = response.xpath(xp % 'Artist:').extract()
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status
        xp = '//td[contains(text(),"%s")]/following-sibling::td/text()'
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Genres
        xp = '//td[contains(text(),"%s")]/following-sibling::td/a/span/text()'
        manga['genres'] = response.xpath(xp % 'Genres:').extract()
        # Description
        xp = '//td[contains(text(),"%s")]/following-sibling::td/text()'
        manga['description'] = response.xpath(xp % 'Description:').extract()
        # Cover image
        xp = '//div[@class="ipsBox"]/div/div/img/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//tr[contains(@class,"chapter_row")' \
             ' and not(contains(@class,"chapter_row_expand"))]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue()
            # Name
            xp = './td[1]/a/text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            issue['number'] = line.xpath(xp).re(
                r'Ch.(?:Story )?([.\d]+)')
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Language
            xp = './td[2]/div/@title'
            issue['language'] = line.xpath(xp).extract()
            # Release
            xp = './td[5]/text()'
            issue['release'] = line.xpath(xp).extract()
            # URL
            xp = './td[1]/a/@href'
            url = line.xpath(xp).extract()[0]
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)
        yield manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://bato.to
        @returns items 1 100
        @returns request 0 1
        @scrapes url name issues
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        xp = './/tr[contains(@class, "row")]'
        last_row, manga = None, None
        for update in response.xpath(xp):
            row = update.xpath('@class').extract()[0].split()[0]
            if row != last_row:
                if manga:
                    yield manga
                manga = Manga(issues=[])
                # Name
                xp = 'td[2]/a[2]/text()'
                manga['name'] = update.xpath(xp).extract()
                # URL
                xp = 'td[2]/a[2]/@href'
                manga['url'] = update.xpath(xp).extract()
            else:
                issue = Issue()
                # Name
                xp = './/td/a[img/@style="vertical-align:middle;"]/text()'
                issue['name'] = update.xpath(xp).extract()
                # Number
                issue['number'] = update.xpath(xp).re(
                    r'Ch.(?:Story )?([.\d]+)')
                # Order
                # This is only an estimation for now
                issue['order'] = issue['number']
                # Language
                xp = './/td/div/@title'
                issue['language'] = update.xpath(xp).extract()
                # Release
                xp = './/td[last()]/text()'
                issue['release'] = update.xpath(xp).extract()
                # URL
                xp = './/td/a[img/@style="vertical-align:middle;"]/@href'
                url = update.xpath(xp).extract()[0]
                issue['url'] = response.urljoin(url)

                # Check if is a new update
                update_date = convert_to_date(issue['release'][0].strip())
                if update_date < until:
                    return

                manga['issues'].append(issue)
            last_row = row

        # Return the last manga
        if manga:
            yield manga

        # Next page
        xp = '//a[@title="Older Releases"]/@href'
        next_url = response.xpath(xp).extract()
        if next_url:
            next_url = response.urljoin(next_url[0])
            meta = {'until': until}
            yield scrapy.Request(next_url, self.parse_latest, meta=meta)

    def parse_manga(self, response, manga, issue):
        # Get the URL from response.request instead for response, to
        # use the unormalized one
        referer_url = response.request.url
        areader_id = referer_url.split('#')[1]
        partial_url = '/areader?id=%s&p=%%s&supress_webtoon=t' % areader_id
        partial_url = response.urljoin(partial_url)

        # Get the first AJAX answer to recover the list of pages
        url = partial_url % 1
        meta = {
            'manga': manga,
            'issue': issue,
            'partial_url': partial_url,
            'referer_url': referer_url,
        }
        return scrapy.Request(url, self._parse_manga, meta=meta,
                              dont_filter=True)

    def _parse_manga(self, response):
        partial_url = response.meta['partial_url']

        # This select is used to times (with the same ID), we get only
        # the first one
        xp = '(//select[@id="page_select"])[1]/option/@value'
        for number, _ in enumerate(response.xpath(xp).extract()):
            url = partial_url % (number + 1)
            meta = {
                'manga': response.meta['manga'],
                'issue': response.meta['issue'],
                'number': number + 1,
            }
            headers = {
                'Referer': response.meta['referer_url']
            }
            yield scrapy.Request(url, self._parse_page, meta=meta,
                                 headers=headers)

    def _parse_page(self, response):
        manga = response.meta['manga']
        issue = response.meta['issue']
        number = response.meta['number']

        xp = '//div[@id="full_image"]/div/img/@src'
        url = response.xpath(xp).extract()
        issue_page = IssuePage(
            manga=manga,
            issue=issue,
            number=number,
            image_urls=url
        )
        return issue_page
