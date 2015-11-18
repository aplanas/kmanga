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

logger = logging.getLogger(__name__)


class SmartProxy(object):

    def __init__(self, settings):
        self.error_codes = {
            int(x) for x in settings.getlist('SMART_PROXY_ERROR_CODES')
        }
        self.retry_error_codes = {
            int(x) for x in settings.getlist('RETRY_HTTP_CODES')
        }

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_request(self, request, spider):
        # The proxy only works if the operation is fetch an issue
        if not hasattr(spider, '_operation') or spider._operation != 'manga':
            return

        # If the proxy is already set, we are done
        if 'proxy' in request.meta:
            return

        if needs_proxy(spider.name):
            proxy = Proxy.objects.filter(source__spider=spider.name)
            proxy = proxy.order_by('?').first()
            if proxy:
                logger.info('Using proxy <%s> for request' % proxy)
                request.meta['proxy'] = 'http://%s' % proxy.proxy
                # Disable redirection when a proxy is in use
                request.meta['dont_redirect'] = True
            else:
                logger.error('No proxy found for %s' % spider.name)

    def process_response(self, request, response, spider):
        if 'proxy' in request.meta:
            if response.status in self.retry_error_codes:
                self._delete_proxy_from_request(request, spider)
            elif response.status in self.error_codes:
                # If the status is one of the error codes that is not
                # in the retry error code, we need to map as one of
                # them, like HTTP 500
                response.status = 500
                self._delete_proxy_from_request(request, spider)
            elif not response.body:
                # If the body is empty, we consider it as a proxy
                # error with HTTP error code 500.  This solution will
                # trigger another retry with a different proxy
                response.status = 500
                self._delete_proxy_from_request(request, spider)
        return response

    def process_exception(self, request, exception, spider):
        if 'proxy' in request.meta:
            self._delete_proxy_from_request(request, spider)

    def _delete_proxy_from_request(self, request, spider):
        proxy = request.meta['proxy'].lstrip('htp:/')
        del request.meta['proxy']
        try:
            proxy = Proxy.objects.get(proxy=proxy, source__spider=spider.name)
            logger.warning('Removing failed proxy <%s>, %d proxies left' % (
                proxy, Proxy.objects.count()))
            proxy.delete()
        except Proxy.DoesNotExist:
            pass
