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

import os.path

from django.core.files import File
from scrapy import log

from main.models import Source, Manga

# https://docs.djangoproject.com/en/dev/releases/1.7/#standalone-scripts
import django
django.setup()


class UpdateDBPipeline(object):
    def process_item(self, item, spider):
        # _operation store where the item comes from.
        operation = spider._operation
        update_method = 'update_%s' % operation
        if hasattr(self, update_method):
            getattr(self, update_method)(item, spider)
        else:
            log.msg('Method %s not found, item %s not stored' % update_method,
                    level=log.DEBUG)
        return item

    def _update_relation(self, obj, field_obj, field_rel_obj, items, update,
                         m2m=None):
        """Helper method to update list relation between two models.

           obj           -- row of the database (instance of a Model)
           field_obj     -- field name of obj that relate with
                            rel_obj. The name of this field is
                            `XXXX_set`.
           field_rel_obj -- field name of rel_obj that is a natural
                            key in the other side.
           items         -- list of items with new values.
           update        -- callback to update a new object from an
                            item.
           m2m           -- list of valid objects for m2m relations.

        """
        rel_obj = getattr(obj, field_obj)

        values_rel_obj = {
            getattr(i, field_rel_obj): i for i in rel_obj.all()
        }
        set_values_rel_obj = set(values_rel_obj)

        values_items = {
            i[field_rel_obj]: i for i in items
        }
        set_values_items = set(values_items)

        if m2m:
            values_m2m = {
                getattr(i, field_rel_obj): i for i in m2m
            }

        # New values
        new_values = set_values_items - set_values_rel_obj
        for i in new_values:
            if not m2m:
                new_obj = rel_obj.create()
                update(new_obj, values_items[i])
                new_obj.save()
            else:
                rel_obj.add(values_m2m[i])

        # Updated values
        update_values = set_values_items & set_values_rel_obj
        for i in update_values:
            if not m2m:
                update(values_rel_obj[i], values_items[i])
                values_rel_obj[i].save()

        # Outdated values
        del_values = set_values_rel_obj - set_values_items
        if not m2m:
            kwargs = {
                '%s__in' % field_rel_obj: del_values
            }
            rel_obj.filter(**kwargs).delete()
        else:
            for i in del_values:
                rel_obj.remove(values_m2m[i])

        return (new_values, update_values, del_values)

    def update_genres(self, item, spider):
        """Update the list of genres."""
        spider_name = spider.name.lower()
        source = Source.objects.get(spider=spider_name)

        # Convert the items in a way that _update_relation understand
        items = [{'name': i} for i in item['names']]

        new_values, update_values, del_values = self._update_relation(
            source, 'genre_set', 'name', items, self._update_name)

        for i in new_values:
            log.msg('Added new genre in %s: %s' % (spider_name, i),
                    level=log.DEBUG)

        for i in update_values:
            log.msg('Update genre in %s: %s' % (spider_name, i),
                    level=log.DEBUG)

        for i in del_values:
            log.msg('Removed outdated genre in %s: %s' % (spider_name, i),
                    level=log.DEBUG)

    def update_catalog(self, item, spider):
        """Update the catalog (list of mangas and issues)."""

        # A catalog is a list of mangas (collections) updates.  The
        # manga item from a catalog update can have more information
        # that the one created from a collection update.  For now only
        # 'rank' is include in the catalog and not in the collection.
        # spider_name = spider.name.lower()
        # source = Source.objects.get(spider=spider_name)

        # manga, _ = Manga.objects.get_or_create(url=item['url'],
        #                                        source=source)
        # self.update_collention(item, spider, manga=manga)
        # XXX TODO -- We need to delete old collections

    def update_collection(self, item, spider, manga=None):
        """Update a collection of issues (a manga)."""
        if not manga:
            spider_name = spider.name.lower()
            source = Source.objects.get(spider=spider_name)
            manga, _ = Manga.objects.get_or_create(
                url=item['url'],
                source=source)

        ignore_fields = ('rank',)
        exceptions = ('alt_name', 'genres', 'image_urls', 'images', 'issues')
        for key, value in item.items():
            if key not in exceptions and key not in ignore_fields:
                setattr(manga, key, value)

        # alt_name
        alt_names = [{'name': i} for i in item['alt_name']]
        self._update_relation(manga, 'altname_set', 'name',
                              alt_names, self._update_name)

        # genres
        genres = [{'name': i} for i in item['genres']]
        self._update_relation(manga, 'genres', 'name',
                              genres, self._update_name,
                              m2m=source.genre_set.all())

        # cover
        manga.cover.delete()
        if item['images']:
            name = os.path.basename(item['images'][0])
            manga.cover.save(name, File(item['images'][0]))

        # issues
        self._update_relation(manga, 'issue_set', 'url', item['issues'],
                              self._update_issue)

    def update_latest(self, item, spider):
        pass

    def update_manga(self, item, spider):
        pass

    def _update_name(self, obj, item):
        """Helper update function."""
        obj.name = item['name']

    def _update_issue(self, obj, item):
        """Helper update function."""
        obj.name = item['name']
        obj.number = item['number']
        obj.url = item['number']
