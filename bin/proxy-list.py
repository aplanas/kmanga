#!/usr/bin/env python
from multiprocessing.pool import ThreadPool
import re
import urllib2


PROXY_LIST = [
    'http://txt.proxyspy.net/proxy.txt',
    # 'http://alexa.lr2b.com/proxylist.txt',
]
TEST_URL = 'http://submanga.com/c/139702'
TEST_YES = 'paginadora'
TEST_NO = 'Hemos eliminado'

TIMEOUT = 5


def is_valid_proxy(proxy):
    """Check if is a valid proxy, using a URL for test."""
    _proxy = urllib2.ProxyHandler({'http': proxy})
    opener = urllib2.build_opener(_proxy)
    try:
        html = opener.open(TEST_URL, timeout=TIMEOUT).read()
    except Exception:
        return None
    if TEST_YES in html and TEST_NO not in html:
        return proxy


if __name__ == '__main__':
    proxy_re = re.compile(r'((?:\d{1,3}.){3}\d{1,3}:\d{1,4})')
    plst = []
    for proxy_list in PROXY_LIST:
        for line in urllib2.urlopen(proxy_list):
            match = proxy_re.match(line)
            if match:
                plst.append(match.group(1))

    pool = ThreadPool(processes=255)
    for p in pool.imap(is_valid_proxy, plst):
        if p:
            print p
