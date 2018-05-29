import datetime
import logging
import logging.handlers

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection
from django.db.models import F
from django.db.models import Q
from django.utils import timezone

from core.models import Manga
from core.models import Source
from core.models import Subscription
from registration.models import UserProfile
from scrapyctl.scrapyctl import ScrapyCtl
from scrapyctl.utils import send

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Launch scrapy spiders from command line.'

    def add_arguments(self, parser):
        parser.add_argument('command', choices=[
            'list',
            'update-genres',
            'update-catalog',
            'update-collection',
            'update-latest',
            'search',
            'subscribe',
            'send',
            'sendsub',
            'retry',
        ], help='Command to execute')

        # Parameters used by some commands
        parser.add_argument(
            '-m', '--manga', action='store', dest='manga', default=None,
            help='Name of the manga. Partial match for search (<manga>).')
        parser.add_argument(
            '--issues', action='store', dest='issues', default=None,
            help='List of issues numbers (order) (<list_of_numbers|all>).')
        parser.add_argument(
            '--url', action='store', dest='url', default=None,
            help='Manga or issue URL (<url>).')
        parser.add_argument(
            '--lang', action='store', dest='lang', default=None,
            help='Language of the manga (<EN|ES>).')
        parser.add_argument(
            '--details', action='store_true', dest='details', default=False,
            help='Add more details in the list of mangas.')
        parser.add_argument(
            '--until', action='store', dest='until',
            default=datetime.date.today(),
            help='Until parameter to latest update (<DD-MM-YYYY>).')
        parser.add_argument(
            '--issues-per-day', action='store', dest='issues-per-day',
            default=4,
            help='Number of issues to send per day (<number>).')
        parser.add_argument(
            '--do-not-send', action='store_true', dest='do-not-send',
            default=False,
            help='Avoid the send of the manga, but register the send.')
        parser.add_argument(
            '--user', action='store', dest='user', default=None,
            help='User name or email address (<user|email>).')
        parser.add_argument(
            '--ignore-time', action='store_true', dest='ignore-time',
            default=False,
            help='Send subscription to all users (ignore subscription time).')

        # General parameters
        parser.add_argument(
            '--spiders', action='store', dest='spiders', default='all',
            help='List of spiders (<list_of_spiders|all>).')
        parser.add_argument(
            '--accounts', action='append', dest='accounts', default=[],
            nargs=3, help='Spider login (<spider> <username> <password>).'),
        parser.add_argument(
            '--loglevel', action='store', dest='loglevel', default='WARNING',
            help='Scrapy log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).'),
        parser.add_argument(
            '--dry-run', action='store_true', dest='dry_run', default=False,
            help='Bypass all the pipelines.')

    def _get_accounts(self, accounts):
        """Parse the `accounts` lists and convert it to dictionary."""
        return {
            spider: (uname, passwd) for (spider, uname, passwd) in accounts
        }

    def _get_spiders(self, scrapy, spiders):
        """Parse the `spiders` option and return a valid list of spider names.

        """
        all_spiders = scrapy.spider_list()
        spiders = spiders.split(',')
        if 'all' in spiders:
            spiders = all_spiders
        for name in spiders:
            if name not in all_spiders:
                raise CommandError('Spider %s not found.' % name)
        return spiders

    def _get_manga(self, spiders, manga=None, url=None):
        """Get a manga based on the name."""
        if len(spiders) > 1:
            raise CommandError('Please, specify a single source')
        spider = spiders[0]
        source = Source.objects.get(spider=spider)

        if not manga and not url:
            raise CommandError("Provide parameters 'manga' or 'url'")

        kwargs = {}
        if manga:
            kwargs['name'] = manga
        elif url:
            kwargs['url'] = url
        mangas = source.manga_set.filter(**kwargs)

        manga = None
        if len(mangas) > 1:
            self.stdout.write('Error. Found multiple mangas:')
            for manga in mangas:
                self.stdout.write('- %s' % manga)
            self.stdout.write('Please, choose one and try again')
            raise CommandError('Manga not found')
        elif not mangas:
            raise CommandError('Manga not found')

        manga = mangas[0]

        return manga

    def _get_issues(self, manga, issues=None, url=None, lang=None):
        """Give a list of issues from a manga."""
        lang = lang.upper() if lang else None
        source = manga.source
        source_langs = [l.language for l in source.sourcelanguage_set.all()]
        if lang not in source_langs:
            if len(source_langs) == 1 and not lang:
                lang = source_langs[0]
            elif lang:
                raise CommandError('Language %s not in %s' % (lang, source))
            else:
                raise CommandError(
                    'Please, set a valid language from %s' % source_langs)

        _issues = manga.issue_set.filter(language=lang)
        if issues == 'all':
            _issues = _issues.order_by('order')
        elif not issues and url:
            _issues = _issues.filter(url=url)
        elif issues:
            orders = []
            for order in issues.split(','):
                if '-' in order:
                    a, b = order.split('-')
                    if a >= b:
                        raise CommandError(
                            'Provide issue range in increasing order.')
                    orders.extend(range(int(a), int(b)+1))
                else:
                    orders.append(int(order))
            _issues = _issues.filter(order__in=orders).order_by('order')
        else:
            raise CommandError('Please, provide some issue numbers (order).')

        return _issues

    def _get_user_profile(self, username):
        """Get an User object from the email or the username."""
        user_profile = UserProfile.objects.filter(
            Q(user__username=username) |
            Q(user__email=username) |
            Q(email_kindle=username)
        )

        if not user_profile.exists():
            raise CommandError('User not found for %s' % username)
        elif user_profile.count() > 1:
            raise CommandError('Multiple users found for %s' % username)

        return user_profile.first()

    def handle(self, *args, **options):
        command = options['command']

        accounts = self._get_accounts(options['accounts'])
        loglevel = options['loglevel']
        dry_run = options['dry_run']

        # Create the ScrapyCtl object to store the CrawlerProcess.
        scrapy = ScrapyCtl(accounts, loglevel)

        # Get the list of spiders names that we are going to work with
        spiders = self._get_spiders(scrapy, options['spiders'])

        if command == 'list':
            self.list_spiders(spiders)
        elif command == 'update-genres':
            scrapy.update_genres(spiders, dry_run)
        elif command == 'update-catalog':
            scrapy.update_catalog(spiders, dry_run)
        elif command == 'update-collection':
            manga = options['manga']
            url = options['url']

            manga = self._get_manga(spiders, manga, url)
            scrapy.update_collection(spiders, manga.name, manga.url,
                                     dry_run)
        elif command == 'update-latest':
            until = options['until']

            if isinstance(until, str):
                until = datetime.datetime.strptime(until, '%d-%m-%Y').date()
            scrapy.update_latest(spiders, until, dry_run)
        elif command == 'search':
            manga = options['manga']
            lang = options['lang']
            details = options['details']
            self.search(spiders, manga, lang, details)
        elif command == 'subscribe':
            user = options['user']
            manga = options['manga']
            url = options['url']
            lang = options['lang']
            issues_per_day = options['issues-per-day']

            manga = self._get_manga(spiders, manga, url)
            self.subscribe(user, manga, lang, issues_per_day)
        elif command == 'send':
            issues = options['issues']
            manga = options['manga']
            url = options['url']
            lang = options['lang']
            username = options['user']
            do_not_send = options['do-not-send']

            # The URL can point to a manga or an issue, so we can use
            # safely in both calls
            manga = self._get_manga(spiders, manga, url)
            issues = self._get_issues(manga, issues, url, lang)
            user_profile = self._get_user_profile(username)
            self.send(issues, user_profile, accounts, loglevel, do_not_send)
        elif command == 'sendsub':
            utc_hour = timezone.now().hour
            user_profiles = []

            ignore_time = options['ignore-time']
            if options['user']:
                username = options['user']
                user_profile = self._get_user_profile(username)
                hour = (user_profile.send_at - user_profile.time_zone) % 24
                if ignore_time or utc_hour == hour:
                    user_profiles = [user_profile]
            else:
                user_profiles = UserProfile.objects.filter(
                    user__subscription__id__gt=0).distinct()
                if not ignore_time:
                    user_profiles = user_profiles.annotate(
                        hour=(24+F('send_at')-F('time_zone')) % 24
                    ).filter(hour=utc_hour)

            do_not_send = options['do-not-send']
            for user_profile in user_profiles:
                self.sendsub(user_profile, accounts, loglevel, do_not_send)
        elif command == 'retry':
            user_profiles = []

            if options['user']:
                username = options['user']
                user_profiles = [self._get_user_profile(username)]
            else:
                user_profiles = UserProfile.objects.filter(
                    user__subscription__id__gt=0).distinct()

            do_not_send = options['do-not-send']
            for user_profile in user_profiles:
                self.retry(user_profile, accounts, loglevel, do_not_send)
        else:
            raise CommandError('Not valid command value.')

        # Refresh the MATERIALIZED VIEW for full text search
        if command.startswith('update'):
            Manga.objects.refresh()

        # Print the SQL statistics in DEBUG mode
        if loglevel == 'DEBUG':
            queries = ['[%s]: %s' % (q['time'], q['sql'])
                       for q in connection.queries]
            logger.debug('\n'.join(queries))

    def list_spiders(self, spiders):
        """List current spiders than can be activated."""
        header = 'List of current spiders:'
        self.stdout.write(header)
        self.stdout.write('=' * len(header))
        self.stdout.write('')
        for name in spiders:
            enabled = False
            try:
                enabled = Source.objects.get(spider=name).enabled
            except Source.DoesNotExist:
                pass
            if enabled:
                self.stdout.write('- %s' % name)
            else:
                self.stdout.write('- %s (disabled)' % name)

    def search(self, spiders, manga, lang, details):
        """Search a manga in the database."""
        if not manga:
            raise CommandError("Parameter 'manga' is not optional")

        q = manga
        for name in spiders:
            header = 'Results from %s:' % name
            self.stdout.write(header)
            self.stdout.write('=' * len(header))
            self.stdout.write('')
            try:
                source = Source.objects.get(spider=name)
            except Source.DoesNotExist:
                pass
            for manga in source.manga_set.filter(name__icontains=q):
                self.stdout.write('- %s' % manga)
                issues = manga.issue_set
                if lang:
                    lang = lang.upper()
                    issues = issues.filter(language=lang)
                for issue in issues.order_by('order'):
                    if details:
                        self.stdout.write(' [%s] [%s] [%s] [%s] %s' %
                                          (issue.language,
                                           issue.order,
                                           issue.release,
                                           issue.url,
                                           issue.name))
                    else:
                        self.stdout.write(' [%s] [%s] %s' %
                                          (issue.language,
                                           issue.order,
                                           issue.name))
                self.stdout.write('')

    def subscribe(self, user, manga, lang, issues_per_day):
        """Subscribe an user to a manga."""
        user_profile = UserProfile.objects.get(user__username=user)
        if lang:
            lang = lang.upper()

        manga.subscribe(user_profile.user, lang, issues_per_day)

    def send(self, issues, user_profile, accounts, loglevel, do_not_send):
        """Send a list of issues to an user."""

        user = user_profile.user
        if do_not_send:
            # If the user have a subscription but we are not sending
            # issues, mark them as sent
            try:
                for issue in issues:
                    subscription = Subscription.actives.get(
                        user=user, manga=issue.manga)
                    self.stdout.write("Marking '%s' as sent" % issue)
                    subscription.add_sent(issue)
            except Exception:
                msg = 'The user %s does not have a '\
                      'subscription to %s' % (user, issue.manga)
                self.stdout.write(msg)
        else:
            send(issues, user, accounts, loglevel)

    def sendsub(self, user_profile, accounts, loglevel, do_not_send):
        """Prepare the daily subscriptions to an user."""
        user = user_profile.user

        # Basic algorithm:
        #
        #   * Get the number of issues processed during the last 24hs
        #     for an user, and calculate the remaining number of
        #     issues to send to this user.
        #
        #   * Get the list of subscriptions for this user in random
        #     order (for sources that are active).
        #
        #   * For each subcription, get the list of issues that can be
        #     sent for this user today. This calculation is done in
        #     `Subscription.issues_to_send()`
        #
        remains = user_profile.remains()

        issues = []
        subscriptions = user.subscription_set(manager='actives')\
                            .filter(manga__source__enabled=True)\
                            .order_by('?')
        for subscription in subscriptions:
            for issue in subscription.issues_to_send():
                # Exit if we reach the limit for today
                if remains <= 0:
                    break
                # Increment the retry counter if the result was FAILED
                issue.retry_if_failed(user)
                issues.append(issue)
                remains -= 1

        self.send(issues, user_profile, accounts, loglevel, do_not_send)

    def retry(self, user_profile, accounts, loglevel, do_not_send):
        """Retry the failing send to an user."""
        user = user_profile.user

        issues = []
        subscriptions = user.subscription_set(manager='actives')\
                            .filter(manga__source__enabled=True)
        for subscription in subscriptions:
            for issue in subscription.issues_to_retry():
                # Increment the retry counter if the result was FAILED
                issue.retry_if_failed(user)
                issues.append(issue)

        self.send(issues, user_profile, accounts, loglevel, do_not_send)
