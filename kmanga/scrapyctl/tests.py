from datetime import date
from unittest.mock import MagicMock
from unittest.mock import Mock
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import TestCase

from core.models import Manga
from core.models import Source
# from registration.models import UserProfile
from scrapyctl.management.commands.scrapy import Command
from scrapyctl.mobictl import MobiInfo
from scrapyctl.scrapyctl import ScrapyCtl


class CommandTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def setUp(self):
        self.scrapy = ScrapyCtl(accounts={}, loglevel='ERROR')
        self.command = Command()
        self.command.stdout = MagicMock()
        self.all_spiders = ['batoto', 'kissmanga', 'mangadex', 'mangafox',
                            'mangahere', 'mangareader', 'mangasee',
                            'unionmangas']

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
        manga.pk = None
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
        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
        }

        with self.assertRaises(CommandError):
            self.command.handle(command=None, **options)

    def test_handle_wrong_param(self):
        """Test handle when the parameter is wrong."""
        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
        }

        with self.assertRaises(CommandError):
            self.command.handle(command='bad-parameter', **options)

    @patch.object(Command, 'list_spiders')
    def test_handle_list(self, list_spiders):
        """Test the `list` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
        }

        c = Command()
        c.handle(command='list', **options)
        list_spiders.assert_called_once_with(self.all_spiders)

    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_genres(self, scrapyctl):
        """Test the `update-genres` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
        }

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle(command='update-genres', **options)
        scrapyctl.update_genres.assert_called_once_with(self.all_spiders,
                                                        False)

    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_catalog(self, scrapyctl):
        """Test the `update-catalog` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
        }

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle(command='update-catalog', **options)
        scrapyctl.update_catalog.assert_called_once_with(self.all_spiders,
                                                         False)

    @patch.object(Command, '_get_spiders')
    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_collection(self, scrapyctl, get_spiders):
        """Test the `update-collection` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
            'manga': 'Manga 1',
            'url': None,
        }

        scrapyctl.return_value = scrapyctl
        get_spiders.return_value = ['source1']
        c = Command()
        c.handle(command='update-collection', **options)
        scrapyctl.update_collection.assert_called_once_with(
            ['source1'], 'Manga 1', 'http://source1.com/manga1', False)

    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_update_latest(self, scrapyctl):
        """Test the `update-latest` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
            'until': '01-01-2015',
        }
        until = date(year=2015, month=1, day=1)

        scrapyctl.return_value = scrapyctl
        scrapyctl.spider_list.return_value = self.all_spiders
        c = Command()
        c.handle(command='update-latest', **options)
        scrapyctl.update_latest.assert_called_once_with(
            self.all_spiders, until, False)

        scrapyctl.reset_mock()

        options['until'] = until
        c = Command()
        c.handle(command='update-latest', **options)
        scrapyctl.update_latest.assert_called_once_with(
            self.all_spiders, until, False)

    @patch.object(Command, 'search')
    def test_handle_search(self, search):
        """Test the `search` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
            'manga': 'Manga 1',
            'lang': 'EN',
            'details': False,
        }

        c = Command()
        c.handle(command='search', **options)
        search.assert_called_once_with(self.all_spiders, 'Manga 1',
                                       'EN', False)

    @patch.object(Command, 'subscribe')
    @patch.object(Command, '_get_spiders')
    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_subscribe(self, scrapyctl, get_spiders, subscribe):
        """Test the `subscribe` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
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
        c.handle(command='subscribe', **options)
        subscribe.assert_called_once_with('user1', manga, 'EN', 4)

    @patch.object(Command, 'send')
    @patch.object(Command, '_get_manga')
    @patch.object(Command, '_get_issues')
    @patch.object(Command, '_get_user_profile')
    @patch.object(Command, '_get_spiders')
    @patch('scrapyctl.management.commands.scrapy.ScrapyCtl')
    def test_handle_send(self, scrapyctl, get_spiders, get_user_profile,
                         get_issues, get_manga, send):
        """Test the `send` handle method."""

        options = {
            'spiders': 'all',
            'accounts': [],
            'loglevel': 'ERROR',
            'dry_run': False,
            'issues': [1, 2, 3],
            'manga': 'Manga 1',
            'url': None,
            'lang': 'EN',
            'user': 'user1',
            'do-not-send': False,
        }

        get_spiders.return_value = ['source1']
        get_user_profile.return_value = ['user_profile']
        get_issues.return_value = ['issues']
        get_manga.return_value = ['manga']
        c = Command()
        c.handle(command='send', **options)
        send.assert_called_once_with(['issues'], ['user_profile'], {},
                                     options['loglevel'],
                                     options['do-not-send'])

    # XXX TODO - Split in different tests
    # @patch.object(Command, 'sendsub')
    # @patch.object(Command, '_get_user_profile')
    # def test_handle_sendsub(self, get_user_profile, sendsub):
    #     """Test the `sendsub` handle method."""

    #     options = {
    #         'spiders': 'all',
    #         'accounts': [],
    #         'loglevel': 'ERROR',
    #         'dry_run': False,
    #         'user': 'user1',
    #         'do-not-send': False,
    #         'ignore-time': False,
    #     }

    #     user_profile = UserProfile.objects.get(user__username='user1')

    #     c = Command()
    #     c.handle(command='sendsub', **options)
    #     sendsub.assert_called_once_with(user_profile, {},
    #                                     options['loglevel'],
    #                                     options['do-not-send'])

    #     sendsub.reset_mock()
    #     user_profiles = UserProfile.objects.all()

    #     options['ignore-time'] = True

    #     options['user'] = None
    #     c = Command()
    #     c.handle(command='sendsub', **options)
    #     for user_profile in user_profiles:
    #         sendsub.assert_any_call(user_profile,
    #                                 options['accounts'],
    #                                 options['loglevel'],
    #                                 options['do-not-send'])


class MobiCtlTestCase(TestCase):

    def test_info_title(self):
        """Test the Info._title() method."""
        issue = Mock()
        issue.configure_mock(**{
            'name': '',
            'number': '',
            'manga.name': '',
        })
        info = MobiInfo(issue)

        tests = (
            (('Manga', 'Manga 1 - title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'manga 1 - title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'Manga 1', '1', False, 0, 0),
             'Manga 001'),
            (('Manga', 'Manga 99.11', '99.11', False, 0, 0),
             'Manga 099.11'),
            (('Manga', 'Manga 1: title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'manga 1 Vol.1 title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'manga 1 vol.1 title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'Manga 1 Ch.1 title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'Manga 1 Ch1 Vol 1 title', '1', False, 0, 0),
             'Manga 001: title'),
            (('Manga', 'Manga 1 Ch.1 title', '1', True, 1, 1),
             'Manga 001 (01/01): title'),
            (('Manga', 'Manga 1 Ch.1', '1', True, 1, 1),
             'Manga 001 (01/01)'),
            (('Manga', 'Manga 1a - title', '1a', False, 0, 0),
             'Manga 001a: title'),
            (('Manga', 'Manga 1.1a - title', '1.1a', False, 0, 0),
             'Manga 001.1a: title'),
            (('Manga', 'Manga a - title', 'a', False, 0, 0),
             'Manga 000a: title'),
            (('Manga', 'Manga - title', '', False, 0, 0),
             'Manga: title'),
            (('Manga', 'title', '', False, 0, 0),
             'Manga: title'),
        )
        for params, result in tests:
            self.assertEqual(info._title(*params), result)
