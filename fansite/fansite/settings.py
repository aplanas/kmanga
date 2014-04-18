# Scrapy settings for fansite project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#
import os.path


BOT_NAME = 'fansite'

SPIDER_MODULES = ['fansite.spiders']
NEWSPIDER_MODULE = 'fansite.spiders'

ITEM_PIPELINES = {
    'scrapy.contrib.pipeline.images.ImagesPipeline': 1,
    'fansite.pipelines.MobiContainer': 500,
}

IMAGES_STORE = os.path.join(os.path.dirname(__file__), '..', 'img_store')
MOBI_STORE = os.path.join(os.path.dirname(__file__), '..', 'mobi_store')

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'fansite (+http://www.yourdomain.com)'
