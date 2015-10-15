import os.path

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import connection
from django.db import models
from django.db.models import Count
from django.db.models import Q
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
    url = models.URLField(unique=True)

    def __str__(self):
        return u'%s (%s)' % (self.name, self.url)


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
        return u'%s (%s)' % (self.get_language_display(), self.language)


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


class AdvRawQuerySet(models.query.RawQuerySet):
    """RawQuerySet subclass with advanced options."""
    def __init__(self, raw_query, paged_query, count_query,
                 model=None, query=None, params=None,
                 translations=None, using=None, hints=None):
        super(AdvRawQuerySet, self).__init__(raw_query, model=model,
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
        if self.params:
            params = self.params + [stop-start, start]
        else:
            params = (stop-start, start)
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
        #   FROM core_issue
        #  WHERE core_issue.manga_id = core_manga.id
        # '''
        # Manga.objects.extra({
        #     'issue__modified__max': extra_query
        # }).order_by('-issue__modified__max')

        raw_query = '''
         SELECT core_manga.id,
                MAX(core_issue.modified) AS issue__modified__max
           FROM core_manga
LEFT OUTER JOIN core_issue
             ON (core_manga.id = core_issue.manga_id)
       GROUP BY core_manga.id
       ORDER BY issue__modified__max DESC,
                core_manga.name ASC,
                core_manga.url ASC;
'''
        paged_query = '''
         SELECT core_manga.id,
                MAX(core_issue.modified) AS issue__modified__max
           FROM core_manga
LEFT OUTER JOIN core_issue
             ON (core_manga.id = core_issue.manga_id)
       GROUP BY core_manga.id
       ORDER BY issue__modified__max DESC,
                core_manga.name ASC,
                core_manga.url ASC
          LIMIT %s
         OFFSET %s;
'''
        count_query = '''
         SELECT COUNT(*)
           FROM core_manga;
'''
        return AdvRawQuerySet(raw_query=raw_query,
                              paged_query=paged_query,
                              count_query=count_query,
                              model=self.model,
                              using=self.db)

    def _to_tsquery(self, q):
        """Convert a query to a PostgreSQL tsquery."""
        # Separate parentesis from words
        for token in ('(', ')'):
            q = q.replace(token, ' %s ' % token)
        # Parse the query
        op = {
            'and': '&',
            'or': '|',
            'not': '-',
            '(': '(',
            ')': ')',
        }
        # Join operators
        j = '&|'
        # Operators that expect and join before
        ops_j = '-('
        tsquery = []
        for token in q.split():
            if token in op:
                if tsquery and op[token] in ops_j and tsquery[-1] not in j:
                    tsquery.append(op['and'])
                tsquery.append(op[token])
            else:
                if tsquery and tsquery[-1] not in (j + ops_j):
                    tsquery.append(op['and'])
                tsquery.append('%s:*' % token)

        # Add spaces between join operators
        tsquery = [(t if t not in j else ' %s ' % t) for t in tsquery]
        return ''.join(tsquery)

    def is_valid(self, q):
        """Check is the query is a valid query."""
        q = self._to_tsquery(q)
        # Separate parentesis from words
        for token in ('(', ')'):
            q = q.replace(token, ' %s ' % token)

        s = []
        for token in q.split():
            if token == '(':
                s.append(token)
            elif token == ')':
                try:
                    t = s.pop()
                except IndexError:
                    return False
                if t != '(':
                    return False
        return not len(s)

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
        return AdvRawQuerySet(raw_query=raw_query,
                              paged_query=paged_query,
                              count_query=count_query,
                              model=self.model,
                              params=[q],
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

    name = models.CharField(max_length=200, db_index=True)
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
    url = models.URLField(unique=True, db_index=True)
    source = models.ForeignKey(Source)

    objects = MangaQuerySet.as_manager()

    def __str__(self):
        return self.name

    def subscribe(self, user, language=None, issues_per_day=4, paused=False):
        """Subscribe an User to the current manga."""
        language = language if language else user.userprofile.language
        obj, created = Subscription.all_objects.update_or_create(
            manga=self,
            user=user,
            defaults={
                'language': language,
                'issues_per_day': issues_per_day,
                'paused': paused,
                'deleted': False,
            })
        return obj

    def is_subscribed(self, user):
        """Check if an user is subscribed to this manga."""
        return self.subscription(user).exists()

    def subscription(self, user):
        """Return the users' subscription of this manga."""
        return self.subscription_set.filter(user=user)

    def languages(self):
        """Return the number of issues per language."""
        return self.issue_set\
                   .values('language')\
                   .order_by('language')\
                   .annotate(Count('language'))


@python_2_unicode_compatible
class AltName(TimeStampedModel):
    name = models.CharField(max_length=200)
    manga = models.ForeignKey(Manga)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Issue(TimeStampedModel):
    name = models.CharField(max_length=200)
    number = models.CharField(max_length=10)
    order = models.IntegerField()
    language = models.CharField(max_length=2,
                                choices=SourceLanguage.LANGUAGE_CHOICES)
    release = models.DateField()
    url = models.URLField(unique=True)
    manga = models.ForeignKey(Manga)

    class Meta:
        ordering = ('order', 'name')

    def __str__(self):
        return self.name

    def is_sent(self, user):
        """Check if an user has received this issue."""
        return self.history(user, status=History.SENT).exists()

    def history(self, user, status=None):
        """Return the History for an user for this issue."""
        # XXX TODO - Avoid filtering by subscription__deleted using
        # the Subscription manager.
        query = self.history_set.filter(
            subscription__user=user,
            subscription__deleted=False)
        if status:
            query = query.filter(status=status)
        return query


class SubscriptionQuerySet(models.QuerySet):
    def latests(self, user):
        """Return the latests subscriptions with history changes."""
        # See the notes from `MangaQuerySet.latests()`
        raw_query = '''
         SELECT core_subscription.id,
                MAX(core_history.modified) AS history__modified__max
           FROM core_subscription
LEFT OUTER JOIN core_history
             ON (core_subscription.id = core_history.subscription_id)
          WHERE core_subscription.deleted = false
            AND core_subscription.user_id = %s
       GROUP BY core_subscription.id
       ORDER BY history__modified__max DESC,
                core_subscription.id ASC;
'''
        paged_query = '''
         SELECT core_subscription.id,
                MAX(core_history.modified) AS history__modified__max
           FROM core_subscription
LEFT OUTER JOIN core_history
            ON (core_subscription.id = core_history.subscription_id)
          WHERE core_subscription.deleted = false
            AND core_subscription.user_id = %s
       GROUP BY core_subscription.id
       ORDER BY history__modified__max DESC,
                core_subscription.id ASC
          LIMIT %s
         OFFSET %s;
'''
        count_query = '''
         SELECT COUNT(*)
           FROM core_subscription
          WHERE core_subscription.deleted = false
            AND core_subscription.user_id = %s;
'''
        return AdvRawQuerySet(raw_query=raw_query,
                              paged_query=paged_query,
                              count_query=count_query,
                              model=self.model,
                              params=[user.id],
                              using=self.db)


class SubscriptionManager(models.Manager):
    def get_queryset(self):
        """Exclude deleted subscriptions."""
        return super(SubscriptionManager,
                     self).get_queryset().exclude(deleted=True)


class SubscriptionActiveManager(models.Manager):
    def get_queryset(self):
        """Exclude paused and deleted subscriptions."""
        return super(SubscriptionActiveManager,
                     self).get_queryset().exclude(
                         Q(paused=True) | Q(deleted=True))


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
    actives = SubscriptionActiveManager.from_queryset(SubscriptionQuerySet)()
    all_objects = models.Manager()

    class Meta:
        unique_together = ('manga', 'user')

    def __str__(self):
        return u'%s (%d per day)' % (self.manga, self.issues_per_day)

    def issues_to_send(self):
        """Return the list of issues to send, ordered by number."""
        already_sent = History.objects.sent_last_24hs(self.user,
                                                      subscription=self)
        remains = max(0, self.issues_per_day-already_sent)
        return self.manga.issue_set.filter(
            language=self.language
        ).exclude(
            pk__in=self.history_set.filter(status__in=(
                History.PROCESSING,
                History.SENT,
                History.FAILED,
            )).values('issue__id')
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
        query = self
        if status:
            query = query.filter(status=status)
        return query.order_by('-modified')

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
            query = query.filter(subscription=subscription)
        if status:
            query = query.filter(status=status)
        return query

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
            query = query.filter(subscription=subscription)
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

    class Meta:
        unique_together = ('issue', 'subscription')

    def __str__(self):
        return u'%s (%s)' % (self.issue, self.get_status_display())

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
