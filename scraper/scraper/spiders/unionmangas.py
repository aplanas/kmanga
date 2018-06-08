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

from scraper.items import Genres, Manga, Issue, IssuePage
from .mangaspider import MangaSpider


class UnionMangas(MangaSpider):
    name = 'unionmangas'
    allowed_domains = ['unionmangas.site']
    vhost_ip = '85.93.89.57'

    def get_genres_url(self):
        return 'http://unionmangas.site/mangas'

    def get_catalog_url(self):
        return 'http://unionmangas.site/mangas/a-z'

    def get_collection_url(self, manga):
        return 'http://unionmangas.site/manga/%s' % manga

    def get_latest_url(self, until):
        return 'http://unionmangas.site/'

    def get_manga_url(self, manga, issue):
        return 'http://unionmangas.site/%s/%s' % (manga, issue)

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://unionmangas.site/mangas
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//ul[@class="dropdown-menu"]/li/a/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://unionmangas.site/mangas/a-z/10
        @returns items 0
        @returns request 1 50
        """

        xp = '//div[contains(@class, "bloco-manga")]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = 'a[2]/@href'
            manga['url'] = item.xpath(xp).extract_first()
            # Rank
            xp = 'div[@style="display: none"]/text()'
            manga['rank'] = item.xpath(xp).re(r'([\d.]+) views')
            # Rank order
            manga['rank_order'] = 'DESC'
            meta = {'manga': manga}
            yield response.follow(manga['url'], self.parse_collection,
                                  meta=meta)

        # Next page
        xp = '//ul[@class="pagination"]/li/a[contains(., "Next")]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://unionmangas.site/manga/bleach
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
        xp = '//div[@class="col-md-12"]/h2/text()'
        manga['name'] = response.xpath(xp).extract_first()
        # Alternate name
        manga['alt_name'] = manga['name']
        # Author
        xp = '//label[contains(text(), "%s")]/following-sibling::text()'
        manga['author'] = response.xpath(xp % 'Autor:').extract()
        # Artist
        manga['artist'] = response.xpath(xp % 'Artista:').extract()
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Status (Ativo / Completo)
        xp = '//label[contains(text(), "Status:")]' \
             '/following-sibling::span/text()'
        manga['status'] = response.xpath(xp).extract()
        # Genres
        xp = '//label[contains(text(), "Gênero(s):")]' \
             '/following-sibling::a/text()'
        manga['genres'] = response.xpath(xp).extract()
        # Description
        xp = '//div[@class="panel-body"]/text()'
        manga['description'] = response.xpath(xp).extract()
        # Cover image
        xp = '//img[@class="img-thumbnail"]/@src'
        manga['image_urls'] = response.xpath(xp).extract()

        # Parse the manga issues list
        manga['issues'] = []
        xp = '//div[@class="col-xs-6 col-md-6"]'
        lines = response.xpath(xp)
        for line in lines:
            issue = Issue(language='PT')
            # Name
            xp = 'a/text()'
            issue['name'] = line.xpath(xp).extract()
            # Number
            issue['number'] = line.xpath(xp).re(r'Cap. ([.\d]+)$')
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = 'span/text()'
            issue['release'] = line.xpath(xp).re(r'\d{2}/\d{2}/\d{4}')
            # URL
            xp = 'a/@href'
            issue['url'] = line.xpath(xp).extract()
            manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://unionmangas.site/
        @returns items 0
        @returns request 10 100
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//a[@class="link-titulo"]/@href'
        for url in response.xpath(xp).extract():
            manga = Manga(url=url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

    def parse_manga(self, response, manga, issue):
        xp = '//img/@src'
        for number, url in enumerate(response.xpath(xp).extract()):
            url = response.urljoin(url)
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number+1,
                image_urls=[url]
            )
            yield issue_page
