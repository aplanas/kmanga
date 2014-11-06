from __future__ import absolute_import

from optparse import make_option
import os

from django.conf import settings
from django.db import connection
from django.core.management.base import BaseCommand, CommandError

import utils
from main.models import Source
from scrapy import log, signals
from scrapy.crawler import Crawler
from scrapy.utils.project import get_project_settings

from twisted.internet import reactor


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
            help='Update an element (<genres|catalog|collection|latest>).'),
        make_option(
            '--search', action='store', dest='search', default=None,
            help='Search locally mangas.'),
        make_option(
            '--send', action='store', dest='send', default=None,
            help='Send issues to the user (list of numbers).'),
        make_option(
            '--manga', action='store', dest='manga', default=None,
            help='Name of the manga.'),
        make_option(
            '--url', action='store', dest='url', default=None,
            help='Set the start url for the operation,'
            ' can be a list separated with comma.'),
        make_option(
            '--to', action='store', dest='to', default=None,
            help='Email address to send the issue.'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default='INFO',
            help='Log level for scrapy.'),
        )
    help = 'Launch scrapy spiders from command line.'
    args = '[<spider_name>]'

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
        all_spiders = utils.spider_list()
        spiders = args if args else all_spiders
        for name in spiders:
            if name not in all_spiders:
                raise CommandError('Spider %s not found.' % name)

        if options['list']:
            self.stdout.write('List of current spiders:')
            for name in all_spiders:
                self.stdout.write(' * %s' % name)
        elif options['update']:
            _options = ('genres', 'catalog', 'collection', 'latest')
            if options['update'] not in _options:
                raise CommandError('Not valid value for update')

            reactor_control = ReactorControl()

            for name in spiders:
                crawler = self._create_crawler()
                crawler.signals.connect(reactor_control.remove_crawler,
                                        signal=signals.spider_closed)
                kwargs = {
                    options['update']: True,
                    'manga': options['manga'],
                }
                if options['url']:
                    kwargs['url'] = options['url']
                spider = crawler.spiders.create(name, **kwargs)
                reactor_control.add_crawler()
                crawler.crawl(spider)
                crawler.start()

            log.start(loglevel=options['loglevel'])
            reactor.run()

            # Print the SQL statistics in DEBUG mode
            queries = ['[%s]: %s' % (q['time'], q['sql'])
                       for q in connection.queries]
            log.msg('\n'.join(queries), level=log.DEBUG)

        elif options['search']:
            for name in spiders:
                header = 'Results from %s:' % name
                print header
                print '=' * len(header)
                print
                source = Source.objects.get(spider=name)
                q = options['search']
                for manga in source.manga_set.filter(name__icontains=q):
                    print '- %s' % manga
                    for issue in manga.issue_set.order_by('number'):
                        print '  %s' % issue
                    print
        elif options['send']:
            pass
