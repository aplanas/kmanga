from __future__ import absolute_import

from optparse import make_option
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from scrapy import log, signals
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings

from twisted.internet import reactor


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--list', action='store_true', dest='list', default=False,
            help='List available spiders.'),
        make_option(
            '--url', action='store', dest='url', default=None,
            help='Set the start url for the operation.'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default=None,
            help='Log level for scrapy.'),
        )
    help = 'Launch scrapy spiders from command line.'
    args = '<spider_name> <genres|catalog|collection|manga>'

    def _create_crawler(self):
        if 'SCRAPY_SETTINGS_MODULE' not in os.environ:
            _s = settings.SCRAPY_SETTINGS_MODULE
            os.environ['SCRAPY_SETTINGS_MODULE'] = _s

        crawler = Crawler(get_project_settings())
        return crawler

    def handle(self, *args, **options):
        crawler = self._create_crawler()
        # crawler.configure()

        if options['list']:
            print 'List of current spiders:'
            for name in crawler.spiders.list():
                if name != 'mangaspider':
                    print ' * %s' % name

        # raise CommandError()
