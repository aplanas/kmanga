import os

from django.conf import settings

from scrapy import signals
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

MAX_CRAWLERS = 5


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

    def __init__(self, loglevel):
        self.loglevel = loglevel
        self.settings = self._get_settings()
        # Values for `loglevel`: CRITICAL, ERROR, WARNING, INFO, DEBUG.
        self.settings.set('LOG_LEVEL', loglevel)
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
        for name in spiders:
            kwargs = {
                command: True,
                'manga': manga,
                'issue': issue,
                'url': url,
            }
            if dry_run:
                kwargs['dry-run'] = dry_run
            self.process.crawl(name, **kwargs)
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
        for name in spiders:
            kwargs = {
                'latest': until.strftime('%d-%m-%Y'),
            }
            if dry_run:
                kwargs['dry-run'] = dry_run
            self.process.crawl(name, **kwargs)
        self.process.start()

    def _create_crawler(self, spider, manga, issue, url, from_email,
                        to_email, dry_run):
        """Utility method to create (crawler, kwargs) tuples."""
        kwargs = {
            'manga': manga,
            'issue': issue,
            'url': url,
            'from': from_email,
            'to': to_email,
        }
        if dry_run:
            kwargs['dry-run'] = dry_run
        crawler = self.process._create_crawler(spider)
        return (crawler, kwargs)

    def _send(self, spider, manga, issues, urls, from_email, to_email,
              dry_run=False):
        """Send a list of issues to an user."""
        crawlers = []
        for issue, url in zip(issues, urls):
            crawlers.append(self._create_crawler(spider, manga, issue,
                                                 url, from_email,
                                                 to_email, dry_run))
        process_control = ProcessControl(crawlers, self.process)
        process_control.run()

    def send(self, issues, user, dry_run=False):
        """High level function to send issues to an user."""
        crawlers = []
        for issue in issues:
            crawlers.append(self._create_crawler(
                issue.manga.source.name,
                issue.manga.name,
                issue.number,
                issue.url,
                settings.KMANGA_EMAIL,
                user.userprofile.kindle_email,
                dry_run
            ))
        process_control = ProcessControl(crawlers, self.process)
        process_control.run()
