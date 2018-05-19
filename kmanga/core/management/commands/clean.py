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
            '-o', '--hours', action='store', dest='hours', default=None,
            help='Number of hours to select objects (<number>). '
                 'This is added to the `days` parameter.')
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

    def _print_table(self, title, header, body):
        """Pretty print a table with constrains."""
        self.stdout.write('')
        self.stdout.write(title)
        self.stdout.write('=' * len(title))
        self.stdout.write('')

        line = ''.join('%-*s' % (j, i) for i, j in header)
        self.stdout.write(line)
        self.stdout.write('-' * len(line))

        _, size = zip(*header)
        for line in body:
            line = ['%.*s' % (j-1, i) for i, j in zip(line, size)]
            line = ''.join('%-*s' % (j, i) for i, j in zip(line, size))
            self.stdout.write(line)
        self.stdout.write('-' * len(line))

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

        # `cover` command do not use the `days` nor `hours` parameter
        if options['days'] is None and options['hours'] is None \
           and command not in ('cover',):
            raise CommandError('Provide some days/hours to find old objects.')
        elif options['days'] or options['hours']:
            hours = 24 * int(options['days'] if options['days'] else 0)
            hours += int(options['hours'] if options['hours'] else 0)

        sources = self._get_sources(options['spiders'])
        remove = options['remove']
        list_ = options['list']
        force = options['force']
        list_ = list_ or not force

        loglevel = options['loglevel']
        logger.setLevel(loglevel)

        if command == 'manga':
            self._clean_manga(hours, sources, list_)
        elif command == 'user':
            self._clean_user(hours, remove, list_)
        elif command == 'image-cache':
            cache = os.path.join(settings.IMAGES_STORE, 'full')
            self._clean_image_cache(hours, cache, list_)
        elif command == 'mobi-cache':
            cache = MobiCache(settings.MOBI_STORE)
            self._clean_cache(hours, cache, list_)
        elif command == 'issue-cache':
            cache = IssueCache(settings.ISSUES_STORE, settings.IMAGES_STORE)
            self._clean_cache(hours, cache, list_)
            mobi_cache = MobiCache(settings.MOBI_STORE)
            self._clean_broken_issue_cache(cache, mobi_cache, list_)
        elif command == 'cover':
            self._clean_cover(sources, list_)
        elif command == 'result-processing':
            self._clean_result(hours, Result.PROCESSING, list_)
        elif command == 'result-failed':
            self._clean_result(hours, Result.FAILED, list_)
        else:
            raise CommandError('Not valid command value.')

    def _fmt(self, timedelta=None, hours=None):
        """String format hours to show days and hours."""
        fmt = '%02dd %02dh'
        if timedelta:
            return fmt % (timedelta.days, timedelta.seconds // 3600)
        if hours:
            return fmt % (hours // 24, hours % 24)

    def _clean_manga(self, hours, sources, list_):
        """Remove old mangas not updated (deleted)."""
        today = timezone.now()
        since = today - timezone.timedelta(hours=hours)
        mangas = Manga.objects.filter(modified__lt=since)
        if sources:
            mangas = mangas.filter(source__in=sources)

        if list_:
            title = 'Mangas to remove (age: %s)' % self._fmt(hours=hours)
            header = (('name', 35), ('url', 46), ('source', 11), ('age', 7))
            body = []

        for manga in mangas:
            old = self._fmt(timedelta=(today - manga.modified))
            if list_:
                body.append((manga.name, manga.url, manga.source.name, old))
            else:
                logger.info('Removing %s (%s) from %s [%s].' % (manga.name,
                                                                manga.url,
                                                                manga.source,
                                                                old))
                manga.delete()

        if list_:
            self._print_table(title, header, body)

    def _clean_user(self, hours, remove, list_):
        """Remove or disable inactive user."""
        today = timezone.now()
        since = today - timezone.timedelta(hours=hours)
        # Get the users that not login in several days/hours, and do
        # not have recent results.
        userprofiles = UserProfile.objects.filter(
            user__last_login__lt=since
        ).annotate(
            last_sent=Max('user__subscription__result__modified')
        ).filter(
            Q(last_sent__lt=since) | Q(last_sent__isnull=True)
        )

        if list_:
            title = 'Users to remove (age: %d)' % hours
            header = (('username', 30), ('email', 40), ('last login', 10),
                      ('last sent', 10))
            body = []

        for userprofile in userprofiles:
            user = userprofile.user
            last_login = self._fmt(timedelta=(today - user.last_login))
            if userprofile.last_sent:
                last_sent = self._fmt(
                    timedelta=(today - userprofile.last_sent))
            else:
                last_sent = 'never'

            if list_:
                body.append((user.username, user.email, last_login,
                             last_sent))
            else:
                if remove:
                    logger.info(
                        'Removing %s <%s> [login: %s] [result: %s].' % (
                            user.username,
                            user.email,
                            last_login,
                            last_sent))
                    user.delete()
                else:
                    logger.info(
                        'Disabling %s <%s> [login: %s] [result: %s].' % (
                            user.username,
                            user.email,
                            last_login,
                            last_sent))
                    user.is_active = False
                    user.save()

        if list_:
            self._print_table(title, header, body)

    def _file_date(self, file_path, tzinfo=None):
        """Return the date of a file."""
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(file_path))
        if tzinfo:
            mtime = mtime.replace(tzinfo=tzinfo)
        return mtime

    def _clean_image_cache(self, hours, cache, list_):
        """Remove old cached images."""
        today = timezone.now()

        if list_:
            title = 'Image from the cache to remove ' \
                '(age: %s)' % self._fmt(hours=hours)
            header = (('image', 92), ('age', 7))
            body = []

        for file_ in os.listdir(cache):
            file_ = os.path.join(cache, file_)
            mtime = self._file_date(file_, today.tzinfo)
            old = (today - mtime).total_seconds() // 3600
            if old >= hours:
                old = self._fmt(hours=old)
                if list_:
                    body.append((file_, old))
                else:
                    logger.info('Removing %s [%s].' % (file_, old))
                    os.unlink(file_)

        if list_:
            self._print_table(title, header, body)

    def _clean_cache(self, hours, cache, list_):
        """Remove old cached mobi or issues."""
        today = timezone.now()

        if list_:
            title = 'Items from the cache to remove ' \
                '(age: %s)' % self._fmt(hours=hours)
            header = (('manga', 54), ('issue', 23), ('source', 15), ('age', 7))
            body = []

        tzinfo = today.tzinfo
        to_delete = ((k, today - v[-1].replace(tzinfo=tzinfo))
                     for k, v in cache.items())
        to_delete = ((k, o) for k, o in to_delete
                     if o.total_seconds() // 3600 >= hours)

        for key, old in to_delete:
            try:
                issue = Issue.objects.get(url=key)
                manga = issue.manga
                spider = manga.source.spider
            except Exception:
                issue = key
                manga = '<UNKNOWN>'
                spider = '<UNKNOWN>'
            old = self._fmt(timedelta=old)
            if list_:
                body.append((manga, issue, spider, old))
            else:
                logger.info('Removing %s %s - %s [%s].' % (manga, issue,
                                                           spider, old))
                del cache[key]

        if list_:
            self._print_table(title, header, body)

    def _missing_pages(self, images):
        """Check if there is a missing page."""
        return not all(i['images'] for i in images)

    def _clean_broken_issue_cache(self, issue_cache, mobi_cache, list_):
        """Remove old mobi and issues with missing pages."""

        if list_:
            title = 'Issues with missing pages'
            header = (('manga', 54), ('issue', 23), ('source', 15))
            body = []

        to_delete = [k for k, v in issue_cache.items()
                     if self._missing_pages(v[0])]
        for key in to_delete:
            try:
                issue = Issue.objects.get(url=key)
                manga = issue.manga
                spider = manga.source.spider
            except Exception:
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
            self._print_table(title, header, body)

    def _clean_cover(self, sources, list_):
        """Remove unused cover images."""
        media = os.path.abspath(settings.MEDIA_ROOT)

        if list_:
            title = 'Covers to remove'
            header = (('image', 84), ('source', 15))
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
            self._print_table(title, header, body)

    def _clean_result(self, hours, status, list_):
        """Remove old results in a bad state."""
        today = timezone.now()
        since = today - timezone.timedelta(hours=hours)
        results = Result.objects.filter(modified__lt=since, status=status)

        if list_:
            title = 'Results to remove (age: %s)' % self._fmt(hours=hours)
            header = (('manga', 50), ('issue', 21), ('source', 13),
                      ('user', 8), ('age', 7))
            body = []

        for result in results:
            old = self._fmt(timedelta=(today - result.modified))
            if list_:
                body.append((result.issue.manga.name,
                             result.issue.number,
                             result.issue.manga.source.name,
                             result.subscription.user,
                             old))
            else:
                logger.info('Removing %s (%s) for user %s [%s].' % (
                    result.issue,
                    result.status,
                    result.subscription.user,
                    old))
                result.delete()

        if list_:
            self._print_table(title, header, body)
