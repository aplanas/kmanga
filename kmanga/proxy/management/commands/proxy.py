from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from core.models import Source
from proxy.models import Proxy
from proxy.utils import check_proxy
from proxy.utils import logger
from proxy.utils import needs_proxy
from proxy.utils import update_proxy
from scrapyctl.scrapyctl import ScrapyCtl


class Command(BaseCommand):
    help = 'Process proxies for spiders from command line.'

    def add_arguments(self, parser):
        parser.add_argument('command', choices=[
            'list',
            'update-proxy',
        ], help='Command to execute')

        parser.add_argument(
            '-c', '--clean', action='store_true', dest='clean', default=False,
            help='Remove broken proxies from the database.')
        # General parameters
        parser.add_argument(
            '--loglevel', action='store', dest='loglevel', default='WARNING',
            help='Log level (<CRITICAL|ERROR|WARNING|INFO|DEBUG>).')

    def handle(self, *args, **options):
        command = options['command']

        loglevel = options['loglevel']
        logger.setLevel(loglevel)

        if command == 'list':
            scrapy = ScrapyCtl(None, loglevel)
            self._list_spiders(scrapy)
        elif command == 'update-proxy':
            clean = options['clean']
            self._update_proxy(clean)
        else:
            raise CommandError('Not valid command value.')

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

    def _update_proxy(self, clean):
        """Get the list of valid proxies and update the model."""
        if clean:
            proxies = Proxy.objects.values_list('proxy', flat=True)
            proxies = set(check_proxy(proxies))
            for proxy in Proxy.objects.all():
                if (proxy.proxy, proxy.source.spider) not in proxies:
                    proxy.delete()

        # Recover new proxies
        proxies = update_proxy()
        self.stdout.write('Found %s valid proxies' % len(proxies))
        for proxy, spider in proxies:
            source = Source.objects.get(spider=spider)
            Proxy.objects.get_or_create(proxy=proxy, source=source)
        total = Proxy.objects.all().count()
        self.stdout.write('Number of proxies in the database: %s' % total)
