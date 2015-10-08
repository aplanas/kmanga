from django.db import models
from django.utils.encoding import python_2_unicode_compatible

from core.models import Source
from core.models import TimeStampedModel


@python_2_unicode_compatible
class Proxy(TimeStampedModel):
    proxy = models.CharField(max_length=32)
    source = models.ForeignKey(Source)

    class Meta:
        unique_together = ('proxy', 'source')

    def __str__(self):
        return u'%s (%s)' % (self.proxy, self.source.name)
