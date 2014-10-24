from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from scrapyctl.manga import run_spider


@python_2_unicode_compatible
class Source(models.Model):
    name = models.CharField(max_length=200)
    spider = models.CharField(max_length=80)
    url = models.URLField()

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

    def __str__(self):
        return self.language


@python_2_unicode_compatible
class ConsolidateGenre(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class Genre(models.Model):
    name = models.CharField(max_length=200)
    source = models.ForeignKey(Source)
    # consolidategenre = models.ForeignKey(ConsolidateGenre)

    def __str__(self):
        return self.name


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
    cover = models.ImageField()
    url = models.URLField()
    source = models.ForeignKey(Source)

    def __str__(self):
        return self.name


@python_2_unicode_compatible
class AltName(models.Model):
    name = models.CharField(max_length=200)
    manga = models.ForeignKey(Manga)

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

    def __str__(self):
        return '%s %s: %s' % (self.manga.name, self.number, self.name)


@python_2_unicode_compatible
class History(models.Model):
    name = models.CharField(max_length=200)
    from_issue = models.IntegerField()
    to_issue = models.IntegerField()
    to_email = models.EmailField()
    send_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return '%s [%03d-%03d]' % (self.name, self.from_issue, self.to_issue)

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})


@python_2_unicode_compatible
class HistoryLine(models.Model):
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

    history = models.ForeignKey(History)
    issue = models.IntegerField()
    status = models.CharField(max_length=2, choices=STATUS_CHOICES,
                              default=PENDING)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '%s [%s]' % (self.status, self.updated)

    def send_mobi(self):
        run_spider('mangareader', self.history.name, self.issue,
                   self.history.to_email)
