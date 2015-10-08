from __future__ import absolute_import

from optparse import make_option

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from core.models import Source
from proxy.models import Proxy
from proxy.utils import logger
from proxy.utils import needs_proxy
from proxy.utils import update_proxy
from scrapyctl.scrapyctl import ScrapyCtl


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        # General parameters
        make_option(
            '--loglevel', action='store', dest='loglevel', default='WARNING',
            help='Log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).'),
        )
    help = 'Process proxies for spiders from command line.'
    commands = [
        'list',
        'update-proxy',
    ]
    args = '|'.join(commands)

    def handle(self, *args, **options):
        if not args or len(args) > 1:
            msg = 'Please, provide one command: %s' % Command.args
            raise CommandError(msg)
        command = args[0]

        loglevel = options['loglevel']
        logger.setLevel(loglevel)

        if command == 'list':
            scrapy = ScrapyCtl(loglevel)
            self._list_spiders(scrapy)
        elif command == 'update-proxy':
            self._update_proxy()
        else:
            raise CommandError('Not valid command value. '
                               'Please, provide a command: %s' % Command.args)

    def _list_spiders(self, scrapy):
        """List current spiders than can be activated."""
        header = 'List of current spiders:'
        spiders = scrapy.spider_list()

        self.stdout.write(header)
        self.stdout.write('=' * len(header))
        self.stdout.write('')
        for spider in spiders:
            if needs_proxy(spider):
                self.stdout.write('- %s (PROXY)' % spider)
            else:
                self.stdout.write('- %s' % spider)

    def _update_proxy(self):
        """Get the list of valid proxies and update the model."""
        proxies = update_proxy()
        self.stdout.write('Found %s valid proxies' % len(proxies))
        for proxy, spider in proxies:
            source = Source.objects.get(spider=spider)
            Proxy.objects.get_or_create(proxy=proxy, source=source)
        total = Proxy.objects.all().count()
        self.stdout.write('Number of proxies in the database: %s' % total)
