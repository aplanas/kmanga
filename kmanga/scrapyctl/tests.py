from __future__ import absolute_import
from datetime import date

from django.core.management.base import CommandError
from django.test import mock
from django.test import TestCase

from core.models import Manga
from core.models import Source
from registration.models import UserProfile
from scrapyctl.management.commands.scrapy import Command
from scrapyctl.scrapyctl import ScrapyCtl


class CommandTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def setUp(self):
        self.scrapy = ScrapyCtl('ERROR')
        self.command = Command()
        self.command.stdout = mock.MagicMock()
        self.all_spiders = ['batoto', 'mangareader',
                            'submanga', 'mangafox']

    def test_get_spiders(self):
        """Test recovering the list of scrapy spiders."""
        # This asks directly to Scrapy, not the database
        spiders = self.command._get_spiders(self.scrapy, 'all')
        self.assertEqual(spiders, self.all_spiders)
        spiders = self.command._get_spiders(self.scrapy, 'batoto')
        self.assertEqual(spiders, ['batoto'])

        with self.assertRaises(CommandError):
            self.command._get_spiders(self.scrapy, 'missing')

    def test_get_manga(self):
        """Test recovering the manga instance from a spider."""
        with self.assertRaises(CommandError):
            self.command._get_manga(['source1', 'source2'])

        with self.assertRaises(CommandError):
            self.command._get_manga(['source1'])

        with self.assertRaises(CommandError):
            self.command._get_manga(['source1'], manga='missing')

        # Duplicate a Manga
        source = Source.objects.get(name='Source 1')
        manga = source.manga_set.get(name='Manga 1')
        manga.id = None
        manga.url += '/different-url'
        manga.save()
        with self.assertRaises(CommandError):
            self.command._get_manga(['source1'], manga='Manga 1')
        manga.delete()

        manga1 = self.command._get_manga(['source1'], manga='Manga 1')
        manga2 = self.command._get_manga(['source1'],
                                         url='http://source1.com/manga1')
        self.assertEqual(manga1, manga2)

    def test_get_issues(self):
        """Test recovering issues list from a manga."""
        manga1 = Manga.objects.get(name='Manga 1')
        manga3 = Manga.objects.get(name='Manga 3')

        with self.assertRaises(CommandError):
            self.command._get_issues(manga1, issues='all')

        with self.assertRaises(CommandError):
            self.command._get_issues(manga1, lang='EN')

        with self.assertRaises(CommandError):
            self.command._get_issues(manga1, issues='all', lang='DE')

        self.assertEqual(self.command._get_issues(manga3,
                                                  issues='all').count(), 5)
        self.assertEqual(
            self.command._get_issues(manga1,
                                     issues='all',
                                     lang='ES').count(), 1)
        self.assertEqual(self.command._get_issues(manga1,
                                                  issues='all',
                                                  lang='EN').count(), 5)

        self.assertEqual(self.command._get_issues(manga1,
                                                  issues='1-5',
                                                  lang='EN').count(), 5)

        self.assertEqual(self.command._get_issues(manga1,
                                                  issues='1,2,3-5',
                                                  lang='EN').count(), 5)

        self.assertEqual(self.command._get_issues(manga1,
                                                  issues='2,1,3',
                                                  lang='EN').count(), 3)
        with self.assertRaises(CommandError):
            self.command._get_issues(manga1, issues='5-1', lang='EN')

        url = 'http://source1.com/manga1/issue1'
        self.assertEqual(self.command._get_issues(manga1,
                                                  issues='1',
                                                  lang='EN').count(),
                         self.command._get_issues(manga1,
                                                  url=url,
                                                  lang='EN').count())

    def test_handle_no_params(self):
        """Test handle when there are not parameters."""
        with self.assertRaises(CommandError):
            self.command.handle()

    def test_handle_wrong_param(self):
        """Test handle when the parameter is wrong."""
        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
        }

        with self.assertRaises(CommandError):
            self.command.handle('bad-parameter', **options)

    @mock.patch.object(Command, 'list_spiders')
    def test_handle_list(self, list_spiders):
        """Test the `list` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
        }

        c = Command()
        c.handle('list', **options)
        list_spiders.assert_called_once_with(self.all_spiders)

    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_genres(self, scrapyctl):
        """Test the `update-genres` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
        }

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle('update-genres', **options)
        scrapyctl.update_genres.assert_called_once_with(self.all_spiders,
                                                        False)

    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_catalog(self, scrapyctl):
        """Test the `update-catalog` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
        }

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle('update-catalog', **options)
        scrapyctl.update_catalog.assert_called_once_with(self.all_spiders,
                                                         False)

    @mock.patch.object(Command, '_get_spiders')
    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_collection(self, scrapyctl, get_spiders):
        """Test the `update-collection` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'manga': 'Manga 1',
            'url': None,
        }

        scrapyctl.return_value = scrapyctl
        get_spiders.return_value = ['source1']
        c = Command()
        c.handle('update-collection', **options)
        scrapyctl.update_collection.assert_called_once_with(
            ['source1'], 'Manga 1', 'http://source1.com/manga1', False)

    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_latest(self, scrapyctl):
        """Test the `update-latest` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'until': '01-01-2015',
        }
        until = date(year=2015, month=1, day=1)

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle('update-latest', **options)
        scrapyctl.update_latest.assert_called_once_with(
            self.all_spiders, until, False)

        scrapyctl.reset_mock()

        options['until'] = until
        c = Command()
        c.handle('update-latest', **options)
        scrapyctl.update_latest.assert_called_once_with(
            self.all_spiders, until, False)

    @mock.patch.object(Command, 'search')
    def test_handle_search(self, search):
        """Test the `search` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'manga': 'Manga 1',
            'lang': 'EN',
            'details': False,
        }

        c = Command()
        c.handle('search', **options)
        search.assert_called_once_with(self.all_spiders, 'Manga 1',
                                       'EN', False)

    @mock.patch.object(Command, 'subscribe')
    @mock.patch.object(Command, '_get_spiders')
    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_subscribe(self, scrapyctl, get_spiders, subscribe):
        """Test the `subscribe` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'user': 'user1',
            'manga': 'Manga 1',
            'url': None,
            'lang': 'EN',
            'issues-per-day': 4,
        }

        manga = Manga.objects.get(name='Manga 1')

        scrapyctl.return_value = scrapyctl
        get_spiders.return_value = ['source1']
        c = Command()
        c.handle('subscribe', **options)
        subscribe.assert_called_once_with('user1', manga, 'EN', 4)

    @mock.patch.object(Command, 'send')
    @mock.patch.object(Command, 'subscribe')
    @mock.patch.object(Command, '_get_issues')
    @mock.patch.object(Command, '_get_spiders')
    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_send(self, scrapyctl, get_spiders, get_issues,
                         get_manga, send):
        """Test the `send` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'issues': [1, 2, 3],
            'manga': 'Manga 1',
            'url': None,
            'lang': 'EN',
            'from': 'from@example.com',
            'to': 'to@example.com',
            'do-not-send': False,
        }

        manga = Manga.objects.get(name='Manga 1')

        scrapyctl.return_value = scrapyctl
        get_spiders.return_value = ['source1']
        get_issues.return_value = ['issues']
        get_manga.return_value = ['manga']
        c = Command()
        c.handle('send', **options)
        send.assert_called_once_with(scrapyctl, ['source1'], manga,
                                     ['issues'], 'from@example.com',
                                     'to@example.com', False)

    @mock.patch.object(Command, 'sendsub')
    @mock.patch.object(Command, 'prepare_sendsub')
    @mock.patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_sendsub(self, scrapyctl, prepare_sendsub, sendsub):
        """Test the `sendsub` handle method."""

        options = {
            'spiders': 'all',
            'loglevel': 'ERROR',
            'dry-run': False,
            'user': 'user1',
            'do-not-send': False,
        }

        user_profile = UserProfile.objects.get(user__username='user1')

        scrapyctl.return_value = scrapyctl
        c = Command()
        c.handle('sendsub', **options)
        prepare_sendsub.assert_called_once_with(scrapyctl, user_profile,
                                                False)
        sendsub.assert_called_once_with(scrapyctl)

        sendsub.reset_mock()
        user_profiles = UserProfile.objects.all()

        options['user'] = None
        c = Command()
        c.handle('sendsub', **options)
        for user_profile in user_profiles:
            prepare_sendsub.assert_any_call(scrapyctl, user_profile, False)
        sendsub.assert_called_once_with(scrapyctl)
