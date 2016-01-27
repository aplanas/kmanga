import datetime
import logging
import os

from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Max
from django.db.models import Q
from django.utils import timezone

from mobi.cache import MobiCache
from scraper.settings import IMAGES_STORE
from scraper.settings import MOBI_STORE

from core.models import Issue
from core.models import Manga
from core.models import Source
from registration.models import UserProfile


logger = logging.getLogger(__name__)


def print_table(title, header, body):
    """Pretty print a table with constrains."""
    print title
    print '=' * len(title)
    print

    line = ' '.join('%-*s' % (j, i) for i, j in header)
    print line
    print '-' * len(line)

    _, size = zip(*header)
    for line in body:
        line = ['%.*s' % (j, i) for i, j in zip(line, size)]
        line = ' '.join('%-*s' % (j, i) for i, j in zip(line, size))
        print line


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '-d', '--days', action='store', dest='days', default=None,
            help='Number of days to select objects (<number>).'),
        make_option(
            '-s', '--spiders', action='store', dest='spiders', default='all',
            help='List of spiders (<list_of_spiders|all>).'),
        make_option(
            '-r', '--remove', action='store_true', dest='remove',
            default=False,
            help='Force the remove of users, instead of disabling them'),
        make_option(
            '-l', '--list', action='store_true', dest='list', default=False,
            help='List the elements to remove or disable.'),
        make_option(
            '-f', '--force', action='store_true', dest='force', default=False,
            help='Force the deletion, otherwise exit the command.'),
        # General parameters
        make_option(
            '--loglevel', action='store', dest='loglevel', default='WARNING',
            help='Log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).'),
        )
    help = 'Clean old resources from the system.'
    commands = [
        'manga',
        'user',
        'image-cache',
        'mobi-cache',
        'cover',
    ]
    args = '|'.join(commands)

    def _get_sources(self, spiders):
        """Parse the `spiders` option and return a valid list of Sources."""
        # This version gets the spiders from the database, instead
        # from Scrapy (like the one in ScrapyCtl)
        spiders = spiders.split(',')
        if 'all' in spiders:
            sources = Source.objects.all()
        else:
            sources = Source.objects.filter(spider__in=spiders)
        return sources

    def handle(self, *args, **options):
        if not args or len(args) > 1:
            msg = 'Please, provide one command: %s' % Command.args
            raise CommandError(msg)
        command = args[0]

        actions = ('force', 'list', 'remove')
        if not any(options[i] for i in actions):
            msg = 'Please, provide one action: %s' % '|'.join(actions)
            raise CommandError(msg)

        # `cover` command do not use the `days` parameter
        if not options['days'] and command not in ('cover',):
            raise CommandError('Provide some days to find old objects.')
        elif options['days']:
            days = int(options['days'])

        sources = self._get_sources(options['spiders'])
        remove = options['remove']
        list_ = options['list']
        force = options['force']
        list_ = list_ or not force

        loglevel = options['loglevel']
        logger.setLevel(loglevel)

        if command == 'manga':
            self._clean_manga(days, sources, list_)
        elif command == 'user':
            self._clean_user(days, remove, list_)
        elif command == 'image-cache':
            cache = os.path.join(IMAGES_STORE, 'full')
            self._clean_image_cache(days, cache, list_)
        elif command == 'mobi-cache':
            cache = MobiCache(MOBI_STORE)
            self._clean_mobi_cache(days, cache, list_)
        elif command == 'cover':
            self._clean_cover(sources, list_)
        else:
            raise CommandError('Not valid command value. '
                               'Please, provide a command: %s' % Command.args)

    def _clean_manga(self, days, sources, list_):
        """Remove old mangas."""
        today = timezone.now()
        since = today - timezone.timedelta(days=days)
        mangas = Manga.objects.filter(modified__lt=since)
        if sources:
            mangas = mangas.filter(source__in=sources)

        if list_:
            title = 'Mangas to clean (days: %d)' % days
            header = (('name', 35), ('url', 50), ('source', 11), ('days', 3))
            body = []

        for manga in mangas:
            old = (today - manga.modified).days
            if list_:
                body.append((manga.name, manga.url, manga.source.name, old))
            else:
                logger.info('Removing %s (%s) from %s [%d].' % (manga.name,
                                                                manga.url,
                                                                manga.source,
                                                                old))
                manga.delete()

        if list_:
            print_table(title, header, body)

    def _clean_user(self, days, remove, list_):
        """Remove or disable inactive user."""
        today = timezone.now()
        since = today - timezone.timedelta(days=days)
        # Get the users that not login in several days, and do not
        # have recent results.
        userprofiles = UserProfile.objects.filter(
            user__last_login__lt=since
        ).annotate(
            last_sent=Max('user__subscription__result__modified')
        ).filter(
            Q(last_sent__lt=since) | Q(last_sent__isnull=True)
        )

        if list_:
            title = 'Users to clean (days: %d)' % days
            header = (('username', 20), ('email', 30),
                      ('last login', 10), ('last sent', 10))
            body = []

        for userprofile in userprofiles:
            user = userprofile.user
            last_login = (today - user.last_login).days
            if userprofile.last_sent:
                last_sent = (today - userprofile.last_sent).days
            else:
                last_sent = 'never'

            if list_:
                body.append((user.username, user.email, last_login,
                             last_sent))
            else:
                if remove:
                    logger.info(
                        'Removing %s <%s> [login: %d] [result: %s].' % (
                            user.username,
                            user.email,
                            last_login,
                            last_sent))
                    user.delete()
                else:
                    logger.info(
                        'Disabling %s <%s> [login: %d] [result: %s].' % (
                            user.username,
                            user.email,
                            last_login,
                            last_sent))
                    user.is_active = False
                    user.save()

        if list_:
            print_table(title, header, body)

    def _file_date(self, file_path, tzinfo=None):
        """Return the date of a file."""
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        if tzinfo:
            mtime = mtime.replace(tzinfo=tzinfo)
        return mtime

    def _clean_image_cache(self, days, cache, list_):
        """Remove old cached images."""
        today = timezone.now()

        if list_:
            title = 'Image cache to clean (days: %d)' % days
            header = (('image', 100), ('days', 3))
            body = []

        for file_ in os.listdir(cache):
            file_ = os.path.join(cache, file_)
            mtime = self._file_date(file_, today.tzinfo)
            old = (today - mtime).days
            if old >= days:
                if list_:
                    body.append((file_, old))
                else:
                    logger.info('Removing %s [%d].' % (file_, old))
                    os.unlink(file_)

        if list_:
            print_table(title, header, body)

    def _clean_mobi_cache(self, days, cache, list_):
        """Remove old cached mobi."""
        today = timezone.now()

        if list_:
            title = 'Manga cache to clean (days: %d)' % days
            header = (('manga', 35), ('issue', 5), ('source', 11), ('days', 3))
            body = []

        tzinfo = today.tzinfo
        to_delete = ((k, (today - v[-1].replace(tzinfo=tzinfo)).days)
                     for k, v in cache.iteritems())
        to_delete = ((k, o) for k, o in to_delete if o >= days)

        for key, old in to_delete:
            issue = Issue.objects.get(url=key)
            manga = issue.manga
            spider = manga.source.spider
            if list_:
                body.append((manga, issue, spider, old))
            else:
                logger.info('Removing %s %s - %s [%d].' % (manga, issue,
                                                           spider, old))
                del cache[key]

        if list_:
            print_table(title, header, body)

    def _clean_cover(self, sources, list_):
        """Remove unused cover images."""
        media = settings.MEDIA_ROOT

        if list_:
            title = 'Cover to clean'
            header = (('image', 100), ('source', 11))
            body = []

        for source in sources:
            # Get file names from the media
            path = os.path.join(media, source.spider)
            if not os.path.exists(path):
                continue
            images = {os.path.join(path, i) for i in os.listdir(path)}

            # Get current covers from the database
            mangas = Manga.objects.filter(source=source)
            covers = {i.cover.path for i in mangas if i.cover}

            for cover in images - covers:
                if list_:
                    body.append((cover, source.spider))
                else:
                    logger.info('Removing %s - %s.' % (cover, source))
                    os.unlink(cover)

        if list_:
            print_table(title, header, body)
