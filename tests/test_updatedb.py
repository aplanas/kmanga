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

import datetime
import unittest

import django
from django.test.utils import setup_test_environment
from django.test.runner import DiscoverRunner
import scraper.items
from scraper.pipelines import UpdateDBPipeline

from core.models import Source, SourceLanguage, Genre, Manga


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
            images_store='tests/fixtures/images')
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
            status='O',
            genres=['g1', 'g2'],
            rank=1,
            rank_order='ASC',
            description='Description',
            image_urls=['http://manga1.org/images/height-large.jpg'],
            images=[{
                'url': 'http://manga1.org/images/height-large.jpg',
                'path': 'height-large.jpg',
                'checksum': None
            }],
            issues=[
                scraper.items.Issue(
                    name='issue1',
                    number='1',
                    order=1,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=1),
                    url='http://manga1.org/issue1'),
                scraper.items.Issue(
                    name='issue2',
                    number='2',
                    order=2,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=2),
                    url='http://manga1.org/issue2'),
            ],
            url='http://manga1.org')
        self.updatedb.update_collection(manga, self.spider)
        self.assertEqual(len(Manga.objects.all()), 1)
        m = Manga.objects.all()[0]
        self.assertEqual(m.name, 'Manga1')
        self.assertEqual(len(m.altname_set.all()), 2)
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('Manga1', 'MangaA')))
        self.assertEqual(m.author, 'Author')
        self.assertEqual(m.artist, 'Artist')
        self.assertEqual(m.reading_direction, 'LR')
        self.assertEqual(m.status, 'O')
        self.assertEqual(len(m.genres.all()), 2)
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g2')))
        self.assertEqual(m.rank, 1.0)
        self.assertEqual(m.rank_order, 'ASC')
        self.assertEqual(m.description, 'Description')

        self.assertEqual(len(m.issue_set.all()), 2)

        i = m.issue_set.get(name='issue1')
        self.assertEqual(i.name, 'issue1')
        self.assertEqual(i.number, '1')
        self.assertEqual(i.order, 1)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=1))
        self.assertEqual(i.url, 'http://manga1.org/issue1')

        i = m.issue_set.get(name='issue2')
        self.assertEqual(i.name, 'issue2')
        self.assertEqual(i.number, '2')
        self.assertEqual(i.order, 2)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=2))
        self.assertEqual(i.url, 'http://manga1.org/issue2')

        # Remove the image
        m.cover.delete()

    def test_update2_collection(self):
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
            status='O',
            genres=['g1', 'g2'],
            rank=1,
            rank_order='ASC',
            description='Description',
            image_urls=['http://manga1.org/images/height-large.jpg'],
            images=[{
                'url': 'http://manga1.org/images/height-large.jpg',
                'path': 'height-large.jpg',
                'checksum': None
            }],
            issues=[
                scraper.items.Issue(
                    name='issue1',
                    number='1',
                    order=1,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=1),
                    url='http://manga1.org/issue1'),
                scraper.items.Issue(
                    name='issue2',
                    number='2',
                    order=2,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=2),
                    url='http://manga1.org/issue2'),
            ],
            url='http://manga1.org')
        self.updatedb.update_collection(manga, self.spider)

        # Add a new alt_name
        manga['alt_name'].append('MangaB')
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.altname_set.all()), 3)
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('Manga1', 'MangaA', 'MangaB')))

        # Remove an alt_name
        del manga['alt_name'][0]
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.altname_set.all()), 2)
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('MangaA', 'MangaB')))

        # Change author
        manga['author'] = 'Another Author'
        self.updatedb.update_collection(manga, self.spider)

        # Change status
        manga['status'] = 'C'
        self.updatedb.update_collection(manga, self.spider)

        # Add a new genre
        manga['genres'].append('g3')
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.genres.all()), 3)
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g2', 'g3')))

        # Remove a genre
        del manga['genres'][1]
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.genres.all()), 2)
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g3')))

        # Add a new issue
        manga['issues'].append(
            scraper.items.Issue(
                name='issue3',
                number='3',
                order=3,
                language='EN',
                release=datetime.date(year=2014, month=1, day=3),
                url='http://manga1.org/issue3')
        )
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.issue_set.all()), 3)

        # Remove an issue
        del manga['issues'][0]
        self.updatedb.update_collection(manga, self.spider)
        m = Manga.objects.all()[0]
        self.assertEqual(len(m.issue_set.all()), 2)

        # Check the final result
        self.assertEqual(len(Manga.objects.all()), 1)
        m = Manga.objects.all()[0]
        self.assertEqual(m.name, 'Manga1')
        self.assertEqual(len(m.altname_set.all()), 2)
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('MangaA', 'MangaB')))
        self.assertEqual(m.author, 'Another Author')
        self.assertEqual(m.artist, 'Artist')
        self.assertEqual(m.reading_direction, 'LR')
        self.assertEqual(m.status, 'C')
        self.assertEqual(len(m.genres.all()), 2)
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g3')))
        self.assertEqual(m.rank, 1.0)
        self.assertEqual(m.rank_order, 'ASC')
        self.assertEqual(m.description, 'Description')

        self.assertEqual(len(m.issue_set.all()), 2)

        i = m.issue_set.get(name='issue2')
        self.assertEqual(i.name, 'issue2')
        self.assertEqual(i.number, '2')
        self.assertEqual(i.order, 2)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=2))
        self.assertEqual(i.url, 'http://manga1.org/issue2')

        i = m.issue_set.get(name='issue3')
        self.assertEqual(i.name, 'issue3')
        self.assertEqual(i.number, '3')
        self.assertEqual(i.order, 3)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=3))
        self.assertEqual(i.url, 'http://manga1.org/issue3')

        # Remove the image
        m.cover.delete()

    def test_update_latest(self):
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
            status='O',
            genres=['g1', 'g2'],
            rank=1,
            rank_order='ASC',
            description='Description',
            image_urls=['http://manga1.org/images/height-large.jpg'],
            images=[{
                'url': 'http://manga1.org/images/height-large.jpg',
                'path': 'height-large.jpg',
                'checksum': None
            }],
            issues=[
                scraper.items.Issue(
                    name='issue1',
                    number='1',
                    order=1,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=1),
                    url='http://manga1.org/issue1'),
                scraper.items.Issue(
                    name='issue2',
                    number='2',
                    order=2,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=2),
                    url='http://manga1.org/issue2'),
            ],
            url='http://manga1.org')
        self.updatedb.update_collection(manga, self.spider)

        manga = scraper.items.Manga(
            name='Manga1',
            issues=[
                scraper.items.Issue(
                    name='issue3',
                    number='3',
                    order=3,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=3),
                    url='http://manga1.org/issue3'),
                scraper.items.Issue(
                    name='issue4',
                    number='4',
                    order=4,
                    language='EN',
                    release=datetime.date(year=2014, month=1, day=4),
                    url='http://manga1.org/issue4'),
            ],
            url='http://manga1.org')
        self.updatedb.update_latest(manga, self.spider)
        self.assertEqual(len(Manga.objects.all()), 1)
        m = Manga.objects.all()[0]
        self.assertEqual(m.name, 'Manga1')
        self.assertEqual(len(m.altname_set.all()), 2)
        self.assertEqual({o.name for o in m.altname_set.all()},
                         set(('Manga1', 'MangaA')))
        self.assertEqual(m.author, 'Author')
        self.assertEqual(m.artist, 'Artist')
        self.assertEqual(m.reading_direction, 'LR')
        self.assertEqual(m.status, 'O')
        self.assertEqual(len(m.genres.all()), 2)
        self.assertEqual({o.name for o in m.genres.all()},
                         set(('g1', 'g2')))
        self.assertEqual(m.rank, 1.0)
        self.assertEqual(m.rank_order, 'ASC')
        self.assertEqual(m.description, 'Description')

        self.assertEqual(len(m.issue_set.all()), 4)

        i = m.issue_set.get(name='issue1')
        self.assertEqual(i.name, 'issue1')
        self.assertEqual(i.number, '1')
        self.assertEqual(i.order, 1)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=1))
        self.assertEqual(i.url, 'http://manga1.org/issue1')

        i = m.issue_set.get(name='issue2')
        self.assertEqual(i.name, 'issue2')
        self.assertEqual(i.number, '2')
        self.assertEqual(i.order, 2)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=2))
        self.assertEqual(i.url, 'http://manga1.org/issue2')

        i = m.issue_set.get(name='issue3')
        self.assertEqual(i.name, 'issue3')
        self.assertEqual(i.number, '3')
        self.assertEqual(i.order, 3)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=3))
        self.assertEqual(i.url, 'http://manga1.org/issue3')

        i = m.issue_set.get(name='issue4')
        self.assertEqual(i.name, 'issue4')
        self.assertEqual(i.number, '4')
        self.assertEqual(i.order, 4)
        self.assertEqual(i.language, 'EN')
        self.assertEqual(i.release, datetime.date(year=2014, month=1, day=4))
        self.assertEqual(i.url, 'http://manga1.org/issue4')

        # Remove the image
        m.cover.delete()
