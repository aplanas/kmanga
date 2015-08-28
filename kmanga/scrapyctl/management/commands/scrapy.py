from __future__ import absolute_import

import datetime
import logging
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import connection

from core.models import History
from core.models import Manga
from core.models import Source
from core.models import Subscription
from registration.models import UserProfile
from scrapyctl.scrapyctl import ScrapyCtl

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # Parameters used by some commands
        make_option(
            '-m', '--manga', action='store', dest='manga', default=None,
            help='Name of the manga. Partial match for search (<manga>).'),
        make_option(
            '--issues', action='store', dest='issues', default=None,
            help='List of issues numbers (<list_of_numbers|all>).'),
        make_option(
            '--url', action='store', dest='url', default=None,
            help='Manga or issue URL (<url>).'),
        make_option(
            '--lang', action='store', dest='lang', default=None,
            help='Language of the manga (<EN|ES>).'),
        make_option(
            '--details', action='store_true', dest='details', default=False,
            help='Add more details in the list of mangas.'),
        make_option(
            '--until', action='store', dest='until',
            default=datetime.date.today(),
            help='Until parameter to latest update (<DD-MM-YYYY>).'),
        make_option(
            '--issues-per-day', action='store', dest='issues-per-day',
            default=4,
            help='Number of issues to send per day (<number>).'),
        make_option(
            '--do-not-send', action='store_true', dest='do-not-send',
            default=False,
            help='Avoid the send of the manga, but register the send.'),
        make_option(
            '--user', action='store', dest='user', default=None,
            help='User name for the subscription (<user>).'),
        make_option(
            '--from', action='store', dest='from', default=None,
            help='Email address from where to send the issue (<email>).'),
        make_option(
            '--to', action='store', dest='to', default=None,
            help='Email address or user to send the issue (<email|user>).'),

        # General parameters
        make_option(
            '--spiders', action='store', dest='spiders', default='all',
            help='List of spiders (<list_of_spiders|all>).'),
        make_option(
            '--loglevel', action='store', dest='loglevel', default='INFO',
            help='Scrapy log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).'),
        make_option(
            '--dry-run', action='store_true', dest='dry-run', default=False,
            help='Bypass all the pipelines.'),
        )
    help = 'Launch scrapy spiders from command line.'
    commands = [
        'list',
        'update-genres',
        'update-catalog',
        'update-collection',
        'update-latest',
        'search',
        'subscribe',
        'send',
        'sendsub',
    ]
    args = '|'.join(commands)

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
        source = Source.objects.get(name=spider)

        if not manga and not url:
            raise CommandError("Provide parameters 'manga' or 'url'")

        kwargs = {}
        if manga:
            kwargs['name'] = manga
        if url:
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
            _issues = _issues.order_by('number')
        elif not issues and url:
            _issues = _issues.filter(url=url)
        elif issues:
            numbers = []
            for number in issues.split(','):
                if '-' in number:
                    a, b = number.split('-')
                    if a >= b:
                        raise CommandError(
                            'Provide issue range in increasin order.')
                    numbers.extend(range(int(a), int(b)+1))
                else:
                    numbers.append(float(number))
            _issues = _issues.filter(number__in=numbers).order_by('number')
        else:
            raise CommandError('Please, provide some issue numbers.')

        return _issues

    def handle(self, *args, **options):
        if not args or len(args) > 1:
            msg = 'Please, provide one command: %s' % Command.args
            raise CommandError(msg)
        command = args[0]

        loglevel = options['loglevel']
        dry_run = options['dry-run']

        # Create the ScrapyCtl object to store the CrawlerProcess.
        scrapy = ScrapyCtl(loglevel)

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

            if isinstance(until, basestring):
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
            _from = options['from']
            to = options['to']
            do_not_send = options['do-not-send']

            # The URL can point to a manga or an issue, so we can use
            # safely in both calls
            manga = self._get_manga(spiders, manga, url)
            issues = self._get_issues(manga, issues, url, lang)
            self.send(scrapy, spiders, manga, issues, _from, to,
                      do_not_send)
        elif command == 'sendsub':
            if options['user']:
                username = options['user']
                user_profile = UserProfile.objects.get(user__username=username)
                user_profiles = [user_profile]
            else:
                user_profiles = UserProfile.objects.filter(
                    user__subscription__id__gt=0).distinct()
            do_not_send = options['do-not-send']
            for user_profile in user_profiles:
                try:
                    self.sendsub(scrapy, user_profile, do_not_send)
                except Exception as e:
                    msg = 'Error sending subscription for %s' % user_profile
                    logger.error(msg)
                    logger.error(e)
        else:
            raise CommandError('Not valid command value. '
                               'Please, provide a command: %s' % Command.args)

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
            self.stdout.write('- %s' % name)

    def search(self, spiders, manga, lang, details):
        """Search a manga in the database."""
        q = manga
        for name in spiders:
            header = 'Results from %s:' % name
            self.stdout.write(header)
            self.stdout.write('=' * len(header))
            self.stdout.write('')
            source = Source.objects.get(spider=name)
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

    def subscribe(self, user, manga, lang, issues_per_day):
        """Subscribe an user to a manga."""
        user_profile = UserProfile.objects.get(user__username=user)
        if lang:
            lang = lang.upper()

        manga.subscribe(user_profile.user, lang, issues_per_day)

    def send(self, scrapy, spiders, manga, issues, _from, to,
             do_not_send):
        """Send a list of issues to an user."""
        if isinstance(issues, list):
            numbers, urls = zip(*[(i.number, i.url) for i in issues])
        else:
            numbers, urls = zip(*issues.values_list('number', 'url'))

        _from = _from if _from else settings.KMANGA_EMAIL
        if not to:
            raise CommandError("Parameter 'to' is not optional")

        user_profile = None
        if '@' in to:
            user_profile = UserProfile.objects.get(email_kindle=to)
        else:
            user_profile = UserProfile.objects.get(user__username=to)

        if not user_profile:
            raise CommandError('User not found for %s' % to)

        if do_not_send:
            # If the user have a subscription, mark the issues as sent
            user = user_profile.user
            try:
                subscription = user.subscription_set.get(manga=manga)
            except:
                msg = 'The user %s do not have a subscription to %s' % (user,
                                                                        manga)
            else:
                self.stdout.write(msg)
                for issue in issues:
                    # TODO XXX - Remove `unicode` in Python 3
                    self.stdout.write("Marked '%s' as sent" % unicode(issue))
                    subscription.add_sent(issue)
        else:
            scrapy._send(spiders[0], manga.name, numbers, urls, _from,
                         user_profile.email_kindle)

    def sendsub(self, scrapy, user_profile, do_not_send):
        """Send the daily subscriptions to an user."""
        user = user_profile.user

        # Basic algorithm:
        #
        #   * Get the number of issues sent during the last 24hs for
        #     an user, and calculate the remaining number of issues to
        #     send to this user.
        #
        #   * Get the list of subscriptions for this user in random
        #     order.
        #
        #   * For each subcription, get the number of issues sent
        #     during the last 24hs, and calculate the number of issues
        #     that can be sent for this user today. This calculation
        #     is done in `Subscription.issues_to_send()`

        already_sent = History.objects.sent_last_24hs(user)
        remains = max(0, user_profile.issues_per_day-already_sent)

        issues = []
        for subscription in user.subscription_set.order_by('?'):
            for issue in subscription.issues_to_send():
                # Exit if we reach the limit for today
                if remains <= 0:
                    break
                issues.append(issue)
                remains -= 1

        # Reverse the order of issues to send. This will help when the
        # MOBI arrives to the Kindle for ordering.
        issues.reverse()

        if do_not_send:
            # If the user have a subscription but we are not sending
            # issues, mark them as sent
            user = user_profile.user
            try:
                for issue in issues:
                    subscription = Subscription.active.get(
                        user=user, manga=issue.manga)
                    self.stdout.write("Marking '%s' as sent" % issue)
                    subscription.add_sent(issue)
            except:
                msg = 'The user %s do not have a '\
                      'subscription to %s' % (user, issue.manga)
                self.stdout.write(msg)
        elif issues:
            scrapy.send(issues, user)
