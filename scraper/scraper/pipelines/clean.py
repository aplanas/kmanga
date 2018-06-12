# -*- coding: utf-8 -*-
#
# (c) 2018 Alberto Planas <aplanas@gmail.com>
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

from datetime import date
from datetime import datetime
from datetime import timedelta
import logging
import re
import urllib.parse

from scrapy.exceptions import DropItem
from scrapy.utils.markup import remove_tags, replace_entities

logger = logging.getLogger(__name__)

# Languages
GERMAN = 'DE'
ENGLISH = 'EN'
SPANISH = 'ES'
FRENCH = 'FR'
ITALIAN = 'IT'
RUSSIAN = 'RU'
PORTUGUESE = 'PT'
LANGUAGES = (GERMAN, ENGLISH, SPANISH, FRENCH, ITALIAN, RUSSIAN,
             PORTUGUESE)


def convert_to_date(str_, dmy=False):
    """Parse humanized dates."""
    if str_.startswith('Today'):
        return date.today()
    elif str_.startswith('Yesterday'):
        return date.today() - timedelta(days=1)
    elif str_.endswith('now'):
        return date.today()
    elif str_.endswith(('minutes ago', 'minute ago')):
        minutes = 1
        try:
            minutes = int(re.search(r'(\d+) minutes? ago', str_).group(1))
        except AttributeError:
            pass
        return (datetime.now() - timedelta(minutes=minutes)).date()
    elif str_.endswith(('hours ago', 'hour ago')):
        hours = 1
        try:
            hours = int(re.search(r'(\d+) hours? ago', str_).group(1))
        except AttributeError:
            pass
        return (datetime.now() - timedelta(hours=hours)).date()
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
    elif str_.endswith(('months ago', 'month ago')):
        months = 1
        try:
            months = int(re.search(r'(\d+) months? ago', str_).group(1))
        except AttributeError:
            pass
        return date.today() - timedelta(days=months*30)
    elif str_.endswith(('years ago', 'year ago')):
        years = 1
        try:
            years = int(re.search(r'(\d+) years? ago', str_).group(1))
        except AttributeError:
            pass
        return date.today() - timedelta(days=years*365)
    elif re.match(r'\d{2} \w+ \d{4} - \d{2}:\d{2} \w{2}', str_):
        return datetime.strptime(str_, '%d %B %Y - %I:%M %p').date()
    elif re.match(r'\d{2} \w{3} \d{4}', str_):
        return datetime.strptime(str_, '%d %b %Y').date()
    elif re.match(r'\w{3} \d{1,2}, \d{4} \d{2}:\d{2}\w{2}', str_):
        return datetime.strptime(str_, '%b %d, %Y %H:%M%p').date()
    elif re.match(r'\w{3} \d{1,2}, \d{4}', str_):
        return datetime.strptime(str_, '%b %d, %Y').date()
    elif re.match(r'\d{1,2}-\d{1,2}-\d{4}', str_):
        return datetime.strptime(str_, '%d-%m-%Y').date()
    elif re.match(r'\d{1,2}/\d{1,2}/\d{4}', str_):
        if dmy:
            return datetime.strptime(str_, '%d/%m/%Y').date()
        else:
            return datetime.strptime(str_, '%m/%d/%Y').date()
    elif re.match(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00', str_):
        return datetime.strptime(str_, '%Y-%m-%dT%H:%M:%S+00:00').date()
    elif re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} UTC', str_):
        return datetime.strptime(str_, '%Y-%m-%d %H:%M:%S UTC').date()
    else:
        raise ValueError('Format "%s" not recognized' % str_)


def convert_to_number(str_, as_int=False, separator=r',', default=0):
    """Parse issues / viewers numbers."""
    result = default
    # Remove ordinal suffix
    str_ = re.sub(r'(st|nd|rd|th)', '', str_)
    # Remove decimal separator (for millards)
    str_ = re.sub(separator, '', str_)
    try:
        if str_.endswith('k'):
            result = 1000 * float(str_[:-1])
        elif str_.endswith('m'):
            result = 1000 * 1000 * float(str_[:-1])
        else:
            result = float(str_)
    except ValueError:
        logger.warning("Can't convert '%s' to a number. "
                       'Using default value %s' % (str_, default))

    if as_int:
        result = int(result)

    return result


class CleanBasePipeline(object):

    def process_item(self, item, spider):
        """Search a proper method to clean this item. Generate names of
        candidates and call it passing the item and the spider. The
        order of calling is:

        - clean_<spidername>_<itemname>()
        - clean_<itemname>()

        """

        # Bypass the pipeline if called with dry-run parameter.
        if hasattr(spider, 'dry_run'):
            return item

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
            logger.debug('Method (%s, %s) not found,'
                         'item not cleaned' % (item_method, spider_method))
        return item

    def _as_str(self, obj, separator=' '):
        """Convert the object into a string, if can be iterated, use separator
        to make the join.

        """
        if isinstance(obj, list):
            obj = separator.join(o.strip() for o in obj)
        return str(obj).strip()

    def _as_list(self, obj):
        """Convert the object into a list of elements."""
        if isinstance(obj, (list, tuple)):
            lst = [self._as_list(i) for i in obj]
            return [j for i in lst for j in i]
        else:
            return [obj]

    def _clean_field_str(self, field, clean_html=False,
                         optional=False, max_length=None):
        """Generic clean method for string field."""
        value = self._as_str(field)
        if max_length:
            value = value[:max_length]
        if clean_html:
            value = replace_entities(remove_tags(value))
        if not value and not optional:
            raise ValueError('field is not optional'
                             " or can't be converted to a string")
        return value

    def _clean_field_int(self, field, optional=False, separator=r',',
                         default=0):
        """Generic clean method for integer field."""
        value = default
        try:
            value = convert_to_number(self._as_str(field, separator=''),
                                      as_int=True, separator=separator,
                                      default=default)
        except ValueError:
            if not optional:
                raise ValueError('field is not optional'
                                 " or can't be converted to an integer")
        return value

    def _clean_field_float(self, field, optional=False, separator=r',',
                           default=0.0):
        """Generic clean method for float field."""
        value = default
        try:
            value = convert_to_number(self._as_str(field, separator=''),
                                      separator=separator, default=default)
        except ValueError:
            if not optional:
                raise ValueError('field is not optional'
                                 " or can't be converted to a float")
        return value

    def _clean_field_list(self, field, cleaner=None,
                          cleaner_params=None, optional=False,
                          exclude=None, drop=False, max_length=None):
        """Generic clean method for list field."""
        if cleaner:
            cleaner_params = cleaner_params if cleaner_params else ()
            value = []
            for e in self._as_list(field):
                try:
                    c = cleaner(e, *cleaner_params)
                except DropItem:
                    # If the exception created by the cleaner function
                    # is DropItem and we are allowed to drop items, we
                    # drop it, else we re-raise the exception droping
                    # the full item container.
                    if not drop:
                        raise
                else:
                    value.append(c)
        else:
            value = [e.strip() for e in self._as_list(field)]
        if exclude:
            value = [e for e in value if e not in exclude]
        if max_length:
            value = [e[:max_length] for e in value]
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

    def _clean_field_date(self, field, dmy=False, optional=False):
        """Transform the field into a date."""
        if isinstance(field, date):
            return field
        value = self._as_str(field)
        try:
            value = convert_to_date(value, dmy=dmy)
        except ValueError:
            if not optional:
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
        for field_name, value in item.items():
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
                    logger.debug('Method (%s, %s) not found,'
                                 'field %s not cleaned' % (item_method,
                                                           spider_method,
                                                           field_name))
            except ValueError as e:
                msg = 'Error processing %s: %s [%s]'
                raise DropItem(msg % (field_name, str(value), e))
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
            'alt_name': (self._clean_field_list,
                         {
                             'optional': True,
                             'max_length': 200,
                             'exclude': ('',),
                         }),
            'author': (self._clean_field_str,
                       {
                           'optional': True,
                           'max_length': 200,
                       }),
            'artist': (self._clean_field_str,
                       {
                           'optional': True,
                           'max_length': 200,
                       }),
            'reading_direction': (self._clean_field_set,
                                  {'values': ('LR', 'RL')}),
            'status': (self._clean_field_set,
                       {
                           'values': ('O', 'C'),
                           'translator':
                           {
                               'Ongoing': 'O',
                               'Completed': 'C',
                           },
                       }),
            'genres': (self._clean_field_list,
                       {
                           'optional': True,
                           'max_length': 200,
                           'exclude': ('',),
                       }),
            'rank': (self._clean_field_int, {'optional': True}),
            'rank_order': (self._clean_field_set,
                           {'values': ('ASC', 'DESC')}),
            'description': (self._clean_field_str,
                            {
                                'clean_html': True,
                                'optional': True,
                            }),
            # 'image_urls'
            # 'images'
            'issues': (self._clean_field_list,
                       {
                           'cleaner': self.clean_issue,
                           'cleaner_params': (spider,),
                           'drop': True,
                       }),
            'url': self._clean_field_str,
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- Issue
    def clean_issue(self, item, spider):
        cleaning_plan = {
            'name': (self._clean_field_str, {'max_length': 200}),
            'number': (self._clean_field_str, {
                'optional': True,
                'max_length': 10,
            }),
            'order': self._clean_field_int,
            'language': (self._clean_field_set,
                         {'values': LANGUAGES}),
            'release': self._clean_field_date,
            'url': self._clean_field_str,
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- IssuePage
    def clean_issuepage(self, item, spider):
        cleaning_plan = {
            'manga': self._clean_field_str,
            'issue': (self._clean_field_str, {'optional': True}),
            'number': self._clean_field_int,
            # 'image_urls'
            # 'images'
        }
        return self.clean_item(item, spider, cleaning_plan)

    # -- Batoto fields
    def clean_field_batoto_genres_names(self, field):
        field = [genre.title() for genre in field]
        return self._clean_field_list(field)

    def clean_field_batoto_issue_language(self, field):
        lang = {
            'flag_germany': GERMAN,
            'flag_united_kingdom': ENGLISH,
            'flag_spain': SPANISH,
            'flag_france': FRENCH,
            'flag_italy': ITALIAN,
            'flag_russia': RUSSIAN,
            'flag_portugal': PORTUGUESE,
        }
        return self._clean_field_set(field, lang.values(), translator=lang)

    # -- Mangafox fields
    def clean_field_mangafox_manga_name(self, field):
        # Remove the postfix Manga | Manhwa | Manhua
        values = field
        if any(i in field[0] for i in ('Manga', 'Manhwa', 'Manhua')):
            values = field[0].split()[:-1]
        return self._clean_field_str(values)

    def clean_field_mangafox_manga_alt_name(self, field):
        values = [i.split(';') for i in field]
        return self._clean_field_list(values, exclude=('',),
                                      optional=True,
                                      max_length=200)

    def clean_field_mangafox_issue_url(self, field):
        # Sometimes Issues URL do not ends with '1.html', this causes
        # problem in the updatedb part (can remove issues and replace
        # it with the equivalent ones, but with different URL)
        url = self._clean_field_str(field)
        return urllib.parse.urljoin(url, '1.html')

    # -- KissManga fields
    def clean_field_kissmanga_issue_number(self, field):
        field = self._clean_field_str(field, optional=True, max_length=10)
        return re.sub(r'\b00?', '', field)

    # -- UnionMangas fields
    def clean_field_unionmangas_manga_status(self, field):
        status = {
            'Ativo': 'O',
            'Completo': 'C',
        }
        return self._clean_field_set(field, status.values(), translator=status)

    def clean_field_unionmangas_manga_rank(self, field):
        return self._clean_field_int(field, separator=r'\.')

    def clean_field_unionmangas_issue_release(self, field):
        return self._clean_field_date(field, dmy=True)

    # -- MangaSee fields
    def clean_field_mangasee_manga_reading_direction(self, field):
        type_ = self._clean_field_str(field)
        # This table is not exact, for example, some Manhwa are readed
        # from right to left, like a Manga
        reading_direction = {
            'Doujinshi': 'RL',
            'Manga': 'RL',
            'Manhua': 'RL',
            'Manhwa': 'LR',
            'OEL': 'LR',
            'One-Shot': 'RL',
        }.get(type_, 'RL')
        return reading_direction

    def clean_field_mangasee_manga_status(self, field):
        return 'O' if 'Ongoing' in field else 'C'

    # -- MangaDex fields
    def clean_field_mangadex_manga_reading_direction(self, field):
        type_ = self._clean_field_str(field)
        reading_direction = {
            'Japanese': 'RL',
            'Chinese (Simp)': 'RL',
            'Korean': 'LR',
        }.get(type_, 'LR')
        return reading_direction

    def clean_field_mangadex_manga_status(self, field):
        # Some other status like 'Hiatus' are like Ongoing
        return 'C' if 'Completed' in field else 'O'

    def clean_field_mangadex_issue_language(self, field):
        lang = {
            'German': GERMAN,
            'English': ENGLISH,
            'Spanish (Es)': SPANISH,
            'French': FRENCH,
            'Italian': ITALIAN,
            'Russian': RUSSIAN,
            'Portuguese (Br)': PORTUGUESE,
        }
        return self._clean_field_set(field, lang.values(), translator=lang)
