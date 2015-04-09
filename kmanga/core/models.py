import os.path
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Source(models.Model):
    name = models.CharField(max_length=200)
    spider = models.CharField(max_length=80)
    url = models.URLField()
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s (%s)' % (self.name, self.url)


@python_2_unicode_compatible
class SourceLanguage(models.Model):
    GERMAN = 'DE'
    ENGLISH = 'EN'
    SPANISH = 'ES'
    FRENCH = 'FR'
    ITALIAN = 'IT'
    RUSSIAN = 'RU'
    LANGUAGE_CHOICES = (
        (ENGLISH, 'English'),
        (SPANISH, 'Spanish'),
        (GERMAN, 'German'),
        (FRENCH, 'French'),
        (ITALIAN, 'Italian'),
        (RUSSIAN, 'Russian'),
    )

    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    source = models.ForeignKey(Source)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.language


@python_2_unicode_compatible
class ConsolidateGenre(models.Model):
    name = models.CharField(max_length=200)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Genre(models.Model):
    name = models.CharField(max_length=200)
    source = models.ForeignKey(Source)
    # consolidategenre = models.ForeignKey(ConsolidateGenre)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class FTSRawQuerySet(models.query.RawQuerySet):
    """RawQuerySet subclass with advanced options."""
    def __init__(self, raw_query, model=None, query=None, params=None,
                 translations=None, using=None, hints=None):
        super(FTSRawQuerySet, self).__init__(raw_query, model=model,
                                             query=query,
                                             params=params,
                                             translations=translations,
                                             using=using, hints=hints)
        # XXX TODO - Store a version of `raw_query` more easy to
        # manipulate the head and the tail.  Potentially this change
        # can break the query.
        self.raw_query = ' '.join(raw_query.split())

        self.count_query = re.sub(r'^SELECT .*? FROM', 'SELECT COUNT(*) FROM',
                                  self.raw_query)
        self.count_query = re.sub(' ORDER BY .*$', ';', self.count_query)

        self.paged_query = self.raw_query
        if self.paged_query.endswith(';'):
            self.paged_query = self.paged_query[:-1]
        self.paged_query += ' LIMIT %s OFFSET %s;'

    def __getitem__(self, key):
        if isinstance(key, slice):
            start, stop = key.start, key.stop
        else:
            start, stop = key, key + 1
        params = self.params + [stop-start, start]
        return models.query.RawQuerySet(self.paged_query,
                                        model=self.model,
                                        params=params,
                                        translations=self.translations,
                                        using=self._db,
                                        hints=self._hints)

    def __len__(self):
        cursor = connection.cursor()
        # Remove the last elements of `self.params` to adjust it to
        # the real number of parameters.  We can, potentially, remove
        # the one used for the ORDER BY.
        nparams = self.count_query.count('%s')
        params = self.params
        if nparams < len(params):
            params = params[:nparams-len(params)]
        cursor.execute(self.count_query, params)
        return cursor.fetchone()[0]


class MangaQuerySet(models.QuerySet):
    def latests(self):
        return self.annotate(
            models.Max('issue__last_modified')
        ).order_by('-issue__last_modified__max')

    def _to_tsquery(self, q):
        """Convert a query with the prefix syntax."""
        return ' & '.join(u + ':*' for u in q.split())

    def search(self, q):
        q = self._to_tsquery(q)
        return FTSRawQuerySet('''
SELECT core_manga.*
FROM core_manga
JOIN core_manga_fts_view ON core_manga.id = core_manga_fts_view.id
WHERE core_manga_fts_view.document @@ to_tsquery(%s)
ORDER BY ts_rank(core_manga_fts_view.document, to_tsquery(%s)) DESC;
        ''', model=self.model, params=[q, q], using=self.db)

    def refresh(self):
        cursor = connection.cursor()
        cursor.execute('REFRESH MATERIALIZED VIEW core_manga_fts_view;')


def _cover_path(instance, filename):
    return os.path.join(instance.source.spider, filename)


@python_2_unicode_compatible
class Manga(models.Model):
    LEFT_TO_RIGHT = 'LR'
    RIGHT_TO_LEFT = 'RL'
    READING_DIRECTION = (
        (LEFT_TO_RIGHT, 'Left-to-right'),
        (RIGHT_TO_LEFT, 'Right-to-left'),
    )

    ONGOING = 'O'
    COMPLETED = 'C'
    STATUS = (
        (ONGOING, 'Ongoing'),
        (COMPLETED, 'Completed'),
    )

    ASC = 'ASC'
    DESC = 'DESC'
    RANK_ORDER = (
        (ASC, 'Ascending'),
        (DESC, 'Descending'),
    )

    name = models.CharField(max_length=200)
    # slug = models.SlugField(max_length=200)
    # release = models.DateField()
    author = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    reading_direction = models.CharField(max_length=2,
                                         choices=READING_DIRECTION,
                                         default=RIGHT_TO_LEFT)
    status = models.CharField(max_length=1,
                              choices=STATUS,
                              default=ONGOING)
    genres = models.ManyToManyField(Genre)
    rank = models.IntegerField(null=True, blank=True)
    rank_order = models.CharField(max_length=4,
                                  choices=RANK_ORDER,
                                  default=ASC)
    description = models.TextField()
    cover = models.ImageField(upload_to=_cover_path)
    url = models.URLField()
    source = models.ForeignKey(Source)
    last_modified = models.DateTimeField(auto_now=True)

    objects = MangaQuerySet.as_manager()

    def __str__(self):
        return self.name

    def subscribe(self, user, issues_per_day=2, paused=False):
        """Subscribe an User to the current Manga."""
        return Subscription.objects.create(
            manga=self,
            user=user,
            issues_per_day=issues_per_day,
            paused=paused)


@python_2_unicode_compatible
class AltName(models.Model):
    name = models.CharField(max_length=200)
    manga = models.ForeignKey(Manga)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Issue(models.Model):
    name = models.CharField(max_length=200)
    number = models.DecimalField(max_digits=5, decimal_places=1)
    language = models.CharField(max_length=2,
                                choices=SourceLanguage.LANGUAGE_CHOICES)
    release = models.DateField()
    url = models.URLField()
    manga = models.ForeignKey(Manga)
    last_modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class SubscriptionQuerySet(models.QuerySet):
    def latests(self):
        return self.annotate(
            models.Max('history__send_date')
        ).order_by('-history__send_date__max')


@python_2_unicode_compatible
class Subscription(models.Model):
    manga = models.ForeignKey(Manga)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    issues_per_day = models.IntegerField(default=2)
    paused = models.BooleanField(default=False)

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        unique_together = ('manga', 'user')

    def __str__(self):
        return '%s (%d per day)' % (self.manga, self.issues_per_day)


class HistoryQuerySet(models.QuerySet):
    def latests(self, status=None):
        latests = self
        if status:
            latests = latests.filter(status=status)
        return latests.annotate(
            models.Max('send_date')
        ).order_by('-send_date__max')

    def pending(self):
        return self.latests(status=History.PENDING)

    def processing(self):
        return self.latests(status=History.PROCESSING)

    def sent(self):
        return self.latests(status=History.SENT)

    def failed(self):
        return self.latests(status=History.FAILED)


@python_2_unicode_compatible
class History(models.Model):
    PENDING = 'PE'
    PROCESSING = 'PR'
    SENT = 'SE'
    FAILED = 'FA'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SENT, 'Sent'),
        (FAILED, 'Failed'),
    )

    issue = models.ForeignKey(Issue)
    subscription = models.ForeignKey(Subscription)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES,
                              default=PENDING)
    send_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)

    objects = HistoryQuerySet.as_manager()

    def __str__(self):
        return '%s (%s)' % (self.issue, self.get_status_display())

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})

    def is_pending(self):
        return self.status == 'PE'

    def is_processing(self):
        return self.status == 'PR'

    def is_sent(self):
        return self.status == 'SE'

    def is_failed(self):
        return self.status == 'FA'
