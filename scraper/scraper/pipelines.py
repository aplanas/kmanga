# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import collections
import hashlib
import os

try:
    import cPickle as pickle
except:
    import pickle

from scrapy.mail import MailSender
from scrapy.utils.decorator import inthread

from mobi import Container, MangaMobi

# from main.models import HistoryLine


# class ScraperPipeline(object):
#     def process_item(self, item, spider):
#         return item


class MobiCache(collections.MutableMapping):
    def __init__(self, mobi_store):
        self.mobi_store = mobi_store
        self.index = os.path.join(mobi_store, 'cache', 'index')
        self.data = os.path.join(mobi_store, 'cache', 'data')

        # Create cache directories if they don't exists.
        for directory in (self.index, self.data):
            if not os.path.exists(directory):
                os.makedirs(directory)

    def __index_file(self, key):
        spider, name, issue = key
        name = '%s_%s_%03d' % (spider, name, int(issue))
        name = hashlib.md5(name).hexdigest()
        return os.path.join(self.index, name)

    def __data_file(self, key):
        spider, name, issue = key
        name = '%s_%s_%03d' % (spider, name, int(issue))
        name = hashlib.md5(name).hexdigest()
        return os.path.join(self.data, name)

    def __getitem__(self, key):
        try:
            # The last element contains the key.
            return pickle.load(open(self.__index_file(key), 'rb'))[:-1]
        except:
            raise KeyError

    def __setitem__(self, key, value):
        # Makes sure that the element is not there anymore.
        if key in self:
            del self[key]

        # Create first the links into the data store.
        data_file_prefix = self.__data_file(key)
        value_ext = [(v[0], v[1], '%s-%02d' % (data_file_prefix, i))
                     for i, v in enumerate(value)]
        for _, mobi_file, data_file in value_ext:
            os.link(mobi_file, data_file)

        # Store the index in the index file.
        index = [(v[0], v[2]) for v in value_ext]
        index.append(key)
        pickle.dump(index, open(self.__index_file(key), 'wb'),
                    pickle.HIGHEST_PROTOCOL)

    def __delitem__(self, key):
        index = self[key]
        for _, _data_file in index:
            os.unlink(_data_file)
        os.unlink(self.__index_file(key))

    def __iter__(self):
        for index_path in os.listdir(self.index):
            index_path = os.path.join(self.index, index_path)
            yield pickle.load(open(index_path, 'rb'))[-1]

    def __len__(self):
        return len(os.listdir(self.index))


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
            key = (spider.name, spider.manga, spider.issue)
            if key not in self.items:
                self.items[key] = []
            self.items[key].append(item)
        return item

    def close_spider(self, spider):
        if hasattr(spider, 'manga') and hasattr(spider, 'issue'):
            return self.create_mobi()

    def _create_mobi(self, name, number, images):
        """Create the MOBI file and return a generator."""
        dir_name = '%s_%03d' % (name, int(number))
        container = Container(os.path.join(self.mobi_store, dir_name))
        container.create()
        images = sorted(images, key=lambda x: x['number'])
        images = [os.path.join(self.images_store, i['images'][0]['path'])
                  for i in images]
        container.add_images(images, adjust=Container.ROTATE, as_link=True)

        if container.get_size() > self.volume_max_size:
            containers = container.split(self.volume_max_size)
            container.clean()
        else:
            containers = [container]

        # XXX TODO - Recover the info from the database
        class Info(object):
            pass

        values_and_containers = []
        for volume, container in enumerate(containers):
            info = Info()
            if len(containers) > 1:
                info.title = '%s %03d V%02d' % (name, int(number), volume+1)
            else:
                info.title = '%s %03d' % (name, int(number))
            info.language = 'en'
            info.author = 'author'
            info.publisher = 'publisher'

            mobi = MangaMobi(container, info)
            mobi_name, mobi_file = mobi.create()
            values_and_containers.append(((mobi_name, mobi_file), container))
            # Containers are cleaned by the caller.
            # container.clean()
        return values_and_containers

    @inthread
    def create_mobi(self):
        cache = MobiCache(self.mobi_store)

        for key, value in self.items.items():
            spider, name, number = key

            if key not in cache:
                # The containers need to be cleaned here.
                values_and_containers = self._create_mobi(name, number, value)
                cache[key] = [v[0] for v in values_and_containers]
                for _, container in values_and_containers:
                    container.clean()

            # for mobi_name, mobi_file in cache[key]:
            #     mail = MailSender.from_settings(self.settings)
            #     deferred = mail.send(
            #         to=[self.settings['MAIL_TO']],
            #         subject='Your kmanga.net request',
            #         body='',
            #         attachs=((mobi_name, 'application/x-mobipocket-ebook',
            #                   open(mobi_file, 'rb')),))
            #     cb_data = [self.settings['MAIL_FROM'],
            #                self.settings['MAIL_TO'],
            #                name, number]
            #     deferred.addCallbacks(self.mail_ok, self.mail_err,
            #                           callbackArgs=cb_data,
            #                           errbackArgs=cb_data)
            #     # XXX TODO - Send email when errors

    def mail_ok(self, result, from_mail, to_mail, manga_name, manga_issue):
        # hl = HistoryLine.objects.filter(
        #     history__name=manga_name,
        #     history__from_issue__lte=manga_issue,
        #     history__to_issue__gte=manga_issue)
        # for h in hl:
        #     print 'HEEEEEEEEEEEEEEEEEEEEEEEERE', h
        print 'Mail OK', from_mail, to_mail, manga_name, manga_issue

    def mail_err(self, result, from_mail, to_mail, manga_name, manga_issue):
        print 'Mail ERROR', from_mail, to_mail, manga_name, manga_issue
