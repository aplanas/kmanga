from __future__ import absolute_import

import os

from django.conf import settings
from django.db import connection

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


def _create_crawler():
    """Create a scrapy crawler instance."""
    if 'SCRAPY_SETTINGS_MODULE' not in os.environ:
        _s = settings.SCRAPY_SETTINGS_MODULE
        os.environ['SCRAPY_SETTINGS_MODULE'] = _s

    crawler = Crawler(get_project_settings())
    crawler.configure()
    return crawler


def spider_list():
    """Return the list of current spiders."""
    crawler = _create_crawler()
    return [n for n in crawler.spiders.list() if n != 'mangaspider']


def _updatedb(spiders, command, manga=None, issue=None, loglevel='INFO'):
    """Launch the scraper to update the database."""
    reactor_control = ReactorControl()

    for name in spiders:
        crawler = _create_crawler()
        crawler.signals.connect(reactor_control.remove_crawler,
                                signal=signals.spider_closed)
        kwargs = {
            command: True,
            'manga': manga,
            'url': url,
        }
        spider = crawler.spiders.create(name, **kwargs)
        reactor_control.add_crawler()
        crawler.crawl(spider)
        crawler.start()

    log.start(loglevel=loglevel)
    reactor.run()


def updatedb_genres(spiders, loglevel='INFO'):
    """Launch the scraper to update the genres."""
    _updatedb(spider, 'genres', loglevel=loglevel)


def updatedb_catalog(spiders, loglevel='INFO'):
    """Launch the scraper to update the genres."""
    _updatedb(spider, 'genres', loglevel=loglevel)


def updatedb_collection(spiders, manga, url, loglevel='INFO'):
    """Launch the scraper to update list of issues for one manga."""
    _updatedb(spider, 'collection', manga=manga, url=url,
              loglevel=loglevel)


def updatedb_latest(spiders, loglevel='INFO'):
    """Launch the scraper to update the latest issues."""
    _updatedb(spider, command='latest', loglevel=loglevel)


#             # Print the SQL statistics in DEBUG mode
#             queries = ['[%s]: %s' % (q['time'], q['sql'])
#                        for q in connection.queries]
#             log.msg('\n'.join(queries), level=log.DEBUG)

#         elif options['search']:
#             for name in spiders:
#                 header = 'Results from %s:' % name
#                 print header
#                 print '=' * len(header)
#                 print
#                 source = Source.objects.get(spider=name)
#                 q = options['search']
#                 for manga in source.manga_set.filter(name__icontains=q):
#                     print '- %s' % manga
#                     for issue in manga.issue_set.order_by('number'):
#                         print '  %s' % issue
#                     print
#         elif options['send']:
#             pass




# from scrapy import log, signals
# from scrapy.crawler import Crawler
# from scrapy.utils.project import get_project_settings

# from twisted.internet import reactor

# from scraper.spiders.mangareader import MangaReader


def run_spider(spider, manga, issue, to_mail):
    pass
    # kwargs = {
    #     'manga': manga,
    #     'issue': issue,
    #     'from': None,
    #     'to': to_mail,
    # }

    # spider = MangaReader(**kwargs)
    # settings = get_project_settings()
    # crawler = Crawler(settings)
    # crawler.signals.connect(reactor.stop, signal=signals.spider_closed)
    # crawler.configure()
    # crawler.crawl(spider)
    # crawler.start()
    # log.start()
    # reactor.run()
