from django.db import models

from core.models import Source
from core.models import TimeStampedModel


class ProxyQuerySet(models.QuerySet):
    def get_one(self, spider):
        """Get one proxy for a specific source."""
        return self.filter(source__spider=spider).order_by('?').first()

    def discard(self, proxy, spider):
        """Discard a proxy that is failing."""
        try:
            proxy = self.get(proxy=proxy, source__spider=spider)
            proxy.discard()
        except Proxy.DoesNotExist:
            pass

    def remainings(self, spider):
        """Return the number of proxy for a source."""
        return self.filter(source__spider=spider).count()


class Proxy(TimeStampedModel):
    # Number of retries before giving up and removing the entry
    RETRY = 3

    proxy = models.CharField(max_length=32)
    source = models.ForeignKey(Source, on_delete=models.CASCADE)
    retry = models.IntegerField(default=0)

    objects = ProxyQuerySet.as_manager()

    class Meta:
        unique_together = ('proxy', 'source')

    def __str__(self):
        return '%s (%s)' % (self.proxy, self.source.name)

    def discard(self):
        """Discard a proxy that is failing."""
        self.retry += 1
        if self.retry <= Proxy.RETRY:
            self.save()
        else:
            self.delete()
