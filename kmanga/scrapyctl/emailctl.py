import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django_rq import job

from core.models import Result
from mobi.cache import MobiCache

logger = logging.getLogger(__name__)


@job('high', timeout=15*60)
def send_mobi(issue, user):
    """RQ job to send MOBI documents."""
    mobi_cache = MobiCache(settings.MOBI_STORE)

    result = issue.create_result_if_needed(user, Result.PROCESSING)

    if issue.url not in mobi_cache:
        logger.error('Issue not found in mobi cache (%s)' % issue)
        result.set_status(Result.FAILED)
        return
    # Ignore the creation date from the cache.
    mobi_info, _ = mobi_cache[issue.url]

    email = user.userprofile.email_kindle
    for mobi_name, mobi_file in mobi_info:
        try:
            EmailMessage(
                subject='Your kmanga.net request',
                body='',
                from_email=settings.KMANGA_EMAIL,
                to=[email],
                attachments=[(mobi_name, open(mobi_file, 'rb').read(),
                              'application/x-mobipocket-ebook')]
            ).send()
        except Exception:
            logger.error('Error while sending issue (%s) to (%s)' % (issue,
                                                                     user))
            result.set_status(Result.FAILED)
        else:
            result.set_status(Result.SENT)
