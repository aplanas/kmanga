from __future__ import absolute_import

import logging

from core.models import Result
from scrapyctl.mobictl import create_mobi_and_send
from scrapyctl.scrapyctl import scrape_issues


def send(issues, user, accounts=None, loglevel=logging.WARNING):
    """Send a list of issues to an user."""

    if issues:
        for issue in issues:
            issue.create_result_if_needed(user, Result.PROCESSING)
        scrape_job = scrape_issues.delay(issues, accounts, loglevel)
        # This job also update the Result status
        create_mobi_and_send.delay(issues, user, depends_on=scrape_job)
