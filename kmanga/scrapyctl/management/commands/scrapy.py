from __future__ import absolute_import

from optparse import make_option
import os

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from scrapy import log, signals
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings

from twisted.internet import reactor


# XXX TODO -- The command line needs to be valid for these operations:
#  - [X] List available spiders
#  - [] Search manga names and information
#  - [X] Update genres, catalog or collection
#  - [] Send one manga or a list of mangas to an email


# Part of this code is based on:
# http://stackoverflow.com/questions/22825492/how-to-stop-the-reactor-after-the-run-of-multiple-spiders-in-the-same-process-on

class ReactorControl:

    def __init__(self):
        self.crawlers_running = 0

    def add_crawler(self):
        self.crawlers_running += 1

    def remove_crawler(self):
        self.crawlers_running -= 1
        if not self.crawlers_running:
            reactor.stop()


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--list', action='store_true', dest='list', default=False,
            help='List available spiders.'),
        make_option(
            '--update', action='store', dest='update', default=None,
            help='Update an element (<genres|catalog|collection>).'),
        make_option(
            '--manga', action='store', dest='manga', default=None,
            help='Name of the manga to .'),
        make_option(
            '--url', action='store', dest='url', default=None,
            help='Set the start url for the operation,'
            ' can be a list separated with comma.'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default=None,
            help='Log level for scrapy.'),
        )
    help = 'Launch scrapy spiders from command line.'
    args = '[<spider_name>] OPTIONS'

    def _create_crawler(self):
        if 'SCRAPY_SETTINGS_MODULE' not in os.environ:
            _s = settings.SCRAPY_SETTINGS_MODULE
            os.environ['SCRAPY_SETTINGS_MODULE'] = _s

        crawler = Crawler(get_project_settings())
        crawler.configure()
        return crawler

    def spider_list(self, crawler):
        """Return the list of current spiders."""
        return [n for n in crawler.spiders.list() if n != 'mangaspider']

    def handle(self, *args, **options):
        # Get the list of spiders names that we are going to work with
        _crawler = self._create_crawler()
        all_spiders = self.spider_list(_crawler)
        spiders = args if args else all_spiders
        for name in spiders:
            if name not in all_spiders:
                raise CommandError('Spider %s not found.' % name)

        if options['list']:
            self.stdout.write('List of current spiders:')
            for name in all_spiders:
                self.stdout.write(' * %s' % name)
        elif options['update']:
            if options['update'] not in ('genres', 'catalog', 'collection'):
                raise CommandError('Not valid value for update')

            reactor_control = ReactorControl()

            for name in spiders:
                crawler = self._create_crawler()
                crawler.signals.connect(reactor_control.remove_crawler,
                                        signal=signals.spider_closed)
                kwargs = {
                    options['update']: True,
                }
                spider = crawler.spiders.create(name, **kwargs)
                reactor_control.add_crawler()
                crawler.crawl(spider)
                crawler.start()

            log.start()
            reactor.run()
