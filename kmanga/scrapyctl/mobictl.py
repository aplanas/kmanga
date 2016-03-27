from __future__ import absolute_import

import logging
import os

from django.conf import settings
from django_rq import job

from core.models import Result
from scrapyctl.emailctl import send_mobi
from mobi import Container
from mobi import MangaMobi
from mobi.cache import IssueCache
from mobi.cache import MobiCache

# Empty page.  Used when the original one can't be downloaded.
EMPTY = 'empty.png'

logger = logging.getLogger(__name__)


class MobiCtl(object):
    """Helper class to create MOBI documents."""

    def __init__(self, issue, images, images_store):
        """Create a new MOBI from one issue and a set of images."""
        self.issue = issue
        self.images = images
        self.images_store = images_store

        self.kindlegen = settings.KINDLEGEN
        self.mobi_store = settings.MOBI_STORE
        self.volume_max_size = settings.VOLUME_MAX_SIZE

    def _normalize(self, number):
        """Normalize the string that represent a `number`."""
        number = [i if i.isalnum() else '_' for i in number.lower()]
        return ''.join(number)

    def _create_mobi(self):
        """Create the MOBI file and return a list of files and containers."""
        name = self.issue.name
        number = self.issue.number

        dir_name = '%s_%s' % (name, self._normalize(number))
        container = Container(os.path.join(self.mobi_store, dir_name))
        container.create(clean=True)
        images = sorted(self.images, key=lambda x: x['number'])
        _images = []
        for i in images:
            if i['images']:
                image_path = i['images'][0]['path']
            else:
                image_path = EMPTY
            _images.append(os.path.join(self.images_store, image_path))
        container.add_images(_images, adjust=Container.ROTATE, as_link=True)

        if container.get_size() > self.volume_max_size:
            containers = container.split(self.volume_max_size, clean=True)
            container.clean()
        else:
            containers = [container]

        # Basic container to store issue information
        class Info(object):
            def __init__(self, issue, multi_vol=False, vol=None):
                if multi_vol:
                    self.title = '%s %s/%02d' % (issue.manga.name,
                                                 issue.number, vol)
                else:
                    self.title = '%s %s' % (issue.manga.name,
                                            issue.number)
                self.language = issue.language.lower()
                self.author = issue.manga.author
                self.publisher = issue.manga.source.name
                reading_direction = issue.manga.reading_direction.lower()
                self.reading_direction = 'horizontal-%s' % reading_direction

        mobi_and_containers = []
        for volume, container in enumerate(containers):
            multi_vol, vol = len(containers) > 1, volume + 1
            info = Info(self.issue, multi_vol, vol)

            mobi = MangaMobi(container, info, kindlegen=self.kindlegen)
            mobi_file = mobi.create()
            mobi_and_containers.append((mobi_file, container))
        return mobi_and_containers

    def create_mobi(self):
        """Create the MOBI file and return a list of files and names."""
        cache = MobiCache(settings.MOBI_STORE)

        url = str(self.issue.url)
        if url not in cache:
            mobi_and_containers = self._create_mobi()
            # XXX TODO - We are not storing stats in the cache anymore (is
            # not the place), so we need to store it in a different place.
            # Maybe in the database?
            cache[url] = [m[0] for m in mobi_and_containers]
            # The containers need to be cleaned here.
            for _, container in mobi_and_containers:
                container.clean()

        mobi_info, _ = cache[url]
        return mobi_info


@job('default', timeout=15*60)
def _create_mobi(issue, result=None):
    """RQ job to create a single MOBI document."""
    issue_cache = IssueCache(settings.ISSUES_STORE, settings.IMAGES_STORE)

    url = str(issue.url)
    if url not in issue_cache:
        logger.error('Issue not found in issue cache (%s)' % issue)
        if result:
            result.set_status(Result.FAILED)
    elif not issue_cache.is_valid(url):
        logger.error('Issue in issue cache is not valid (%s)' % issue)
        if result:
            result.set_status(Result.FAILED)
        del issue_cache[url]
    else:
        images, _ = issue_cache[url]
        mobictl = MobiCtl(issue, images, settings.IMAGES_STORE)
        mobictl.create_mobi()


@job
def create_mobi(issues):
    """RQ job to create MOBI documents."""
    for issue in issues:
        _create_mobi.delay(issue)


@job
def create_mobi_and_send(issues, user):
    """RQ job to create MOBI documents and send it to the user."""
    for issue in issues:
        result = Result.objects.create_if_new(issue, user, Result.PROCESSING)

        # These jobs also update the Result status
        mobi_job = _create_mobi.delay(issue, result=result)
        send_mobi.delay(issue, user, depends_on=mobi_job)
