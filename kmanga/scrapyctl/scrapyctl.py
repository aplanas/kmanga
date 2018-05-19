import logging
import logging.handlers
import os

from django.conf import settings
from django_rq import job

from mobi.cache import IssueCache
from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

MAX_CRAWLERS = 5


class ScrapySocketHandler(logging.handlers.SocketHandler):
    """Fix the log record created by Scrapy."""

    def makePickle(self, record):
        # Some Scrapy componets, like the engine or the telnet
        # middleware, add some components to the log record, that
        # contains references to objects that can't be serialized with
        # pikcle.  For now we remove this extra information.
        if hasattr(record, 'spider'):
            del record.spider
        if hasattr(record, 'crawler'):
            del record.crawler
        return super(ScrapySocketHandler, self).makePickle(record)


class ProcessControl(object):
    def __init__(self, crawlers, process, max_crawlers=MAX_CRAWLERS):
        self.crawlers = crawlers
        self.process = process
        self.max_crawlers = max_crawlers
        self.crawlers_running = 0

    def run(self):
        while self.crawlers and self.crawlers_running < self.max_crawlers:
            self.add_crawler()
        self.process.start()

    def add_crawler(self):
        if self.crawlers:
            crawler, kwargs = self.crawlers.pop(0)
            crawler.signals.connect(self.remove_crawler,
                                    signal=signals.spider_closed)
            self.crawlers_running += 1
            self.process.crawl(crawler, **kwargs)

    def remove_crawler(self):
        self.crawlers_running -= 1
        self.add_crawler()


class ScrapyCtl(object):
    """Class to store and manage the CrawlerProcess single instance."""

    def __init__(self, accounts, loglevel, remote=False):
        self.accounts = settings.SCRAPY_ACCOUNTS
        if accounts:
            self.accounts.update(accounts)
        self.loglevel = loglevel
        self.settings = self._get_settings()
        # Values for `loglevel`: CRITICAL, ERROR, WARNING, INFO, DEBUG.
        self.settings.set('LOG_LEVEL', loglevel)
        if remote:
            # Configure remote logging and disable the scrapy logging.
            self.settings.set('LOG_ENABLED', False)
            logger = logging.getLogger()
            handler = ScrapySocketHandler(
                'localhost', logging.handlers.DEFAULT_TCP_LOGGING_PORT)
            handler.setLevel(loglevel)
            logger.addHandler(handler)

        self.process = CrawlerProcess(self.settings)

    def _get_settings(self):
        """Return the current scrapy settings."""
        if 'SCRAPY_SETTINGS_MODULE' not in os.environ:
            _s = settings.SCRAPY_SETTINGS_MODULE
            os.environ['SCRAPY_SETTINGS_MODULE'] = _s
        return get_project_settings()

    def spider_list(self):
        """Return the list of current spiders."""
        spiders = self.process.spider_loader.list()
        return [i for i in spiders if i != 'mangaspider']

    def _update(self, spiders, command, manga=None, issue=None,
                url=None, dry_run=False):
        """Launch the scraper to update the database."""
        for spider in spiders:
            if spider in self.accounts:
                username, password = self.accounts[spider]
            else:
                username, password = None, None

            kwargs = {
                command: True,
                'username': username,
                'password': password,
                'manga': manga,
                'issue': issue,
                'url': url,
            }
            if dry_run:
                kwargs['dry_run'] = dry_run
            self.process.crawl(spider, **kwargs)
        self.process.start()

    def update_genres(self, spiders, dry_run=False):
        """Launch the scraper to update the genres."""
        self._update(spiders, 'genres', dry_run=dry_run)

    def update_catalog(self, spiders, dry_run=False):
        """Launch the scraper to update the full catalog of a site."""
        self._update(spiders, 'catalog', dry_run=dry_run)

    def update_collection(self, spiders, manga, url, dry_run=False):
        """Launch the scraper to update list of issues for one manga."""
        self._update(spiders, 'collection', manga=manga, url=url,
                     dry_run=dry_run)

    def update_latest(self, spiders, until, dry_run=False):
        """Launch the scraper to update the latest issues."""
        for spider in spiders:
            if spider in self.accounts:
                username, password = self.accounts[spider]
            else:
                username, password = None, None

            kwargs = {
                'latest': until.strftime('%d-%m-%Y'),
                'username': username,
                'password': password,
            }
            if dry_run:
                kwargs['dry_run'] = dry_run
            self.process.crawl(spider, **kwargs)
        self.process.start()

    def _create_crawler(self, spider, manga, issue, url, dry_run):
        """Utility method to create (crawler, kwargs) tuples."""
        if spider in self.accounts:
            username, password = self.accounts[spider]
        else:
            username, password = None, None

        kwargs = {
            'manga': manga,
            'username': username,
            'password': password,
            'issue': issue,
            'url': url,
        }
        if dry_run:
            kwargs['dry_run'] = dry_run
        crawler = self.process._create_crawler(spider)
        return (crawler, kwargs)

    def scrape(self, issues, dry_run=False):
        """Create crawlers to scrape issues."""
        cache = IssueCache(settings.ISSUES_STORE, settings.IMAGES_STORE)
        crawlers = [
            self._create_crawler(
                issue.manga.source.name.lower(),
                issue.manga.name,
                issue.number,
                issue.url,
                dry_run
            ) for issue in issues if issue.url not in cache
        ]
        process_control = ProcessControl(crawlers, self.process)
        process_control.run()


def _scrape_issues(issues, accounts, loglevel):
    """Helper to scrape issues."""
    scrapy = ScrapyCtl(accounts, loglevel, remote=True)
    scrapy.scrape(issues)


@job('default', timeout=60*60)
def scrape_issues(issues, accounts, loglevel):
    """RQ job to scrape issues."""
    _scrape_issues(issues, accounts, loglevel)


@job('low', timeout=60*60*3)
def scrape_issues_slow(issues, accounts, loglevel):
    """RQ job to scrape issues with a proxy."""
    _scrape_issues(issues, accounts, loglevel)
