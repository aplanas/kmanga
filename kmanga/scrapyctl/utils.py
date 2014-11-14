import os

from django.conf import settings

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


def _update(spiders, command, manga=None, issue=None, url=None,
            loglevel='INFO', dry_run=False):
    """Launch the scraper to update the database."""
    reactor_control = ReactorControl()

    for name in spiders:
        crawler = _create_crawler()
        crawler.signals.connect(reactor_control.remove_crawler,
                                signal=signals.spider_closed)
        kwargs = {
            command: True,
            'manga': manga,
            'issue': issue,
            'url': url,
        }
        if dry_run:
            kwargs['dry-run'] = dry_run
        spider = crawler.spiders.create(name, **kwargs)
        reactor_control.add_crawler()
        crawler.crawl(spider)
        crawler.start()

    log.start(loglevel=loglevel)
    reactor.run()


def update_genres(spiders, loglevel='INFO', dry_run=False):
    """Launch the scraper to update the genres."""
    _update(spiders, 'genres', loglevel=loglevel, dry_run=dry_run)


def update_catalog(spiders, loglevel='INFO', dry_run=False):
    """Launch the scraper to update the full catalog of a site."""
    _update(spiders, 'catalog', loglevel=loglevel, dry_run=dry_run)


def update_collection(spiders, manga, url, loglevel='INFO', dry_run=False):
    """Launch the scraper to update list of issues for one manga."""
    _update(spiders, 'collection', manga=manga, url=url,
            loglevel=loglevel, dry_run=dry_run)


def update_latest(spiders, loglevel='INFO', dry_run=False):
    """Launch the scraper to update the latest issues."""
    _update(spiders, command='latest', loglevel=loglevel, dry_run=dry_run)


def send(spider, manga, issues, urls, from_email, to_email, loglevel='INFO',
         dry_run=False):
    """Send a list of issues to an user."""
    reactor_control = ReactorControl()

    name = spider
    for issue, url in zip(issues, urls):
        crawler = _create_crawler()
        crawler.signals.connect(reactor_control.remove_crawler,
                                signal=signals.spider_closed)
        kwargs = {
            'manga': manga,
            'issue': issue,
            'url': url,
            'from': from_email,
            'to': to_email,
        }
        if dry_run:
            kwargs['dry-run'] = dry_run
        spider = crawler.spiders.create(name, **kwargs)
        reactor_control.add_crawler()
        crawler.crawl(spider)
        crawler.start()

    log.start(loglevel=loglevel)
    reactor.run()
