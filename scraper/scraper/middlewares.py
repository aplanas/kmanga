# -*- coding: utf-8 -*-
#
# (c) 2016 Alberto Planas <aplanas@gmail.com>
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
import os.path
import re
from urlparse import urlparse

import django
django.setup()

from proxy.models import Proxy
from proxy.utils import needs_proxy

logger = logging.getLogger(__name__)


class RetryPartial(object):
    """Middleware to consider partial results as errors."""
    def __init__(self, settings):
        self.error_codes = {
            int(x) for x in settings.getlist('SMART_PROXY_ERROR_CODES')
        }

    @classmethod
    def from_crawler(cls, crawler):
        return cls(crawler.settings)

    def process_response(self, request, response, spider):
        logger.debug('Process respose - url: %s, status: %s, '
                     'flags: %s' % (request.url, response.status,
                                    response.flags))

        is_partial = 'partial' in response.flags
        if is_partial and response.status not in self.error_codes:
            # Partial results, not considered as errors, are marked as
            # incorrect.
            logger.debug('Partial result - url: %s' % request.url)
            response.status = 500
        return response


class SmartProxy(object):
    """Middleware to add a proxy to certain requests."""
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
        # The proxy only works if the operation is fetch an issue or a
        # commection
        has_operation = hasattr(spider, '_operation')
        operations = ('catalog', 'collection', 'latest', 'manga')
        if not has_operation or spider._operation not in operations:
            return

        logger.debug('Process request - proxy: %s, url: %s' % (
            request.meta['proxy'] if 'proxy' in request.meta else 'no',
            request.url))

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
            logger.debug('Process respose - proxy: %s, url: %s, '
                         'status: %s, flags: %s' % (
                             request.meta['proxy'], request.url,
                             response.status, response.flags))

            if response.status in self.retry_error_codes:
                self._delete_proxy_from_request(request, spider)
            elif response.status in self.error_codes:
                # Some of the error codes are redirects, we need to
                # check if this a valid redirect, to maintain the
                # proxy and enable the redirect.
                redirect = response.headers.get('Location', None)
                valid = self._valid_redirect(response.status,
                                             request.url,
                                             redirect)
                if valid:
                    logger.debug('Valid redirect - proxy: %s, from: %s, '
                                 'to: %s, status: %s' % (
                                     request.meta['proxy'],
                                     request.url, redirect,
                                     response.status))
                    # If valid, re-enable redirection
                    if 'dont_redirect' in request.meta:
                        del request.meta['dont_redirect']
                else:
                    # If the status is one of the error codes that is
                    # not in the retry error code, we need to map as
                    # one of them, like HTTP 500.
                    logger.debug('Invalid redirect - proxy: %s, from: %s, '
                                 'to: %s, status: %s' % (
                                     request.meta['proxy'],
                                     request.url, redirect,
                                     response.status))
                    self._map_status_error(response)
                    self._delete_proxy_from_request(request, spider)
        return response

    def process_exception(self, request, exception, spider):
        if 'proxy' in request.meta:
            logger.debug('Process exception - proxy: %s, url: %s, '
                         'exception: %s' % (request.meta['proxy'],
                                            request.url, exception))
            self._delete_proxy_from_request(request, spider)

    def _map_status_error(self, response):
        """Set status code as 500 and remove the Content-Encoding."""
        # Some proxies set the Content-Encoding section for partial
        # results, or redirects (that do not containt data).  This can
        # cause problems in the httpcompression middleware.
        response.status = 500
        if 'Content-Encoding' in response.headers:
            del response.headers['Content-Encoding']

    def _delete_proxy_from_request(self, request, spider):
        proxy = request.meta['proxy'].lstrip('htp:/')
        del request.meta['proxy']
        try:
            proxy = Proxy.objects.get(proxy=proxy, source__spider=spider.name)
            logger.warning('Removing failed proxy <%s>, %d proxies left' % (
                proxy, Proxy.objects.filter(
                    source__spider=spider.name).count()))
            proxy.delete()
        except Proxy.DoesNotExist:
            pass

    def _valid_redirect(self, status, url_from, url_to):
        """Implement some heuristics to detect valid redirections."""
        # Check that status code is a redirection
        if not 300 <= status < 400:
            return False

        # Same domain check
        bn_from = os.path.basename(urlparse(url_from).path)
        bn_to = os.path.basename(urlparse(url_to).path)
        if bn_from != bn_to:
            return False

        # Ends in .html check
        if not url_to.endswith('.html'):
            return False

        return True


class VHost(object):
    """Middleware to replace the host name with the IP."""

    def process_request(self, request, spider):
        """Replace the host name with the IP."""
        if hasattr(spider, 'vhost_ip'):
            domain = spider.allowed_domains[0]
            ip = spider.vhost_ip
            url = re.sub(r'(www.)?%s' % domain, ip, request.url)
            # During the second pass, both URL are the same (there is
            # not replacement)
            if request.url != url:
                request = request.replace(url=url, headers={'Host': domain})
                return request

    def process_response(self, request, response, spider):
        """Replace back the IP with the host name."""
        if hasattr(spider, 'vhost_ip'):
            domain = spider.allowed_domains[0]
            ip = spider.vhost_ip
            url = re.sub(ip, domain, response.url)
            response = response.replace(url=url)
        return response
