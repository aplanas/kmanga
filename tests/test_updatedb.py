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

import datetime
import unittest

import django
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
import scraper.items
from scraper.pipelines import UpdateDBPipeline

from main.models import Source, SourceLanguage, Genre, Manga


# Configure Django to run tests outside the manage.py tool
django.setup()
setup_test_environment()


class Spider(object):
    pass


class TestUpdateDBPipeline(unittest.TestCase):

    def setUp(self):
        self.dr = DiscoverRunner()
        self.old_config = self.dr.setup_databases()

        self.updatedb = UpdateDBPipeline(
            images_store='tests/fixtures/images',
            settings=None)
        source = Source.objects.create(
            name='source',
            spider='spider',
            url='http://example.com'
        )
        SourceLanguage.objects.create(
            language='EN',
            source=source
        )
        self.spider = Spider()
        self.spider.name = 'Spider'

    def tearDown(self):
        self.dr.teardown_databases(self.old_config)

    def test_update_relation(self):
        source = Source.objects.get(spider='spider')

        names = ['g1', 'g2', 'g3']
        items = [{'name': i} for i in names]
        n, u, d = self.updatedb._update_relation(source, 'genre_set',
                                                 'name', items,
                                                 self.updatedb._update_name)
        self.assertEqual(n, set(names))
        self.assertEqual(u, set())
        self.assertEqual(d, set())

        names = ['g2', 'g3', 'g4']
        items = [{'name': i} for i in names]
        n, u, d = self.updatedb._update_relation(source, 'genre_set',
                                                 'name', items,
                                                 self.updatedb._update_name)
        self.assertEqual(n, set(['g4']))
        self.assertEqual(u, set(['g2', 'g3']))
        self.assertEqual(d, set(['g1']))

    def test_update_genres(self):
        names = ['g1', 'g2', 'g3']
        genres = scraper.items.Genres(
            names=names
        )
        self.updatedb.update_genres(genres, self.spider)
        self.assertEqual({o.name for o in Genre.objects.all()}, set(names))

        names = ['g2', 'g3', 'g4']
        genres = scraper.items.Genres(
            names=names
        )
        self.updatedb.update_genres(genres, self.spider)
        self.assertEqual({o.name for o in Genre.objects.all()}, set(names))

    def test_update_collection(self):
        names = ['g1', 'g2', 'g3']
        genres = scraper.items.Genres(
            names=names
        )
        self.updatedb.update_genres(genres, self.spider)

        manga = scraper.items.Manga(
            name='Manga1',
            alt_name=['Manga1', 'MangaA'],
            author='Author',
            artist='Artist',
            reading_direction='LR',
            status='ONGOING',
            genres=['g1', 'g2'],
            rank=1,
            rank_order='ASC',
            description='Description',
            image_urls=['http://manga1.org/images/height-large.jpg'],
            images=['height-large.jpg'],
            issues=[
                scraper.items.Issue(
                    name='issue1',
                    number=1,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=1),
                    url='http://manga1.org/issue1'),
                scraper.items.Issue(
                    name='issue2',
                    number=2,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=2),
                    url='http://manga1.org/issue2'),
            ],
            url='http://manga1.org')
        self.updatedb.update_collection(manga, self.spider)
        self.assertEqual(len(Manga.objects.all()), 1)
        m = Manga.objects.all()[0]
        self.assertEqual(m.name, 'Manga1')
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('Manga1', 'MangaA')))
        self.assertEqual(m.author, 'Author')
        self.assertEqual(m.artist, 'Artist')
        self.assertEqual(m.reading_direction, 'LR')
        self.assertEqual(m.status, 'ONGOING')
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g2')))
        self.assertEqual(m.rank, None)
        self.assertEqual(m.rank_order, 'ASC')
        self.assertEqual(m.description, 'Description')

        # Remove the image
        m.cover.delete()
