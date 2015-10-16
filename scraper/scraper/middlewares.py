# -*- coding: utf-8 -*-
#
# (c) 2015 Alberto Planas <aplanas@gmail.com>
#
# This file is part of KManga.
#
# KManga is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# KManga is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with KManga.  If not, see <http://www.gnu.org/licenses/>.

import logging

from proxy.models import Proxy
from proxy.utils import needs_proxy

# https://docs.djangoproject.com/en/dev/releases/1.8/#standalone-scripts
import django
django.setup()


class SmartProxy(object):

    def process_request(self, request, spider):
        # The proxy only works if the operation is fetch an issue
        if spider._operation != 'manga':
            return

        # If the proxy is already set, we are done
        if 'proxy' in request.meta:
            return

        if needs_proxy(spider.name):
            proxy = Proxy.objects.filter(source__spider=spider.name)
            proxy = proxy.order_by('?').first()
            if proxy:
                logging.info('Using proxy <%s> for request' % proxy)
                request.meta['proxy'] = 'http://%s' % proxy.proxy
            else:
                logging.error('No proxy found for %s' % spider.name)

    def process_exception(self, request, exception, spider):
        if 'proxy' not in request.meta:
            return

        proxy = request.meta['proxy'].lstrip('htp:/')
        del request.meta['proxy']
        try:
            proxy = Proxy.objects.get(proxy=proxy, source__spider=spider.name)
            logging.warning('Removing failed proxy <%s>, %d proxies left' % (
                proxy, Proxy.objects.count()))
            proxy.delete()
        except Proxy.DoesNotExist:
            pass
