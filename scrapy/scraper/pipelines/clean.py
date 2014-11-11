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

from datetime import date, datetime, timedelta
import re

from scrapy import log
from scrapy.exceptions import DropItem
from scrapy.utils.markup import remove_tags, replace_entities


def convert_to_date(str_, dmy=False):
    """Parse humanized dates."""
    if str_ == 'Today':
        return date.today()
    elif str_ == 'Yesterday':
        return date.today() - timedelta(days=1)
    elif str_.endswith('now'):
        return date.today()
    elif str_.endswith(('minutes ago', 'minute ago')):
        minutes = 1
        try:
            minutes = int(re.search(r'(\d+) minutes? ago', str_).group(1))
        except AttributeError:
            pass
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
    elif re.match(r'\d{2} \w+ \d{4} - \d{2}:\d{2} \w{2}', str_):
        return datetime.strptime(str_, '%d %B %Y - %I:%M %p').date()
    elif re.match(r'\d{2} \w{3} \d{4}', str_):
        return datetime.strptime(str_, '%d %b %Y').date()
    elif re.match(r'\d{2}/\d{2}/\d{4}', str_):
        if dmy:
            return datetime.strptime(str_, '%d/%m/%Y').date()
        else:
            return datetime.strptime(str_, '%m/%d/%Y').date()
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

    def _clean_field_date(self, field, optional=False):
        """Transform the field into a date."""
        if isinstance(field, date):
            return field
        value = self._as_str(field)
        value = convert_to_date(value)
        if not field and not optional:
            raise ValueError('field is not optional'
                             " or can't be converted to a date")
        return value

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
            'rank': (self._clean_field_int, {'optional': True}),
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
            'release': self._clean_field_date,
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

    def clean_field_batoto_manga_genres(self, field):
        exclude = ('[no chapters]',)
        return self._clean_field_list(field, optional=True, exclude=exclude)

    def clean_field_batoto_issue_language(self, field):
        lang = {
            'English': 'EN',
            'Spanish': 'ES',
        }
        return self._clean_field_set(field, lang.values(), translator=lang,
                                     optional=True)
