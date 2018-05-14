# -*- coding: utf-8 -*-

# Scrapy settings for scraper project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#     http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#     http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html

BOT_NAME = 'scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'


# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scraper (+http://www.yourdomain.com)'

# Configure maximum concurrent requests performed by Scrapy (default: 16)
#CONCURRENT_REQUESTS=32

# Configure a delay for requests for the same website (default: 0)
# See http://scrapy.readthedocs.org/en/latest/topics/settings.html#download-delay
# See also autothrottle settings and docs
#DOWNLOAD_DELAY=3
# The download delay setting will honor only one of:
#CONCURRENT_REQUESTS_PER_DOMAIN=16
#CONCURRENT_REQUESTS_PER_IP=16

# Disable cookies (enabled by default)
#COOKIES_ENABLED=False

# Disable Telnet Console (enabled by default)
#TELNETCONSOLE_ENABLED=False

# Override the default request headers:
#DEFAULT_REQUEST_HEADERS = {
#   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#   'Accept-Language': 'en',
#}

# Enable or disable spider middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/spider-middleware.html
#SPIDER_MIDDLEWARES = {
#    'scraper.middlewares.MyCustomSpiderMiddleware': 543,
#}

# Enable or disable downloader middlewares
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html
#DOWNLOADER_MIDDLEWARES = {
#    'scraper.middlewares.MyCustomDownloaderMiddleware': 543,
#}

# Enable or disable extensions
# See http://scrapy.readthedocs.org/en/latest/topics/extensions.html
#EXTENSIONS = {
#    'scrapy.telnet.TelnetConsole': None,
#}

# Configure item pipelines
# See http://scrapy.readthedocs.org/en/latest/topics/item-pipeline.html
#ITEM_PIPELINES = {
#    'scraper.pipelines.SomePipeline': 300,
#}

# Enable and configure the AutoThrottle extension (disabled by default)
# See http://doc.scrapy.org/en/latest/topics/autothrottle.html
# NOTE: AutoThrottle will honour the standard settings for concurrency and delay
#AUTOTHROTTLE_ENABLED=True
# The initial download delay
#AUTOTHROTTLE_START_DELAY=5
# The maximum download delay to be set in case of high latencies
#AUTOTHROTTLE_MAX_DELAY=60
# Enable showing throttling stats for every response received:
#AUTOTHROTTLE_DEBUG=False

# Enable and configure HTTP caching (disabled by default)
# See http://scrapy.readthedocs.org/en/latest/topics/downloader-middleware.html#httpcache-middleware-settings
#HTTPCACHE_ENABLED=True
#HTTPCACHE_EXPIRATION_SECS=0
#HTTPCACHE_DIR='httpcache'
#HTTPCACHE_IGNORE_HTTP_CODES=[]
#HTTPCACHE_STORAGE='scrapy.extensions.httpcache.FilesystemCacheStorage'


# KManga specific configuration

import os.path

# Retry many times since proxies often fail
RETRY_TIMES = 10
# Retry on most error codes since proxies fail for different reasons
RETRY_HTTP_CODES = [500, 502, 503, 400, 403, 404, 408]

# Some proxy generate redirects of other errors, this codes invalidate
# the proxy and is mapped as a RETRY_HTTP_CODE 500
SMART_PROXY_ERROR_CODES = [301, 302, 504]

DOWNLOADER_MIDDLEWARES = {
    # Engine side
    # Add the VHost middleware at the beginning to avoid re-run all
    # the middleware list every time that the URL change.
    'scraper.middlewares.VHost': 50,
    # CloudFlare middleware needs to be before RetryMiddleware (550)
    'scraper.middlewares.CloudFlare': 555,
    # We need to put SmartProxy between RetryMiddleware (500) and
    # HttpProxyMiddleware (750).  Note that RedirectMiddleware (600)
    # can influence if the response is seem by SmartProxy.
    'scraper.middlewares.SmartProxy': 650,
    # RetryPartial needs to be after SmartProxy, so the
    # process_respose (that is called from the downloader side to
    # engine side direction) can process is a map it as a error.
    'scraper.middlewares.RetryPartial': 655,
    # Downloader side
}

ITEM_PIPELINES = {
    'scrapy.pipelines.images.ImagesPipeline': 25,
    'scraper.pipelines.CleanPipeline': 50,
    'scraper.pipelines.UpdateDBPipeline': 75,
    'scraper.pipelines.CollectorPipeline': 100,
}

_dirname = os.path.dirname(__file__)
IMAGES_STORE = os.path.join(_dirname, '..', 'img_store')
ISSUES_STORE = os.path.join(_dirname, '..', 'issue_store')

USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) Gecko/20100101 Firefox/52.0'

# AutoThrottle
AUTOTHROTTLE_ENABLED = True

# Allow redirect for media documents
MEDIA_ALLOW_REDIRECTS = True

# Mail configuration
MAIL_FROM = 'kindle@kmanga.net'
MAIL_HOST = 'localhost'
MAIL_PORT = 25
MAIL_USER = None
MAIL_PASS = None
MAIL_SSL = True
MAIL_TO = None

# Admin configuration
ADMIN_MAIL = ''

# Import local settings
try:
    from local_settings import *
except ImportError:
    pass
