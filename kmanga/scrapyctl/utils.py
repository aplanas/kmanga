import logging

from core.models import Result
from proxy.utils import needs_proxy
from scrapyctl.mobictl import create_mobi_and_send
from scrapyctl.scrapyctl import scrape_issues
from scrapyctl.scrapyctl import scrape_issues_slow


def send(issues, user, accounts=None, loglevel=logging.WARNING):
    """Send a list of issues to an user."""

    for issue in issues:
        issue.create_result_if_needed(user, Result.PROCESSING)

    # Split the issues in `fast` (direct access) and `slow` (needs proxy)
    fast_issues = [i for i in issues if not needs_proxy(i.manga.source.spider)]
    slow_issues = [i for i in issues if needs_proxy(i.manga.source.spider)]

    if fast_issues:
        scrape_job = scrape_issues.delay(fast_issues, accounts, loglevel)
        # This job also update the Result status
        create_mobi_and_send.delay(fast_issues, user, depends_on=scrape_job)

    if slow_issues:
        scrape_job = scrape_issues_slow.delay(slow_issues, accounts, loglevel)
        # This job also update the Result status
        create_mobi_and_send.delay(slow_issues, user, depends_on=scrape_job)
