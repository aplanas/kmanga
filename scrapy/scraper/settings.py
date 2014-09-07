# -*- coding: utf-8 -*-

# Scrapy settings for scraper project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

import os.path


BOT_NAME = 'scraper'

SPIDER_MODULES = ['scraper.spiders']
NEWSPIDER_MODULE = 'scraper.spiders'

ITEM_PIPELINES = {
    'scrapy.contrib.pipeline.images.ImagesPipeline': 1,
    'scraper.pipelines.MobiContainer': 500,
}

_dirname = os.path.dirname(__file__)
KINDLEGEN = os.path.join(_dirname, '..', '..', 'bin', 'kindlegen')

IMAGES_STORE = os.path.join(_dirname, '..', 'img_store')
MOBI_STORE = os.path.join(_dirname, '..', 'mobi_store')

VOLUME_MAX_SIZE = 15 * 1024**2

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'scraper (+http://www.yourdomain.com)'

# Mail configuration
MAIL_FROM = ''
MAIL_HOST = 'smtp.gmail.com'
MAIL_PORT = 465
MAIL_USER = ''
MAIL_PASS = ''
MAIL_SSL = True
# MAIL_TO = None

# Admin configuration
ADMIN_MAIL = ''
