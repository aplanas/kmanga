import os.path

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

# from scrapyctl.utils import send


@python_2_unicode_compatible
class Source(models.Model):
    name = models.CharField(max_length=200)
    spider = models.CharField(max_length=80)
    url = models.URLField()
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

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
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def __str__(self):
        return self.language


@python_2_unicode_compatible
class ConsolidateGenre(models.Model):
    name = models.CharField(max_length=200)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Genre(models.Model):
    name = models.CharField(max_length=200)
    source = models.ForeignKey(Source)
    # consolidategenre = models.ForeignKey(ConsolidateGenre)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def __str__(self):
        return self.name


class MangaQuerySet(models.QuerySet):
    def latests(self):
        return self.annotate(
            models.Max('issue__last_modified')
        ).order_by('-issue__last_modified__max')


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
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    objects = MangaQuerySet.as_manager()

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class AltName(models.Model):
    name = models.CharField(max_length=200)
    manga = models.ForeignKey(Manga)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

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
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def __str__(self):
        return self.name


class SubscriptionQuerySet(models.QuerySet):
    def latests(self, user):
        return self.filter(user=user).annotate(
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


@python_2_unicode_compatible
class History(models.Model):
    PENDING = 'PE'
    PROCESSING = 'PR'
    SEND = 'SE'
    FAIL = 'FA'
    STATUS_CHOICES = (
        (PENDING, 'Pending'),
        (PROCESSING, 'Processing'),
        (SEND, 'Send'),
        (FAIL, 'Fail'),
    )

    issue = models.ForeignKey(Issue)
    subscription = models.ForeignKey(Subscription)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES,
                              default=PENDING)
    send_date = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True, auto_now_add=True)

    def __str__(self):
        return '%s (%s)' % (self.issue, self.get_status_display())

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})
