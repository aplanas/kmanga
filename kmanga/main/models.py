from django.core.urlresolvers import reverse
from django.db import models


class History(models.Model):
    name = models.CharField(max_length=200)
    from_issue = models.IntegerField()
    to_issue = models.IntegerField()
    from_email = models.EmailField()
    to_email = models.EmailField()
    send_date = models.DateTimeField()

    def __unicode__(self):
        return '%s [%03d-%03d]' % (self.name, self.from_issue, self.to_issue)

    def get_absolute_url(self):
        return reverse('history-detail', kwargs={'pk': self.pk})
