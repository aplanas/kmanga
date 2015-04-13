from __future__ import absolute_import

from datetime import date
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection

from core.models import Manga
from core.models import Source
from scrapy import log
import scrapyctl.utils


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '-l', '--list', action='store_true', dest='list', default=False,
            help='List available spiders.'),
        make_option(
            '-u', '--update', action='store', dest='update', default=None,
            help='Update an element (<genres|catalog|collection|latest>).'),
        make_option(
            '-s', '--search', action='store', dest='search', default=None,
            help='Search locally mangas (<text>).'),
        make_option(
            '--details', action='store_true', dest='details', default=False,
            help='Add more details in the list of mangas.'),
        make_option(
            '-e', '--send', action='store', dest='send', default=None,
            help='Send issues to the user (<list_of_numbers|all>).'),
        make_option(
            '--subscribe', action='store', dest='subscribe', default=None,
            help='Create a subscription for an user to a manga (<days>).'),
        make_option(
            '-m', '--manga', action='store', dest='manga', default=None,
            help='Name of the manga (<text>).'),
        make_option(
            '--url', action='store', dest='url', default=None,
            help='Set the start url for the operation (<url>).'),
        make_option(
            '--lang', action='store', dest='lang', default=None,
            help='Language of the manga (<EN|ES>).'),
        make_option(
            '--until', action='store', dest='until', default=date.today(),
            help='Until parameter to latest update (<DD-MM-YYYY>).'),
        make_option(
            '--from', action='store', dest='from', default=None,
            help='Email address from where to send the issue (<email>).'),
        make_option(
            '--to', action='store', dest='to', default=None,
            help='Email address to send the issue (<email>).'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default='INFO',
            help='Scrapy log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).'),
        make_option(
            '--dry-run', action='store_true', dest='dry-run', default=False,
            help='Bypass all the pipelines.'),
        )
    help = 'Launch scrapy spiders from command line.'
    args = '[<spider_name>]'

    def _get_manga(self, spider, manga=None, url=None):
        """Get a manga based on the name."""
        source = Source.objects.get(spider=spider)
        kwargs = {}
        if manga:
            kwargs['name__icontains'] = manga
        if url:
            kwargs['url'] = url
        mangas = source.manga_set.filter(**kwargs)

        manga = None
        if len(mangas) > 1:
            self.stdout.write('Error. Found multiple mangas:')
            for manga in mangas:
                self.stdout.write('- %s' % manga)
            self.stdout.write('Please, choose one and try again')
        if len(mangas) == 1:
            manga = mangas[0]
        return manga

    def handle(self, *args, **options):
        # Get the list of spiders names that we are going to work with
        all_spiders = scrapyctl.utils.spider_list()
        spiders = args if args else all_spiders
        for name in spiders:
            if name not in all_spiders:
                raise CommandError('Spider %s not found.' % name)

        if options['list']:
            self.list_spiders(all_spiders)
        elif options['update']:
            command = options['update']
            manga = options['manga']
            url = options['url']
            until = options['until']
            loglevel = options['loglevel']
            dry_run = options['dry-run']
            self.update(spiders, command, manga, url, until, loglevel, dry_run)
        elif options['search']:
            manga = options['search']
            lang = options['lang']
            details = options['details']
            self.search(spiders, manga, lang, details)
        elif options['subscribe']:
            pass
        elif options['send']:
            numbers = options['send']
            manga = options['manga']
            url = options['url']
            lang = options['lang']
            _from = options['from']
            to = options['to']
            loglevel = options['loglevel']
            self.send(spiders, numbers, manga, url, lang, _from, to, loglevel)

    def list_spiders(self, spiders):
        """List current spiders than can be activated."""
        header = 'List of current spiders:'
        self.stdout.write(header)
        self.stdout.write('=' * len(header))
        self.stdout.write('')
        for name in spiders:
            self.stdout.write('- %s' % name)

    def update(self, spiders, command, manga, url, until, loglevel, dry_run):
        """Refesh from the database part of the manga information."""
        if command == 'genres':
            scrapyctl.utils.update_genres(spiders, loglevel, dry_run)
        elif command == 'catalog':
            scrapyctl.utils.update_catalog(spiders, loglevel, dry_run)
        elif command == 'collection':
            if len(spiders) > 1:
                raise CommandError('Please, specify a single source')

            if not manga and not url:
                raise CommandError("Provide parameters 'manga' or 'url'")

            _manga = self._get_manga(spiders[0], manga=manga, url=url)
            if not _manga and not url:
                raise CommandError(
                    "'manga' not found, please, provide 'url'")

            manga_name = _manga.name if _manga else manga
            manga_name = manga_name if manga_name else '<NoName>'
            _url = _manga.url if _manga else url

            scrapyctl.utils.update_collection(spiders, manga_name, _url,
                                              loglevel, dry_run)
        elif command == 'latest':
            if isinstance(until, basestring):
                day, month, year = [int(x) for x in until.split('-')]
                until = date(year=year, month=month, day=day)
            scrapyctl.utils.update_latest(spiders, until, loglevel, dry_run)
        else:
            raise CommandError('Not valid value for update')

        # Refresh the MATERIALIZED VIEW for full text search
        Manga.objects.refresh()

        # Print the SQL statistics in DEBUG mode
        if loglevel == 'DEBUG':
            queries = ['[%s]: %s' % (q['time'], q['sql'])
                       for q in connection.queries]
            log.msg('\n'.join(queries), level=log.DEBUG)

    def search(self, spiders, manga, lang, details):
        """Search a manga in the database."""
        for name in spiders:
            header = 'Results from %s:' % name
            self.stdout.write(header)
            self.stdout.write('=' * len(header))
            self.stdout.write('')
            source = Source.objects.get(spider=name)
            q = manga
            for manga in source.manga_set.filter(name__icontains=q):
                self.stdout.write('- %s' % manga)
                issues = manga.issue_set
                if lang:
                    lang = lang.upper()
                    issues = issues.filter(language=lang)
                for issue in issues.order_by('number'):
                    if details:
                        self.stdout.write(u' [%s] [%s] [%s] [%s] %s' %
                                          (issue.language,
                                           issue.number,
                                           issue.release,
                                           issue.url,
                                           issue.name))
                    else:
                        self.stdout.write(u' [%s] [%s] %s' %
                                          (issue.language,
                                           issue.number,
                                           issue.name))
                self.stdout.write('')

    def send(self, spiders, numbers, manga, url, lang, _from, to, loglevel):
        """Send a list of issues to an user."""
        if len(spiders) > 1:
            raise CommandError('Please, specify a single source')
        spider = spiders[0]
        source = Source.objects.get(spider=spider)

        if not manga:
            raise CommandError("Parameter 'manga' is not optional")
        manga = self._get_manga(spiders[0], manga=manga)
        if not manga:
            raise CommandError('Manga %s not found in %s' % (manga, spider))

        lang = lang.upper() if lang else None
        source_langs = [str(l) for l in source.sourcelanguage_set.all()]
        if lang not in source_langs:
            if len(source_langs) == 1 and not lang:
                lang = source_langs[0]
            elif lang:
                raise CommandError('Language %s not in %s' % (lang, spider))
            else:
                raise CommandError(
                    'Please, set a valid language from %s' % source_langs)

        urls = []
        issues = []
        if numbers == 'all':
            _issues = manga.issue_set.filter(language=lang)
            # If a URL is set, send only this single manga
            if url:
                _issues = _issues.filter(url=url)

            for issue in _issues.order_by('number'):
                urls.append(issue.url)
                issues.append(issue.number)
        else:
            _issues = []
            for issue in numbers.split(','):
                if '-' in issue:
                    a, b = issue.split('-')
                    _issues.extend(range(int(a), int(b)+1))
                else:
                    _issues.append(float(issue))

            for number in _issues:
                issue = manga.issue_set.filter(number=number, language=lang)
                issue_count = issue.count()
                if issue_count:
                    if issue_count > 1:
                        msg = 'Multiple issues %s in %s. Adding all matches.'
                        print msg % (number, manga)

                    for i in issue:
                        issues.append(i.number)
                        urls.append(i.url)
                else:
                    raise CommandError('Issue %s not in %s' % (number, manga))

        _from = _from if _from else settings.KMANGA_EMAIL
        if not to:
            raise CommandError("Parameter 'to' is not optional")
        scrapyctl.utils.send(spider, manga.name, issues, urls, _from, to,
                             loglevel)
