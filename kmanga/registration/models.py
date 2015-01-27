from django.conf import settings
from django.db import models


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
    LANGUAGE_CHOICES = (
        (ENGLISH, 'English'),
        (SPANISH, 'Spanish'),
        (GERMAN, 'German'),
        (FRENCH, 'French'),
        (ITALIAN, 'Italian'),
        (RUSSIAN, 'Russian'),
    )

    user = models.OneToOneField(settings.AUTH_USER_MODEL)
    mode = models.CharField(max_length=1, choices=MODE_CHOICES,
                            default=FREE)
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES)
    email_kindle = models.EmailField()
