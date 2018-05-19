import logging
import os
import re
import tempfile

from django.conf import settings
from django_rq import job

from core.models import Result
from core.models import Subscription
from scrapyctl.emailctl import send_mobi
from mobi import Container
from mobi import MangaMobi
from mobi.cache import IssueCache
from mobi.cache import MobiCache

# Empty page.  Used when the original one can't be downloaded.
EMPTY = 'empty.png'

logger = logging.getLogger(__name__)


class MobiInfo(object):
    """Basic container to store Issue information."""
    def __init__(self, issue, multi_vol=False, vol=None, total_vols=1):
        self.title = self._title(issue.manga.name, issue.name, issue.number,
                                 multi_vol, vol, total_vols)
        self.language = issue.language.lower()
        self.author = issue.manga.author
        self.publisher = issue.manga.source.name
        reading_direction = issue.manga.reading_direction.lower()
        self.reading_direction = 'horizontal-%s' % reading_direction

    def is_int(self, number):
        try:
            int(number)
        except ValueError:
            return False
        else:
            return True

    def is_float(self, number):
        try:
            float(number)
        except ValueError:
            return False
        else:
            return True

    def split_number_letter(self, number):
        """Try to split a number in a number and letters."""
        number, letter = re.match(r'([\d.]*)(.)*', number).groups()
        number = number if number else 0
        letter = letter if letter else ''
        return number, letter

    def _title(self, manga_name, issue_name, number, multi_vol, vol,
               total_vols):
        """Generate a title for the MOBI."""
        # Try to extract the name of the issue
        remove = (r'Vol\.?\s*[\d.]+',
                  r'Ch\.?\s*[\d.]+',
                  ':', '-',
                  re.escape(manga_name),
                  number)
        pattern = '|'.join(r'(?:^\s*%s\s*)' % i for i in remove)
        _issue_name = ''
        while issue_name != _issue_name:
            _issue_name = issue_name
            issue_name = re.sub(pattern, '', _issue_name, flags=re.IGNORECASE)

        num, lett = self.split_number_letter(number)
        # Prefix the issue number with zero
        if number and self.is_int(num):
            title = '%s %03d%s' % (manga_name, int(num), lett)
        elif number and self.is_float(num):
            chapter, part = num.split('.')
            title = '%s %03d.%s%s' % (manga_name, float(chapter), part, lett)
        elif number:
            title = '%s %s' % (manga_name, number)
        else:
            title = manga_name
        # Add volume information
        if multi_vol:
            title = '%s (%02d/%02d)' % (title, vol, total_vols)

        if issue_name:
            title = '%s: %s' % (title, issue_name)

        return title


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

    def _create_mobi(self):
        """Create the MOBI file and return a list of files and containers."""
        dir_name = tempfile.mkdtemp(dir=self.mobi_store)
        container = Container(dir_name)
        container.create(clean=True)
        images = sorted(self.images, key=lambda x: x['number'])
        _images = []
        for i in images:
            if i['images']:
                image_path = i['images'][0]['path']
            else:
                image_path = EMPTY
            _images.append(os.path.join(self.images_store, image_path))

        # By default reduce the margin of the image
        _filter = Container.FILTER_MARGIN
        if self.issue.manga.source.has_footer:
            _filter |= Container.FILTER_FOOTER
        container.add_images(_images, adjust=Container.ROTATE,
                             _filter=_filter, as_link=True)

        if container.get_size() > self.volume_max_size:
            containers = container.split(self.volume_max_size, clean=True)
            container.clean()
        else:
            containers = [container]

        mobi_and_containers = []
        for volume, container in enumerate(containers):
            multi_vol, vol = len(containers) > 1, volume + 1
            info = MobiInfo(self.issue, multi_vol, vol, len(containers))

            mobi = MangaMobi(container, info, kindlegen=self.kindlegen)
            mobi_file = mobi.create()
            mobi_and_containers.append((mobi_file, container))
        return mobi_and_containers

    def create_mobi(self):
        """Create the MOBI file and return a list of files and names."""
        cache = MobiCache(settings.MOBI_STORE)

        if self.issue.url not in cache:
            mobi_and_containers = self._create_mobi()
            # XXX TODO - We are not storing stats in the cache anymore (is
            # not the place), so we need to store it in a different place.
            # Maybe in the database?
            cache[self.issue.url] = [m[0] for m in mobi_and_containers]
            # The containers need to be cleaned here.
            for _, container in mobi_and_containers:
                container.clean()

        mobi_info, _ = cache[self.issue.url]
        return mobi_info


@job('low', timeout=2*60*60)
def _create_mobi(issue, result=None):
    """RQ job to create a single MOBI document."""
    issue_cache = IssueCache(settings.ISSUES_STORE, settings.IMAGES_STORE)

    if issue.url not in issue_cache:
        logger.error('Issue not found in issue cache (%s)' % issue)
        if result:
            result.set_status(Result.FAILED)
    elif not issue_cache.is_valid(issue.url):
        logger.error('Issue in issue cache is not valid (%s)' % issue)
        if result:
            result.set_status(Result.FAILED)
        del issue_cache[issue.url]
    else:
        images, _ = issue_cache[issue.url]
        mobictl = MobiCtl(issue, images, settings.IMAGES_STORE)
        mobictl.create_mobi()


@job('high')
def create_mobi(issues):
    """RQ job to create MOBI documents."""
    for issue in issues:
        _create_mobi.delay(issue)


@job('high')
def create_mobi_and_send(issues, user):
    """RQ job to create MOBI documents and send it to the user."""
    for issue in issues:
        try:
            result = issue.create_result_if_needed(user, Result.PROCESSING)
        except Subscription.DoesNotExist:
            # Results in PROCESSING status are cleaned during the
            # subscription removal
            msg = 'Subscription removed for user %s (%s)' % (user, issue)
            logger.warning(msg)
            continue

        # These jobs also update the Result status
        mobi_job = _create_mobi.delay(issue, result=result)
        send_mobi.delay(issue, user, depends_on=mobi_job)
