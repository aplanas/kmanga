import gzip
import itertools
import logging
from multiprocessing.pool import ThreadPool
import re
import StringIO
import urllib2
import urlparse

logger = logging.getLogger(__name__)

URL = 'URL'
VALID = 'VALID'
INVALID = 'INVALID'

TIMEOUT = 5

# Virtual Host table
VHOST = {
    # 'spider_name': 'real_ip',
}

# To be a valid proxy, all the text in the VALID array needs to be in
# the body, and not one of the INVALID text needs to be present (if
# there is one, it will be considered as an invalid proxy)
PROXY_MAP = {
    'mangafox': {
        URL: 'http://mangafox.me/manga/sailor_moon/v01/c001/1.html',
        VALID: [
            '<select onchange="change_page(this)" class="m">',
            'mfcdn.net/store/manga/203/01-001.0/compressed/f000.jpg',
        ],
        INVALID: None
    },
}

# List of URLs that contains proxy lists
PROXY_SOURCE = [
    'http://www.httptunnel.ge/ProxyListForFree.aspx',
    'http://socks24.ru/proxy/httpProxies.txt',
    'http://txt.proxyspy.net/proxy.txt',
    'http://www.therealist.ru/proksi/spisok-elitnyx-proksi-serverov',
    'http://uks.pl.ua/script/getproxy.php?last',
    'http://proxytime.ru/http',
    'http://marcosbl.com/lab/proxies/',
    'http://aliveproxies.com/pages/page-scrapebox-proxies/',
    'http://www.cybersyndrome.net/pla.html?guid=ON',
    'http://www.x-scripts.com/proxy.php',
    'http://www.shroomery.org/ythan/proxylist.php',
    'http://www.my-proxy.com/free-proxy-list.html',
    'http://www.my-proxy.com/free-proxy-list-2.html',
    'http://www.my-proxy.com/free-proxy-list-3.html',
    'http://www.my-proxy.com/free-proxy-list-4.html',
    'http://www.my-proxy.com/free-proxy-list-5.html',
    'http://www.my-proxy.com/free-proxy-list-6.html',
    'http://www.my-proxy.com/free-proxy-list-7.html',
    'http://www.my-proxy.com/free-proxy-list-8.html',
    'http://www.my-proxy.com/free-proxy-list-9.html',
    'http://www.my-proxy.com/free-proxy-list-10.html',
    'http://proxy-ip-list.com/',
]


def update_proxy():
    """Collect new proxies and return validation array."""
    proxies = _collect_proxies()
    return check_proxy(proxies)


def check_proxy(proxies):
    """Return validation array for a list of proxies."""
    pool = ThreadPool(processes=512)
    proxy_source = itertools.product(proxies, PROXY_MAP)
    return [p for p in pool.imap(_is_valid_proxy, proxy_source) if p]


def needs_proxy(spider):
    """Return True if the spider needs a proxy to work."""
    return spider in PROXY_MAP


def _collect_proxies():
    """Generate a list of proxies from different sources."""
    proxy_re = re.compile(r'((?:\d{1,3}.){3}\d{1,3}:\d{1,4})')
    proxies = []
    for url in PROXY_SOURCE:
        logger.info('Collecting proxies from %s' % url)
        try:
            body = urllib2.urlopen(url).read()
            proxies.extend(proxy_re.findall(body))
        except Exception:
            logger.warning('Fail URL %s' % url)
    return list(set(proxies)-set(('127.0.0.1',)))


def _is_valid_proxy(proxy_source):
    """Check if is a valid proxy for a specific Source."""
    proxy, source = proxy_source

    _proxy = urllib2.ProxyHandler({'http': proxy})
    opener = urllib2.build_opener(_proxy)

    test = PROXY_MAP[source]
    url, valid, invalid = test[URL], test[VALID], test[INVALID]

    if source in VHOST:
        parse = urlparse.urlparse(url)
        netloc = parse.netloc
        url = parse._replace(netloc=VHOST[source]).geturl()
        req = urllib2.Request(url)
        req.add_unredirected_header('Host', netloc)
    else:
        req = urllib2.Request(url)

    try:
        response = opener.open(req, timeout=TIMEOUT)
        if response.info().get('Content-Encoding') == 'gzip':
            body = StringIO.StringIO(response.read())
            body = gzip.GzipFile(fileobj=body).read()
        else:
            body = response.read()
    except Exception:
        return None

    if valid and invalid:
        is_valid = all(i in body for i in valid)
        is_valid = is_valid and not any(i in body for i in invalid)
    elif valid:
        is_valid = all(i in body for i in valid)
    elif invalid:
        is_valid = not any(i in body for i in invalid)
    else:
        is_valid = False
    if is_valid:
        return (proxy, source)
