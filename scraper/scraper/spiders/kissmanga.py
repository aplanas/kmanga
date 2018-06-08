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

from spidermonkey import Spidermonkey

from scraper.items import Genres, Manga, Issue, IssuePage
from .mangaspider import MangaSpider


class KissManga(MangaSpider):
    name = 'kissmanga'
    allowed_domains = ['kissmanga.com']
    cloudflare = True

    def get_genres_url(self):
        return 'http://kissmanga.com/AdvanceSearch'

    def get_catalog_url(self):
        return 'http://kissmanga.com/MangaList'

    def get_latest_url(self, until):
        return 'http://kissmanga.com'

    def parse_genres(self, response):
        """Generate the list of genres.

        @url http://kissmanga.com/AdvanceSearch
        @returns items 1
        @returns request 0
        @scrapes names
        """

        xp = '//a[@name="aGenre"]/text()'
        genres = Genres()
        genres['names'] = response.xpath(xp).extract()
        return genres

    def parse_catalog(self, response):
        """Generate the catalog (list of mangas) of the site.

        @url http://kissmanga.com/MangaList?page=200
        @returns items 0
        @returns request 25 60
        """

        xp = '//table[@class="listing"]/tr/td[1]'
        for item in response.xpath(xp):
            manga = Manga()
            # URL
            xp = 'a/@href'
            manga['url'] = response.urljoin(item.xpath(xp).extract_first())
            meta = {'manga': manga}
            yield response.follow(manga['url'], self.parse_collection,
                                  meta=meta)

        # Next page
        xp = '//ul[@class="pager"]/li/a[contains(., "Next")]/@href'
        next_url = response.xpath(xp).extract_first()
        if next_url:
            yield response.follow(next_url, self.parse_catalog)

    def parse_collection(self, response, manga=None):
        """Generate the list of issues for a manga

        @url http://kissmanga.com/Manga/Naruto
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
        # Reading direction
        manga['reading_direction'] = 'RL'
        # Genres
        manga['genres'] = response.xpath(xp % 'Genres:').extract()
        # Status
        xp = '//span[@class="info" and contains(text(), "%s")]' \
             '/following-sibling::text()[1]'
        manga['status'] = response.xpath(xp % 'Status:').extract()
        # Rank
        manga['rank'] = response.xpath(xp % 'Views:').re(r'(\d+).')
        # Rank order
        manga['rank_order'] = 'DESC'
        # Description
        xp = '//p[span[@class="info" and contains(text(), "%s")]]'\
             '/following-sibling::p[1]/text()'
        manga['description'] = response.xpath(xp % 'Summary:').extract()
        # Cover image
        xp = '//div[@id="rightside"]//img/@src'
        url = response.xpath(xp).extract_first()
        manga['image_urls'] = [response.urljoin(url)]

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
            # Some examples that this regex needs to address
            #   1/11 Vol.003 Ch.009.006: Omake 004-koma
            #   21st Century Boys 014
            #   Mob Psycho 100 Ch.099.001: Mob
            #   Mob Psycho 100 Ch.098.002
            #   Fantastic World Vol.001 Ch.002
            #   Black Clover 118 - Mage X
            #   Black Clover 099: Family
            xp = './/a/text()'
            number = line.xpath(xp).re(
                r'(?:[Cc]h.|[Ee]p.|[Cc]haper|[Pp]art.)(\d[.\d]+)'
                r'|(\d[.\d]+)[ :-]+'
                r'|(\d[.\d]+)$')
            issue['number'] = number
            # Order
            issue['order'] = len(lines) - len(manga['issues'])
            # Release
            xp = './td[2]/text()'
            issue['release'] = line.xpath(xp).re(r'\d{1,2}/\d{1,2}/\d{4}')
            # URL
            xp = './/a/@href'
            url = line.xpath(xp).extract_first()
            issue['url'] = response.urljoin(url)
            manga['issues'].append(issue)
        return manga

    def parse_latest(self, response, until=None):
        """Generate the list of new mangas until a date

        @url http://kissmanga.com/
        @returns items 0
        @returns request 25 50
        """

        if not until:
            if 'until' in response.meta:
                until = response.meta['until']
            else:
                until = date.today()

        # Get all manga's URL from the same page and update it via
        # `parse_collection`
        xp = '//div[@class="items"]//a/@href'
        for url in response.xpath(xp).extract():
            url = response.urljoin(url)
            manga = Manga(url=url)
            meta = {'manga': manga}
            yield response.follow(url, self.parse_collection, meta=meta)

        # XXX TODO - we ignore the `until` date, and make a full parse
        # of the initial scroll panel (that contains old entries)

    def parse_manga(self, response, manga, issue):
        # Collect the JavaScript resources.  We need to chain the
        # requests to fetch the assets, to avoid lost of information
        # in the `meta` (with the filter on), or loops and double send
        # of issues (with the filter off)
        meta = {
            'url': response.url,
            'manga': manga,
            'issue': issue,
        }
        return response.follow('/Scripts/ca.js',
                               self._collect_asset_ca, meta=meta)

    def _collect_asset_ca(self, response):
        meta = response.meta
        meta['ca'] = response.body
        return response.follow('/Scripts/lo.js',
                               self._collect_asset_lo, meta=meta)

    def _collect_asset_lo(self, response):
        meta = response.meta
        meta['lo'] = response.body
        return response.follow(meta['url'], self._parse_manga,
                               dont_filter=True, meta=meta)

    def _parse_manga(self, response):
        issue_pages = []
        images = self._unencrypt_images(response)

        manga = response.meta['manga']
        issue = response.meta['issue']

        for number, url in enumerate(images):
            issue_page = IssuePage(
                manga=manga,
                issue=issue,
                number=number + 1,
                image_urls=[url]
            )
            issue_pages.append(issue_page)
        return issue_pages

    def _unencrypt_images(self, response):
        """Build the JavaScript progran to unencrypt the image URLs."""
        xp = '//script'
        # Get the scripts that will build the program to unencrypt the
        # URLs for the images
        ca = response.meta['ca']
        lo = response.meta['lo']
        # Get the list of keys
        keys = response.xpath(xp).re(r'var _0x.*')

        # Generate the JavaScript program to show the URLs
        wrapKA = response.xpath(xp).re(r'lstImages.push\((.*)\);')
        wrapKA = '\n'.join(('print(%s);' % line for line in wrapKA))

        code = [ca, lo]
        code.extend(keys)
        proc = Spidermonkey(early_script_file='-', code=code)
        stdout, stderr = proc.communicate(wrapKA)
        return stdout.strip().split('\n')
