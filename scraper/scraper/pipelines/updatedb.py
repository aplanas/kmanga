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

import logging
import os.path
import urllib.parse

from django.core.files import File
from django.db import transaction

import django
django.setup()

from core.models import Issue
from core.models import Manga
from core.models import Source

logger = logging.getLogger(__name__)


class UpdateDBPipeline(object):
    def __init__(self, images_store):
        self.images_store = images_store

    @classmethod
    def from_settings(cls, settings):
        return cls(settings['IMAGES_STORE'])

    def process_item(self, item, spider):
        # Bypass the pipeline if called with dry-run parameter.
        if hasattr(spider, 'dry_run'):
            return item

        # _operation store where the item comes from.
        operation = spider._operation
        update_method = 'update_%s' % operation
        if hasattr(self, update_method):
            getattr(self, update_method)(item, spider)
        else:
            logger.debug('Method %s not found, '
                         'item %s not stored' % update_method)
        return item

    def _update_relation(self, obj, field_obj, field_rel_obj, items,
                         update, m2m=None):
        """Helper method to update list relation between two models.

           obj           -- row of the database (instance of a Model)
           field_obj     -- field name of obj that relate with
                            rel_obj. The name of this field is
                            `XXXX_set`.
           field_rel_obj -- field name of rel_obj that is a natural
                            key in the other side.
           items         -- list of items with new values.
           update        -- callback to update a new object from an
                            item. If return True, was changed.
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
                new_obj = rel_obj.model()
                update(new_obj, values_items[i])
                rel_obj.add(new_obj, bulk=False)
            else:
                # Sometimes the m2m relation is based on a string, and
                # we can try a different uppercase / lowercase
                # combination
                if i in values_m2m:
                    rel_obj.add(values_m2m[i])
                else:
                    if isinstance(i, str):
                        for (k, v) in values_m2m.items():
                            if i.lower() == k.lower():
                                rel_obj.add(v)
                                break

        # Updated values
        # XXX TODO - update m2m relation
        update_values = set_values_items & set_values_rel_obj
        for i in update_values:
            if not m2m:
                updated = update(values_rel_obj[i], values_items[i])
                if updated:
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

    def _sic(self, obj, item, field):
        """SetIfChange utility method."""
        updated = False
        if getattr(obj, field) != item[field]:
            setattr(obj, field, item[field])
            updated = True
        return updated

    @transaction.atomic
    def update_genres(self, item, spider):
        """Update the list of genres."""
        spider_name = spider.name.lower()
        source = Source.objects.get(spider=spider_name)

        # Convert the items in a way that _update_relation understand
        items = [{'name': i} for i in item['names']]

        new_values, update_values, del_values = self._update_relation(
            source, 'genre_set', 'name', items, self._update_name)

        for i in new_values:
            logger.debug('Added new genre in %s: %s' % (spider_name, i))

        for i in update_values:
            logger.debug('Update genre in %s: %s' % (spider_name, i))

        for i in del_values:
            logger.debug('Removed outdated genre '
                         'in %s: %s' % (spider_name, i))

    # @transaction.atomic
    def update_catalog(self, item, spider):
        """Update the catalog (list of mangas and issues)."""

        # A catalog is a list of mangas (collections) updates.  The
        # manga item from a catalog update can have more information
        # that the one created from a collection update.  Usually the
        # catalog provides information about the 'rank' and
        # 'rank_order', and this information is, sometimes, missing in
        # the collection.  This information will be stored in the
        # database in `update_collection` if it is pressent.
        #
        # The removal (delete) of collection are done outside.  Here
        # we only receive one item at a time, so we can't see the
        # items that are not anymore in the database.  The field
        # `updated` can be used here (only for collection, that is
        # always updated)
        self.update_collection(item, spider)

    @transaction.atomic
    def update_collection(self, item, spider):
        """Update a collection of issues (a manga)."""
        spider_name = spider.name.lower()
        source = Source.objects.get(spider=spider_name)
        try:
            manga = Manga.objects.get(url=item['url'], source=source)
        except Manga.DoesNotExist:
            manga = Manga(url=item['url'], source=source)

        # Relations are synchronized later on
        relations = ('alt_name', 'genres', 'image_urls', 'images', 'issues')
        fields = [f for f in item if f not in relations]

        # Note here that some fields are available when the entry
        # point is via `update_catalog`, and not via
        # `update_collection`.  For example, some sources do not
        # provide information about `rank` in the manga register, but
        # only in the catalog view.  In that case we do not want to
        # overwrite, or use the default value when the item do not
        # contain this information.
        #
        # The solution proposed here is to iterate only for the values
        # that are in the `item`, and delegate in `clean` the
        # detection of the values that are required.
        #
        # Update the fields of the manga object that are populated
        for f in fields:
            self._sic(manga, item, f)

        # Save the object to have a PK (creation of relations). Also
        # update the the `modified` field to signalize that the Manga
        # is still there (share semantic with `last_seen`)
        manga.save()

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
        if item['images']:
            path = urllib.parse.urlparse(item['image_urls'][0]).path
            name = os.path.basename(path)
            image_path = os.path.join(self.images_store,
                                      item['images'][0]['path'])
            # Update the cover always, so if we remove the image in
            # the MEDIA directory, this will be recreated.
            manga.cover.delete(save=False)
            with open(image_path, 'rb') as f:
                manga.cover.save(name, File(f))
        elif manga.cover:
            manga.cover.delete()

        # issues
        self._update_relation(manga, 'issue_set', 'url', item['issues'],
                              self._update_issue)

    @transaction.atomic
    def update_latest(self, item, spider):
        """Update the latest issues in a collection."""
        spider_name = spider.name.lower()
        source = Source.objects.get(spider=spider_name)
        try:
            manga = Manga.objects.get(url=item['url'], source=source)
        except Manga.DoesNotExist:
            # The manga is not a current one.  We simply ignore it
            # because will be created in the next full sync.
            return

        for item_issue in item['issues']:
            if not manga.issue_set.filter(url=item_issue['url']).exists():
                issue = Issue()
                self._update_issue(issue, item_issue)
                manga.issue_set.add(issue, bulk=False)

    @transaction.atomic
    def update_manga(self, item, spider):
        pass

    def _update_name(self, obj, item):
        """Helper update function."""
        changed = [self._sic(obj, item, field) for field in ('name',)]
        return any(changed)

    def _update_issue(self, obj, item):
        """Helper update function."""
        changed = [self._sic(obj, item, field) for field in (
            'name',
            'number',
            'order',
            'language',
            'release',
            'url'
        )]
        return any(changed)
