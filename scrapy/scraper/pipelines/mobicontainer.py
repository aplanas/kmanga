# -*- coding: utf-8 -*-
#
# (c) 2014 Alberto Planas <aplanas@gmail.com>
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

import collections
import hashlib
import os

try:
    import cPickle as pickle
except:
    import pickle

from scrapy.mail import MailSender
from scrapy.utils.decorator import inthread

from main.models import Issue

from mobi import Container, MangaMobi


class MobiCache(collections.MutableMapping):
    def __init__(self, mobi_store):
        self.mobi_store = mobi_store
        self.index = os.path.join(mobi_store, 'cache', 'index')
        self.data = os.path.join(mobi_store, 'cache', 'data')

        # Create cache directories if they don't exists.
        for directory in (self.index, self.data):
            if not os.path.exists(directory):
                os.makedirs(directory)

    def __file(self, key):
        spider, name, issue, url = key
        name = '%s_%s_%03d_%s' % (spider, name, int(issue), url)
        name = hashlib.md5(name).hexdigest()
        return name

    def __index_file(self, key):
        name = self.__file(key)
        return os.path.join(self.index, name)

    def __data_file(self, key):
        name = self.__file(key)
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


class MobiContainer(object):
    def __init__(self, kindlegen, images_store, mobi_store,
                 volume_max_size, settings):
        self.kindlegen = kindlegen
        self.images_store = images_store
        self.mobi_store = mobi_store
        self.volume_max_size = volume_max_size
        self.settings = settings
        self.items = {}

    @classmethod
    def from_settings(cls, settings):
        return cls(settings['KINDLEGEN'],
                   settings['IMAGES_STORE'],
                   settings['MOBI_STORE'],
                   settings['VOLUME_MAX_SIZE'],
                   settings)

    def process_item(self, item, spider):
        if spider._operation == 'manga':
            key = (spider.name, spider.manga, spider.issue, spider.url)
            if key not in self.items:
                self.items[key] = []
            self.items[key].append(item)
        return item

    def close_spider(self, spider):
        if spider._operation == 'manga':
            return self.create_mobi()

    def _create_mobi(self, name, number, images, issue):
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

        # Basic container to store issue information
        class Info(object):
            def __init__(self, issue, multi_vol=False, vol=None):
                if multi_vol:
                    self.title = '%s %03d V%02d' % (issue.manga.name,
                                                    issue.number, vol)
                else:
                    self.title = '%s %03d' % (issue.manga.name,
                                              issue.number)
                # self.title = issue.name
                self.language = issue.language.lower()
                self.author = issue.manga.author
                self.publisher = issue.manga.source.name
                reading_direction = issue.manga.reading_direction.lower()
                self.reading_direction = 'horizontal-%s' % reading_direction

        values_and_containers = []
        for volume, container in enumerate(containers):
            multi_vol, vol = len(containers) > 1, volume + 1
            info = Info(issue, multi_vol, vol)

            mobi = MangaMobi(container, info, kindlegen=self.kindlegen)
            mobi_name, mobi_file = mobi.create()
            values_and_containers.append(((mobi_name, mobi_file), container))
            # Containers are cleaned by the caller (create_mobi)
            # container.clean()
        return values_and_containers

    @inthread
    def create_mobi(self):
        cache = MobiCache(self.mobi_store)

        for key, value in self.items.items():
            spider, name, number, url = key

            issue = Issue.objects.get(url=url)

            if key not in cache:
                # The containers need to be cleaned here.
                values_and_containers = self._create_mobi(name, number,
                                                          value, issue)
                cache[key] = [v[0] for v in values_and_containers]
                for _, container in values_and_containers:
                    container.clean()

            for mobi_name, mobi_file in cache[key]:
                mail = MailSender.from_settings(self.settings)
                deferred = mail.send(
                    to=[self.settings['MAIL_TO']],
                    subject='Your kmanga.net request',
                    body='',
                    attachs=((mobi_name, 'application/x-mobipocket-ebook',
                              open(mobi_file, 'rb')),))
                cb_data = [self.settings['MAIL_FROM'],
                           self.settings['MAIL_TO'],
                           name, number]
                deferred.addCallbacks(self.mail_ok, self.mail_err,
                                      callbackArgs=cb_data,
                                      errbackArgs=cb_data)
                # XXX TODO - Send email when errors

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
