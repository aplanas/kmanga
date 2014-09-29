# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: http://doc.scrapy.org/en/latest/topics/item-pipeline.html

import collections
from datetime import date, datetime, timedelta
import hashlib
import os
import re

try:
    import cPickle as pickle
except:
    import pickle

from scrapy import log
from scrapy.exceptions import DropItem
from scrapy.mail import MailSender
from scrapy.utils.decorator import inthread
from scrapy.utils.markup import remove_tags, replace_entities

from mobi import Container, MangaMobi

# from main.models import HistoryLine


# class ScraperPipeline(object):
#     def process_item(self, item, spider):
#         return item


def convert_to_date(str_):
    """Parse humanized dates."""
    if str_ == 'Today':
        return date.today()
    elif str_ == 'Yesterday':
        return date.today() - timedelta(days=1)
    elif str_.endswith('now'):
        return date.today()
    elif str_.endswith(('minutes ago', 'minute ago')):
        minutes = int(re.search(r'(\d+) minutes? ago', str_).group(1))
        return date.today() - timedelta(minutes=minutes)
    elif str_.endswith(('hours ago', 'hour ago')):
        hours = 1
        try:
            hours = int(re.search(r'(\d+) hours? ago', str_).group(1))
        except AttributeError:
            pass
        return date.today() - timedelta(hours=hours)
    elif str_.endswith(('days ago', 'day ago')):
        days = 1
        try:
            days = int(re.search(r'(\d+) days? ago', str_).group(1))
        except AttributeError:
            pass
        return date.today() - timedelta(days=days)
    elif str_.endswith(('weeks ago', 'week ago')):
        weeks = 1
        try:
            weeks = int(re.search(r'(\d+) weeks? ago', str_).group(1))
        except AttributeError:
            pass
        return date.today() - timedelta(weeks=weeks)
    elif re.match(r'\d{2} \w{3} \d{4}', str_):
        return datetime.strptime(str_, '%d %b %Y').date()
    elif re.match(r'\d{2} \w+ \d{4} - \d{2}:\d{2} \w{2}', str_):
        return date.strptime(str_, '%d %B %Y - %I:%M %p').date()
    else:
        raise ValueError('Format not recognized')


class CleanBasePipeline(object):

    def process_item(self, item, spider):
        """Search a proper method to clean this item. Generate names of
        candidates and call it passing the item and the spider. The
        order of calling is:

        - clean_<spidername>_<itemname>()
        - clean_<itemname>()

        """

        # Deduce the name of the method that can take care of the
        # item, two options: one generic and one specific for the
        # spider.
        item_name = item.__class__.__name__.lower()
        spider_name = spider.name.lower()
        item_method = 'clean_%s' % item_name
        spider_method = 'clean_%s_%s' % (spider_name, item_name)

        if hasattr(self, spider_method):
            return getattr(self, spider_method)(item, spider)
        elif hasattr(self, item_method):
            return getattr(self, item_method)(item, spider)
        else:
            log.msg('Method (%s, %s) not found,'
                    'item not cleaned' % (item_method, spider_method),
                    level=log.DEBUG)
        return item

    def _as_str(self, obj, separator=' '):
        """Convert the object into a string, if can be iterated, use separator
        to make the join.

        """
        if isinstance(obj, list):
            obj = separator.join(o.strip() for o in obj)
        return unicode(obj).strip()

    def _as_list(self, obj):
        """Convert the object into a list."""
        return obj if isinstance(obj, (list, tuple)) else [obj]

    def _clean_field_str(self, field, clean_html=False, optional=False):
        """Generic clean method for string field."""
        value = self._as_str(field)
        if clean_html:
            value = replace_entities(remove_tags(value))
        if not value and not optional:
            raise ValueError('field is not optional'
                             " or can't be converted to a string")
        return value

    def _clean_field_int(self, field, optional=False, default=0):
        """Generic clean method for integer field."""
        value = default
        try:
            value = int(float(self._as_str(field, separator='')))
        except ValueError:
            if not optional:
                raise ValueError('field is not optional'
                                 " or can't be converted to an integer")
        return value

    def _clean_field_num(self, field, optional=False, default=0):
        """Generic clean method for numeric field."""
        value = default
        try:
            value = float(self._as_str(field))
        except ValueError:
            if not optional:
                raise ValueError('field is not optional'
                                 " or can't be converted to a float")
        return value

    def _clean_field_list(self, field, cleaner=None, cleaner_params=None,
                          optional=False, exclude=None):
        """Generic clean method for list field."""
        if cleaner:
            cleaner_params = cleaner_params if cleaner_params else ()
            value = [cleaner(e, *cleaner_params) for e in self._as_list(field)]
        else:
            value = [e.strip() for e in self._as_list(field)]
        if exclude:
            value = [e for e in value if e not in exclude]
        if not value and not optional:
            raise ValueError('field is not optional'
                             " or can't be converted to a list")
        return value

    def _clean_field_set(self, field, values, translator=None, optional=False):
        """Transform the field and check if is in the proper range."""
        value = self._as_str(field)
        if translator:
            if callable(translator):
                value = translator(value)
            else:
                try:
                    value = translator[value]
                except KeyError:
                    if not optional:
                        raise ValueError("field can't be translated")
        else:
            value = value.upper()
        if not value and not optional:
            raise ValueError('field is not optional'
                             " or can't be converted to a string")
        elif value not in values and not optional:
            raise ValueError('field is not a valid value')
        return value

    # def _clean_field_date(self, field, optional=False):
    #     # TODO XXX - Convert typical date formats
    #     if not field and not optional:
    #         raise ValueError('field is not optional'
    #                          " or can't be converted to a date")

    def clean_item(self, item, spider, cleaning_plan):
        """Clean all the fields in a item.

        This method iterates for every field in the item object and
        search a method that can clean it.  The search order is:

        - clean_field_<sipdername>_<itemname>_<fieldname>()
        - clean_field_<itemname>_<fieldname>()
        - <itemname>() inside the cleaning_plan dict

        This _clean do not update the item instance. Return a new
        cleaned instance.

        """

        item_name = item.__class__.__name__.lower()
        spider_name = spider.name.lower()

        _item = item.copy()
        for field_name, value in item.iteritems():
            item_method = 'clean_field_%s_%s' % (item_name, field_name)
            spider_method = 'clean_field_%s_%s_%s' % (spider_name, item_name,
                                                      field_name)

            try:
                if hasattr(self, spider_method):
                    _item[field_name] = getattr(self, spider_method)(value)
                elif hasattr(self, item_method):
                    _item[field_name] = getattr(self, item_method)(value)
                elif field_name in cleaning_plan:
                    _call = cleaning_plan[field_name]
                    if callable(_call):
                        _item[field_name] = _call(value)
                    else:
                        _item[field_name] = _call[0](value, **_call[1])
                else:
                    log.msg('Method (%s, %s) not found,'
                            'field %s not cleaned' % (item_method,
                                                      spider_method,
                                                      field_name),
                            level=log.DEBUG)
            except ValueError as e:
                msg = 'Error processing %s: %s [%s]'
                raise DropItem(msg % (field_name, str(value), e.message))
        return _item


class CleanPipeline(CleanBasePipeline):

    # -- Genres
    def clean_genres(self, item, spider):
        exclude = ('All', '[no chapters]', '')
        cleaning_plan = {
            'names': (self._clean_field_list, {'exclude': exclude})
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- Manga
    def clean_manga(self, item, spider):
        cleaning_plan = {
            'name': self._clean_field_str,
            'alt_name': (self._clean_field_list, {'optional': True}),
            'author': (self._clean_field_str, {'optional': True}),
            'artist': (self._clean_field_str, {'optional': True}),
            'reading_direction': (self._clean_field_set,
                                  {'values': ('LR', 'RL')}),
            'status': (self._clean_field_set,
                       {'values': ('ONGOING', 'COMPLETED')}),
            'genres': (self._clean_field_list, {'optional': True}),
            'rank': self._clean_field_int,
            'rank_order': (self._clean_field_set,
                           {'values': ('ASC', 'DESC')}),
            'description': (self._clean_field_str,
                            {'clean_html': True, 'optional': True}),
            # 'image_urls'
            # 'images'
            'issues': (self._clean_field_list,
                       {
                           'cleaner': self.clean_issue,
                           'cleaner_params': (spider,),
                       }),
            'url': self._clean_field_str,
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- Issue
    def clean_issue(self, item, spider):
        cleaning_plan = {
            'name': self._clean_field_str,
            'number': (self._clean_field_num, {'optional': True}),
            'language': (self._clean_field_set,
                         {'values': ('EN', 'ES')}),
            # 'added'
            'url': self._clean_field_str,
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- IssuePage
    def clean_issuepage(self, item, spider):
        cleaning_plan = {
            'manga': self._clean_field_str,
            'issue': self._clean_field_str,
            'number': self._clean_field_int,
            # 'image_urls'
            # 'images'
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- Batoto fields
    def clean_field_batoto_manga_status(self, field):
        status = {
            'Complete': 'COMPLETED',
            'Ongoing': 'ONGOING',
        }
        return self._clean_field_set(field, status.values(), translator=status)

    def clean_field_batoto_issue_language(self, field):
        lang = {
            'English': 'EN',
            'Spanish': 'ES',
        }
        return self._clean_field_set(field, lang.values(), translator=lang,
                                     optional=True)


class UpdateDBPipeline(object):
    def process_item(self, item, spider):
        return item


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

            mobi = MangaMobi(container, info, kindlegen=self.kindlegen)
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
