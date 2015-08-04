import os.path

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible


class TimeStampedModel(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


@python_2_unicode_compatible
class Source(TimeStampedModel):
    name = models.CharField(max_length=200)
    spider = models.CharField(max_length=80)
    url = models.URLField()

    def __str__(self):
        return '%s (%s)' % (self.name, self.url)


@python_2_unicode_compatible
class SourceLanguage(TimeStampedModel):
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

    def __str__(self):
        return self.language


@python_2_unicode_compatible
class ConsolidateGenre(TimeStampedModel):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Genre(TimeStampedModel):
    name = models.CharField(max_length=200)
    source = models.ForeignKey(Source)
    # consolidategenre = models.ForeignKey(ConsolidateGenre)

    def __str__(self):
        return self.name


class FTSRawQuerySet(models.query.RawQuerySet):
    """RawQuerySet subclass with advanced options."""
    def __init__(self, raw_query, paged_query, count_query,
                 model=None, query=None, params=None,
                 translations=None, using=None, hints=None):
        super(FTSRawQuerySet, self).__init__(raw_query, model=model,
                                             query=query,
                                             params=params,
                                             translations=translations,
                                             using=using, hints=hints)
        self.raw_query = raw_query
        self.paged_query = paged_query
        self.count_query = count_query

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
        cursor.execute(self.count_query, self.params)
        return cursor.fetchone()[0]


class MangaQuerySet(models.QuerySet):
    def latests(self):
        """Return the lastest mangas with new/updated issues."""
        # The correct annotation expression is the next one, but due
        # to an error in Django ORM, this empression uses a full GROUP
        # BY with the data fields.  This produce a slow query.
        #
        # return self.annotate(
        #     models.Max('issue__modified')
        # ).order_by('-issue__modified__max')
        #
        # Alternative (without deferreds)
        #
        # extra_query = '''
        # SELECT MAX(core_issue.modified)
        # FROM core_issue
        # WHERE core_issue.manga_id = core_manga.id
        # '''
        # Manga.objects.extra({
        #     'issue__modified__max': extra_query
        # }).order_by('-issue__modified__max')

        raw_query = '''
SELECT core_manga.id,
       MAX(core_issue.modified) AS issue__modified__max
FROM core_manga
LEFT OUTER JOIN core_issue ON (core_manga.id = core_issue.manga_id)
GROUP BY core_manga.id
ORDER BY issue__modified__max DESC;
'''
        return self.raw(raw_query)

    def _to_tsquery(self, q):
        """Convert a query with the prefix syntax."""
        return ' & '.join(u + ':*' for u in q.split())

    def search(self, q):
        q = self._to_tsquery(q)
        raw_query = '''
SELECT core_manga.*
FROM (
  SELECT id
  FROM core_manga_fts_view,
       to_tsquery(%s) AS q
  WHERE document @@ q
  ORDER BY ts_rank(document, q) DESC,
           name ASC,
           url ASC
) AS ids
INNER JOIN core_manga ON core_manga.id = ids.id;
'''
        paged_query = '''
SELECT core_manga.*
FROM (
  SELECT id
  FROM core_manga_fts_view,
       to_tsquery(%s) AS q
  WHERE document @@ q
  ORDER BY ts_rank(document, q) DESC,
           name ASC,
           url ASC
  LIMIT %s
  OFFSET %s
) AS ids
INNER JOIN core_manga ON core_manga.id = ids.id;
'''
        count_query = '''
SELECT COUNT(*)
FROM core_manga_fts_view
WHERE document @@ to_tsquery(%s);
'''
        return FTSRawQuerySet(raw_query=raw_query,
                              paged_query=paged_query,
                              count_query=count_query,
                              model=self.model, params=[q],
                              using=self.db)

    def refresh(self):
        cursor = connection.cursor()
        cursor.execute('REFRESH MATERIALIZED VIEW core_manga_fts_view;')


def _cover_path(instance, filename):
    return os.path.join(instance.source.spider, filename)


@python_2_unicode_compatible
class Manga(TimeStampedModel):
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
    rank = models.FloatField(null=True, blank=True)
    rank_order = models.CharField(max_length=4,
                                  choices=RANK_ORDER,
                                  default=ASC)
    description = models.TextField()
    cover = models.ImageField(upload_to=_cover_path)
    url = models.URLField()
    source = models.ForeignKey(Source)

    objects = MangaQuerySet.as_manager()

    def __str__(self):
        return self.name

    def subscribe(self, user, language=None, issues_per_day=4, paused=False):
        """Subscribe an User to the current manga."""
        language = language if language else user.userprofile.language
        obj, created = Subscription.objects.update_or_create(
            manga=self,
            user=user,
            defaults={
                'language': language,
                'issues_per_day': issues_per_day,
                'paused': paused,
            })
        return obj

    def is_subscribed(self, user):
        """Check if an user is subscribed to this manga."""
        return self.subscription(user).exists()

    def subscription(self, user):
        """Return the users' subscription of this manga."""
        return self.subscription_set.filter(user=user)


@python_2_unicode_compatible
class AltName(TimeStampedModel):
    name = models.CharField(max_length=200)
    manga = models.ForeignKey(Manga)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Issue(TimeStampedModel):
    name = models.CharField(max_length=200)
    number = models.DecimalField(max_digits=5, decimal_places=1)
    language = models.CharField(max_length=2,
                                choices=SourceLanguage.LANGUAGE_CHOICES)
    release = models.DateField()
    url = models.URLField()
    manga = models.ForeignKey(Manga)

    class Meta:
        ordering = ('number', 'name')

    def __str__(self):
        return self.name

    def is_sent(self, user):
        """Check if an user has received this issue."""
        return self.history(user).exists()

    def history(self, user):
        """Return the History for an user for this issue."""
        return self.history_set.filter(issue=self,
                                       subscription__user=user)


class SubscriptionQuerySet(models.QuerySet):
    def latests(self):
        """Return the latests subscriptions with history changes."""
        # See the notes from `MangaQuerySet.latests()`
        return self.filter(pk__in=self.values('pk').annotate(
            models.Max('history__modified')
        ).order_by('-history__modified__max').values('pk'))
        raw_query = '''
SELECT core_subscription.id,
       MAX(core_history.modified) AS history__modified__max
FROM core_subscription
LEFT OUTER JOIN core_history ON (core_subscription.id = core_history.subscription_id)
GROUP BY core_subscription.id
ORDER BY history__modified__max DESC;
'''
        return self.raw(raw_query)


class SubscriptionManager(models.Manager):
    def get_queryset(self):
        """Exclude deleted subscriptions."""
        return super(SubscriptionManager,
                     self).get_queryset().exclude(deleted=True)


@python_2_unicode_compatible
class Subscription(TimeStampedModel):
    manga = models.ForeignKey(Manga)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    language = models.CharField(max_length=2,
                                choices=SourceLanguage.LANGUAGE_CHOICES)
    issues_per_day = models.IntegerField(default=4)
    paused = models.BooleanField(default=False)
    deleted = models.BooleanField(default=False)

    objects = SubscriptionManager.from_queryset(SubscriptionQuerySet)()
    all_objects = models.Manager()

    class Meta:
        unique_together = ('manga', 'user')

    def __str__(self):
        return '%s (%d per day)' % (self.manga, self.issues_per_day)

    def issues_to_send(self):
        """Return the list of issues to send, ordered by number."""
        already_sent = History.objects.sent_last_24hs(self.user,
                                                      subscription=self)
        remains = max(0, self.issues_per_day-already_sent)
        return self.manga.issue_set.filter(
            language=self.language
        ).exclude(
            pk__in=self.history_set.values('issue_id')
        ).order_by('number')[:remains]

    def add_sent(self, issue):
        """Add or update an History to a Subscription."""
        return History.objects.update_or_create(
            issue=issue,
            subscription=self,
            defaults={
                'send_date': timezone.now(),
                'status': History.SENT,
            })


class HistoryQuerySet(models.QuerySet):
    def latests(self, status=None):
        latests = self
        if status:
            latests = latests.filter(status=status)
        return latests.annotate(
            models.Max('modified')
        ).order_by('-modified__max')

    def _modified_last_24hs(self, user, subscription=None, status=None):
        """Return the list of `History` modified during the last 24 hours."""
        today = timezone.now()
        yesterday = today - timezone.timedelta(days=1)
        # TODO XXX - Objects are created / modified always after time
        # T.  If the send process is slow, the error margin can be
        # bigger than the one used here.
        yesterday += timezone.timedelta(hours=4)
        query = self.filter(
            subscription__user=user,
            modified__range=[yesterday, today],
        )
        if subscription:
            query.filter(subscription=subscription)
        if status:
            query.filter(status=status)
        return query.count()

    def modified_last_24hs(self, user, subscription=None, status=None):
        """Return the number of `History` modified during the last 24 hours."""
        return self._modified_last_24hs(user, subscription, status).count()

    def _sent_last_24hs(self, user, subscription=None):
        """Return the list of `History` sent during the last 24 hours."""
        today = timezone.now()
        yesterday = today - timezone.timedelta(days=1)
        # TODO XXX - Objects are created / modified always after time
        # T.  If the send process is slow, the error margin can be
        # bigger than the one used here.
        yesterday += timezone.timedelta(hours=4)
        query = self.filter(
            subscription__user=user,
            send_date__range=[yesterday, today],
            status=History.SENT,
        )
        if subscription:
            query.filter(subscription=subscription)
        return query

    def sent_last_24hs(self, user, subscription=None):
        """Return the number of `History` sent during the last 24 hours."""
        return self._sent_last_24hs(user, subscription).count()

    def pending(self):
        return self.latests(status=History.PENDING)

    def processing(self):
        return self.latests(status=History.PROCESSING)

    def sent(self):
        return self.latests(status=History.SENT)

    def failed(self):
        return self.latests(status=History.FAILED)


@python_2_unicode_compatible
class History(TimeStampedModel):
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
    missing_pages = models.IntegerField(default=0)
    send_date = models.DateTimeField(null=True, blank=True)

    objects = HistoryQuerySet.as_manager()

    def __str__(self):
        return '%s (%s)' % (self.issue, self.get_status_display())

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})

    def is_pending(self):
        return self.status == History.PENDING

    def is_processing(self):
        return self.status == History.PROCESSING

    def is_sent(self):
        return self.status == History.SENT

    def is_failed(self):
        return self.status == History.FAILED
