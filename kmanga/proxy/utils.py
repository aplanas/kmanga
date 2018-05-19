import gzip
import io
import itertools
import logging
import re
import urllib.error
import urllib.parse
import urllib.request
from multiprocessing.pool import ThreadPool

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
    # 'mangafox': {
    #     URL: 'http://fanfox.net/manga/sailor_moon/v01/c001/1.html',
    #     VALID: [
    #         '<select onchange="change_page(this)" class="m">',
    #         '/store/manga/203/01-001.0/compressed/f000.jpg',
    #     ],
    #     INVALID: None
    # },
}

# List of URLs that contains proxy lists and the decoder
PROXY_SOURCE = [
    ('http://www.httptunnel.ge/ProxyListForFree.aspx', 'plain'),
    ('http://txt.proxyspy.net/proxy.txt', 'plain'),
    ('http://proxytime.ru/http', 'plain'),
    ('http://marcosbl.com/lab/proxies/', 'plain'),
    ('http://aliveproxies.com/pages/page-scrapebox-proxies/', 'plain'),
    ('http://www.cybersyndrome.net/pla.html?guid=ON', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-2.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-3.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-4.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-5.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-6.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-7.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-8.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-9.html', 'plain'),
    ('http://www.my-proxy.com/free-proxy-list-10.html', 'plain'),
    ('http://proxy-ip-list.com/', 'plain'),
    ('http://proxy-ip-list.com/free-usa-proxy-ip.html', 'plain'),
    ('http://proxy-ip-list.com/free-uk-proxy-list.html', 'plain'),
    ('http://proxy-ip-list.com/proxy-list-port-3128.html', 'plain'),
    ('http://proxy-ip-list.com/proxy-8080.html', 'plain'),
    ('http://proxy-ip-list.com/fresh-proxy-list.html', 'plain'),
    ('http://proxy-ip-list.com/download/free-proxy-list.txt', 'plain'),
    ('http://proxy-ip-list.com/download/proxy-list-port-3128.txt', 'plain'),
    ('http://proxy-ip-list.com/download/free-usa-proxy-ip.txt', 'plain'),
    ('http://proxy-ip-list.com/download/free-uk-proxy-list.txt', 'plain'),
    ('http://www.proxylists.net/proxylists.xml', 'xml'),
    ('http://www.proxyrss.com/proxylists/all.gz', 'gz'),
    ('http://www.proxz.com/proxylists.xml', 'xml'),
]


def update_proxy():
    """Collect new proxies and return validation array."""
    collector = {
        'plain': _collect_proxies_plain,
        'xml': _collect_proxies_xml,
        'gz': _collect_proxies_gz,
    }

    proxies = []
    for url, kind in PROXY_SOURCE:
        proxies.extend(collector[kind](url))
    # Remove duplicates and localhost references
    proxies = list(set(proxies)-{'127.0.0.1'})
    return check_proxy(proxies)


def check_proxy(proxies):
    """Return validation array for a list of proxies."""
    pool = ThreadPool(processes=512)
    proxy_source = itertools.product(proxies, PROXY_MAP)
    return [p for p in pool.imap(_is_valid_proxy, proxy_source) if p]


def needs_proxy(spider):
    """Return True if the spider needs a proxy to work."""
    return spider in PROXY_MAP


def _get_url(url, as_string=True):
    """Get the content from a URL."""
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64; rv:49.0) '\
                 'Gecko/20100101 Firefox/49.0'
    request = urllib.request.Request(url)
    request.add_header('User-Agent', user_agent)
    body = ''
    try:
        body = urllib.request.urlopen(request).read()
        if as_string:
            body = body.decode('utf-8')
    except Exception:
        logger.warning('Fail URL %s' % url)
    return body


def _collect_proxies_plain(url):
    """Generate a list of proxies from different sources."""
    logger.info('Collecting proxies (plain) from %s' % url)
    proxy_re = re.compile(r'((?:\d{1,3}.){3}\d{1,3}:\d{1,4})')
    return proxy_re.findall(_get_url(url))


def _collect_proxies_xml(url):
    """Generate a lost of proxies from XML."""
    logger.info('Collecting proxies (XML) from %s' % url)
    proxy_re = re.compile(
        r'<prx:ip>((?:\d{1,3}.){3}\d{1,3})</prx:ip>'
        r'<prx:port>(\d{1,4})</prx:port>')
    body = _get_url(url)
    return ['%s:%s' % (ip, port) for ip, port in proxy_re.findall(body)]


def _collect_proxies_gz(url):
    """Generate a lost of proxies from gzip file."""
    logger.info('Collecting proxies (gzip) from %s' % url)
    body = io.BytesIO(_get_url(url, as_string=False))
    body = gzip.open(body).read().decode('utf-8')
    proxy_re = re.compile(r'((?:\d{1,3}.){3}\d{1,3}:\d{1,4})')
    return proxy_re.findall(body)


def _is_valid_proxy(proxy_source):
    """Check if is a valid proxy for a specific Source."""
    proxy, source = proxy_source

    _proxy = urllib.request.ProxyHandler({'http': proxy})
    opener = urllib.request.build_opener(_proxy)

    test = PROXY_MAP[source]
    url, valid, invalid = test[URL], test[VALID], test[INVALID]

    if source in VHOST:
        parse = urllib.parse.urlparse(url)
        netloc = parse.netloc
        url = parse._replace(netloc=VHOST[source]).geturl()
        req = urllib.request.Request(url)
        req.add_unredirected_header('Host', netloc)
    else:
        req = urllib.request.Request(url)

    try:
        response = opener.open(req, timeout=TIMEOUT)
        if response.info().get('Content-Encoding') == 'gzip':
            body = io.BytesIO(response.read())
            body = gzip.open(body).read().decode('utf-8')
        else:
            body = response.read().decode('utf-8')
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
