import datetime
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db.models import Max
from django.db.models import Q
from django.utils import timezone

from core.models import Issue
from core.models import Manga
from core.models import Result
from core.models import Source
from mobi.cache import IssueCache
from mobi.cache import MobiCache
from registration.models import UserProfile


logger = logging.getLogger(__name__)


def print_table(title, header, body):
    """Pretty print a table with constrains."""
    print
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
    help = 'Clean old resources from the system.'

    def add_arguments(self, parser):
        parser.add_argument('command', choices=[
            'manga',
            'user',
            'image-cache',
            'issue-cache',
            'mobi-cache',
            'cover',
            'result-processing',
            'result-failed',
        ], help='Command to execute')

        parser.add_argument(
            '-d', '--days', action='store', dest='days', default=None,
            help='Number of days to select objects (<number>).')
        parser.add_argument(
            '-s', '--spiders', action='store', dest='spiders', default='all',
            help='List of spiders (<list_of_spiders|all>).')
        parser.add_argument(
            '-r', '--remove', action='store_true', dest='remove',
            default=False,
            help='Force the remove of users, instead of disabling them')
        parser.add_argument(
            '-l', '--list', action='store_true', dest='list', default=False,
            help='List the elements to remove or disable.')
        parser.add_argument(
            '-f', '--force', action='store_true', dest='force', default=False,
            help='Force the deletion, otherwise exit the command.')
        # General parameters
        parser.add_argument(
            '--loglevel', action='store', dest='loglevel', default='WARNING',
            help='Log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).')

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
        command = options['command']

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
            cache = os.path.join(settings.IMAGES_STORE, 'full')
            self._clean_image_cache(days, cache, list_)
        elif command == 'mobi-cache':
            cache = MobiCache(settings.MOBI_STORE)
            self._clean_cache(days, cache, list_)
        elif command == 'issue-cache':
            cache = IssueCache(settings.ISSUES_STORE, settings.IMAGES_STORE)
            self._clean_cache(days, cache, list_)
            mobi_cache = MobiCache(settings.MOBI_STORE)
            self._clean_broken_issue_cache(cache, mobi_cache, list_)
        elif command == 'cover':
            self._clean_cover(sources, list_)
        elif command == 'result-processing':
            self._clean_result(days, Result.PROCESSING, list_)
        elif command == 'result-failed':
            self._clean_result(days, Result.FAILED, list_)
        else:
            raise CommandError('Not valid command value.')

    def _clean_manga(self, days, sources, list_):
        """Remove old mangas not updated (deleted)."""
        today = timezone.now()
        since = today - timezone.timedelta(days=days)
        mangas = Manga.objects.filter(modified__lt=since)
        if sources:
            mangas = mangas.filter(source__in=sources)

        if list_:
            title = 'Mangas to remove (days: %d)' % days
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
            title = 'Users to remove (days: %d)' % days
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
            title = 'Image from the cache to remove (days: %d)' % days
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

    def _clean_cache(self, days, cache, list_):
        """Remove old cached mobi or issues."""
        today = timezone.now()

        if list_:
            title = 'Items from the cache to remove (days: %d)' % days
            header = (('manga', 35), ('issue', 5), ('source', 11), ('days', 3))
            body = []

        tzinfo = today.tzinfo
        to_delete = ((k, (today - v[-1].replace(tzinfo=tzinfo)).days)
                     for k, v in cache.iteritems())
        to_delete = ((k, o) for k, o in to_delete if o >= days)

        for key, old in to_delete:
            try:
                issue = Issue.objects.get(url=key)
                manga = issue.manga
                spider = manga.source.spider
            except:
                issue = key
                manga = '<UNKNOWN>'
                spider = '<UNKNOWN>'
            if list_:
                body.append((manga, issue, spider, old))
            else:
                logger.info('Removing %s %s - %s [%d].' % (manga, issue,
                                                           spider, old))
                del cache[key]

        if list_:
            print_table(title, header, body)

    def _missing_pages(self, images):
        """Check if there is a missing page."""
        return not all(i['images'] for i in images)

    def _clean_broken_issue_cache(self, issue_cache, mobi_cache, list_):
        """Remove old mobi and issues with missing pages."""

        if list_:
            title = 'Issues with missing pages'
            header = (('manga', 35), ('issue', 5), ('source', 11))
            body = []

        to_delete = [k for k, v in issue_cache.iteritems()
                     if self._missing_pages(v[0])]
        for key in to_delete:
            try:
                issue = Issue.objects.get(url=key)
                manga = issue.manga
                spider = manga.source.spider
            except:
                issue = key
                manga = '<UNKNOWN>'
                spider = '<UNKNOWN>'
            if list_:
                body.append((manga, issue, spider))
            else:
                logger.info('Removing %s %s - %s.' % (manga, issue, spider))
                del mobi_cache[key]
                del issue_cache[key]

        if list_:
            print_table(title, header, body)

    def _clean_cover(self, sources, list_):
        """Remove unused cover images."""
        media = os.path.abspath(settings.MEDIA_ROOT)

        if list_:
            title = 'Covers to remove'
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
            covers = {os.path.abspath(i.cover.path) for i in mangas if i.cover}

            for cover in images - covers:
                if list_:
                    body.append((cover, source.spider))
                else:
                    logger.info('Removing %s - %s.' % (cover, source))
                    os.unlink(cover)

        if list_:
            print_table(title, header, body)

    def _clean_result(self, days, status, list_):
        """Remove old results in a bad state."""
        today = timezone.now()
        since = today - timezone.timedelta(days=days)
        results = Result.objects.filter(modified__lt=since, status=status)

        if list_:
            title = 'Results to remove (days: %d)' % days
            header = (('manga', 35), ('issue', 5), ('source', 11), ('user', 8),
                      ('days', 3))
            body = []

        for result in results:
            old = (today - result.modified).days
            if list_:
                body.append((result.issue.manga.name,
                             result.issue.number,
                             result.issue.manga.source.name,
                             result.subscription.user,
                             old))
            else:
                logger.info('Removing %s (%s) for user %s [%d].' % (
                    result.issue,
                    result.status,
                    result.subscription.user,
                    old))
                result.delete()

        if list_:
            print_table(title, header, body)
