from django.core.urlresolvers import reverse
from django.db import models

from .manga import run_spider


class History(models.Model):
    name = models.CharField(max_length=200)
    from_issue = models.IntegerField()
    to_issue = models.IntegerField()
    from_email = models.EmailField()
    to_email = models.EmailField()
    send_date = models.DateTimeField(auto_now_add=True)

    def __unicode__(self):
        return '%s [%03d-%03d]' % (self.name, self.from_issue, self.to_issue)

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})


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

    def __unicode__(self):
        return '%s [%s]' % (self.status, self.updated)

    def send_mobi(self):
        run_spider('mangareader', self.history.name, self.issue,
                   self.history.from_email, self.history.to_email)
