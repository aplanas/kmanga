from __future__ import absolute_import

from django.core.management.base import CommandError
from django.test import mock
from django.test import TestCase

from core.models import Source
from scrapyctl.management.commands.scrapy import Command
from scrapyctl.scrapyctl import ScrapyCtl


class CommandTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def setUp(self):
        self.scrapy = ScrapyCtl('ERROR')
        self.command = Command()
        self.command.stdout = mock.MagicMock()

    def test_get_spiders(self):
        """Test recovering the list of scrapy spiders."""
        # This asks directly to Scrapy, not the database
        spiders = self.command._get_spiders(self.scrapy, 'all')
        self.assertEqual(spiders, ['batoto', 'mangareader', 'submanga', 'mangafox'])
        spiders = self.command._get_spiders(self.scrapy, 'batoto')
        self.assertEqual(spiders, ['batoto'])

        with self.assertRaises(CommandError):
            self.command._get_spiders(self.scrapy, 'missing')

    def test_get_manga(self):
        """Test the manga instance from a spider."""
        with self.assertRaises(CommandError):
            self.command._get_manga(['Source 1', 'Source 2'])

        with self.assertRaises(CommandError):
            self.command._get_manga(['Source 1'])

        with self.assertRaises(CommandError):
            self.command._get_manga(['Source 1'], manga='missing')

        # Duplicate a Manga
        source = Source.objects.get(name='Source 1')
        manga = source.manga_set.get(name='Manga 1')
        manga.id = None
        manga.save()
        with self.assertRaises(CommandError):
            self.command._get_manga(['Source 1'], manga='Manga 1')
        manga.delete()

        manga1 = self.command._get_manga(['Source 1'], manga='Manga 1')
        manga2 = self.command._get_manga(['Source 1'],
                                         url='http://source1.com/manga1')
        self.assertEqual(manga1, manga2)
