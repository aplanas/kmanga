from django.conf import settings
from django.db import models

from core.models import Result


class UserProfile(models.Model):
    FREE = 'F'
    PAY = 'P'
    MODE_CHOICES = (
        (FREE, 'Non-pay user'),
        (PAY, 'Pay user'),
    )
    GERMAN = 'DE'
    ENGLISH = 'EN'
    SPANISH = 'ES'
    FRENCH = 'FR'
    ITALIAN = 'IT'
    RUSSIAN = 'RU'
    PORTUGUESE = 'PT'
    LANGUAGE_CHOICES = (
        (ENGLISH, 'English'),
        (SPANISH, 'Spanish'),
        (GERMAN, 'German'),
        (FRENCH, 'French'),
        (ITALIAN, 'Italian'),
        (RUSSIAN, 'Russian'),
        (PORTUGUESE, 'Portuguese'),
    )
    TIME_ZONE_CHOICES = [
        (i, 'UTC%+03d:00' % i) for i in range(-12, 15)
    ]
    HOUR_CHOICES = [
        (i, '%02d:00' % i) for i in range(0, 24)
    ]
    ISSUES_PER_DAY = {
        FREE: 30,
        PAY: 60,
    }

    user = models.OneToOneField(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                primary_key=True)
    mode = models.CharField(max_length=1, choices=MODE_CHOICES,
                            default=FREE)
    language = models.CharField(max_length=2,
                                choices=LANGUAGE_CHOICES)
    time_zone = models.IntegerField(choices=TIME_ZONE_CHOICES, default=0)
    send_at = models.IntegerField(choices=HOUR_CHOICES, default=0)
    issues_per_day = models.IntegerField(default=ISSUES_PER_DAY[FREE])
    email_kindle = models.EmailField(unique=True)

    def __str__(self):
        return self.user.username

    def remains(self):
        """Calculate remaining issues per day."""
        already_sent = Result.objects.processed_last_24hs(self.user)
        remains = max(0, self.issues_per_day-already_sent)
        return remains
