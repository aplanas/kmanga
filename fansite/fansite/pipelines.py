# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os.path

from scrapy.utils.decorator import inthread

from mobi import Container, MangaMobi


class FansitePipeline(object):
    def process_item(self, item, spider):
        return item


class MobiContainer(object):
    def __init__(self, images_store, mobi_store):
        self.images_store = images_store
        self.mobi_store = mobi_store
        self.items = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings['IMAGES_STORE'], settings['MOBI_STORE'])

    def process_item(self, item, spider):
        if hasattr(spider, 'manga') and hasattr(spider, 'issue'):
            key = (spider.manga, spider.issue)
            if key not in self.items:
                self.items[key] = []
            self.items[key].append(item)
        return item

    def close_spider(self, spider):
        if hasattr(spider, 'manga') and hasattr(spider, 'issue'):
            return self.create_mobi()

    @inthread
    def create_mobi(self):
        for key, value in self.items.items():
            dir_name = '%s_%s' % key
            container = Container(os.path.join(self.mobi_store, dir_name))
            container.create()
            images = [os.path.join(self.images_store, i['images'][0]['path'])
                      for i in value]
            container.add_image_files(images, as_link=True)

            # XXX TODO - Recover the info from the database
            class Info(object):
                pass

            info = Info()
            info.title = '%s %s' % key
            info.language = 'en'
            info.author = 'author'
            info.publisher = 'publisher'
            info.pages = images

            mobi = MangaMobi(container, info)
            mobi.create()
            # XXX TODO - Can I cache the mobi?
            # mobi.clean()

        # XXX TODO - Send email when errors
