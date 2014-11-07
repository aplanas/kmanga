from __future__ import absolute_import

from optparse import make_option

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from main.models import Source
from scrapy import log
import scrapyctl.utils


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
            '--lang', action='store', dest='lang', default=None,
            help='Language of the manga (<EN|ES>).'),
        make_option(
            '--from', action='store', dest='from', default=None,
            help='Email address from where to send the issue.'),
        make_option(
            '--to', action='store', dest='to', default=None,
            help='Email address to send the issue.'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default='INFO',
            help='Log level for scrapy.'),
        )
    help = 'Launch scrapy spiders from command line.'
    args = '[<spider_name>]'

    def _get_manga(self, spider, manga):
        """Get a manga based on the name."""
        source = Source.objects.get(spider=spider)
        mangas = source.manga_set.filter(name__icontains=manga)

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
            header = 'List of current spiders:'
            self.stdout.write(header)
            self.stdout.write('=' * len(header))
            self.stdout.write('')
            for name in all_spiders:
                self.stdout.write('- %s' % name)
        elif options['update']:
            command = options['update']
            if command == 'genres':
                scrapyctl.utils.update_genres(spiders, options['loglevel'])
            elif command == 'catalog':
                scrapyctl.utils.update_catalog(spiders, options['loglevel'])
            elif command == 'collection':
                if len(spiders) > 1:
                    raise CommandError('Please, specify a single source')

                if not options['manga']:
                    raise CommandError("Parameter 'manga' is not optional")
                manga = self._get_manga(spiders[0], options['manga'])
                if not manga and not options['url']:
                    raise CommandError(
                        "'manga' not found, please, provide 'url'")
                manga_name = manga.name if manga else options['manga']

                url = manga.url if manga else options['url']
                scrapyctl.utils.update_collection(spiders, manga_name, url,
                                                  options['loglevel'])
            elif command == 'latest':
                scrapyctl.utils.update_latest(spiders, options['loglevel'])
            else:
                raise CommandError('Not valid value for update')

            # Print the SQL statistics in DEBUG mode
            if options['loglevel'] == 'DEBUG':
                queries = ['[%s]: %s' % (q['time'], q['sql'])
                           for q in connection.queries]
                log.msg('\n'.join(queries), level=log.DEBUG)
        elif options['search']:
            for name in spiders:
                header = 'Results from %s:' % name
                self.stdout.write(header)
                self.stdout.write('=' * len(header))
                self.stdout.write('')
                source = Source.objects.get(spider=name)
                q = options['search']
                for manga in source.manga_set.filter(name__icontains=q):
                    self.stdout.write('- %s' % manga)
                    for issue in manga.issue_set.order_by('number'):
                        self.stdout.write(u'  %s [%s]' % (issue.name,
                                                          issue.language))
                    self.stdout.write('')
        elif options['send']:
            if len(spiders) > 1:
                raise CommandError('Please, specify a single source')
            spider = spiders[0]
            source = Source.objects.get(spider=spider)

            if not options['manga']:
                raise CommandError("Parameter 'manga' is not optional")
            manga = self._get_manga(spiders[0], options['manga'])
            if not manga:
                raise CommandError('Manga %s not found in %s' % (
                    options['manga'], spider))

            lang = options['lang'].upper() if options['lang'] else None
            source_langs = [str(l) for l in source.sourcelanguage_set.all()]
            if lang not in source_langs:
                if len(source_langs) == 1 and not lang:
                    lang = source_langs[0]
                elif lang:
                    raise CommandError('Language %s not in %s' % (lang,
                                                                  spider))
                else:
                    raise CommandError(
                        'Please, set a valid language from %s' % source_langs)

            issues = []
            for issue in options['send'].split(','):
                if '-' in issue:
                    a, b = issue.split('-')
                    issues.extend(range(int(a), int(b)+1))
                else:
                    issues.append(int(issue))

            urls = []
            for number in issues:
                try:
                    issue = manga.issue_set.get(number=number, language=lang)
                    urls.append(issue.url)
                except ObjectDoesNotExist:
                    raise CommandError('Issue %s not in %s' % (number, manga))
                except MultipleObjectsReturned:
                    raise CommandError('Multiple issues %s in %s' % (number,
                                                                     manga))

            _from = options['from'] if options['from'] \
                    else settings.KMANGA_EMAIL

            if not options['to']:
                raise CommandError("Parameter 'to' is not optional")
            to = options['to']

            scrapyctl.utils.send(spider, manga.name, issues, urls, _from, to,
                                 options['loglevel'])
