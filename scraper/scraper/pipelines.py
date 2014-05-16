# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html
import os.path

from scrapy.mail import MailSender
from scrapy.utils.decorator import inthread

from mobi import Container, MangaMobi


class FansitePipeline(object):
    def process_item(self, item, spider):
        return item


class MobiContainer(object):
    def __init__(self, images_store, mobi_store, volume_max_size, settings):
        self.images_store = images_store
        self.mobi_store = mobi_store
        self.volume_max_size = volume_max_size
        self.settings = settings
        self.items = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings['IMAGES_STORE'], settings['MOBI_STORE'],
                   settings['VOLUME_MAX_SIZE'], settings)

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
            name, number = key

            dir_name = '%s_%03d' % (name, int(number))
            container = Container(os.path.join(self.mobi_store, dir_name))
            container.create()
            value = sorted(value, key=lambda x: x['number'])
            images = [os.path.join(self.images_store, i['images'][0]['path'])
                      for i in value]
            container.add_images(images, adjust=Container.ROTATE, as_link=True)

            if container.get_size() > self.volume_max_size:
                containers = container.split(self.volume_max_size)
                container.clean()
            else:
                containers = [container]

            # XXX TODO - Recover the info from the database
            class Info(object):
                pass

            for volume, container in enumerate(containers):
                info = Info()
                if len(containers) > 1:
                    info.title = '%s %03d V%02d' % (name, int(number),
                                                    volume+1)
                else:
                    info.title = '%s %03d' % (name, int(number))
                info.language = 'en'
                info.author = 'author'
                info.publisher = 'publisher'

                mobi = MangaMobi(container, info)
                name, mobi_file = mobi.create()
                mail = MailSender.from_settings(self.settings)
                deferred = mail.send(
                    to=[self.settings['MAIL_TO']],
                    subject=info.title,
                    body='',
                    attachs=((name, 'application/x-mobipocket-ebook',
                              open(mobi_file, 'rb')),))
                cb_data = [self.settings['MAIL_FROM'],
                           self.settings['MAIL_TO'],
                           name, number]
                deferred.addCallbacks(self.mail_ok, self.mail_err,
                                      callbackArgs=cb_data,
                                      errbackArgs=cb_data)
                # XXX TODO - Send email when errors
                # XXX TODO - Can I cache the mobi?
                container.clean()

    def mail_ok(self, result, from_mail, to_mail, manga_name, manga_issue):
        print 'Mail OK', from_mail, to_mail, manga_name, manga_issue

    def mail_err(self, result, from_mail, to_mail, manga_name, manga_issue):
        print 'Mail ERROR', from_mail, to_mail, manga_name, manga_issue
