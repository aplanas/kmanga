from django.test import TestCase

from core.models import AltName
from core.models import Genre
from core.models import History
from core.models import Issue
from core.models import Manga
from core.models import Source
from core.models import SourceLanguage
from core.models import Subscription
from registration.models import UserProfile


class SourceTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test source representation."""
        self.assertEqual(str(Source.objects.get(pk=1)),
                         'Source 1 (http://source1.com)')


class SourceLanguageTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test source language representation."""
        self.assertEqual(str(SourceLanguage.objects.get(pk=1)),
                         'English (EN)')


class GenreTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test genre representation."""
        self.assertEqual(str(Genre.objects.get(pk=1)),
                         'source1_genre1')


class MangaTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_full_text_search_basic(self):
        """Test basic FTS operations."""
        # Initially the materialized view empty
        Manga.objects.refresh()

        # Search for a common keyword
        self.assertEqual(
            len(Manga.objects.search('Description')), 4)

        # Search for specific keyword in the name
        m = Manga.objects.get(name='Manga 1')
        old_value = m.name
        m.name = 'keyword'
        m.save()
        Manga.objects.refresh()
        q = Manga.objects.search('keyword')
        self.assertEqual(len(q), 1)
        self.assertEqual(iter(q).next(), m)
        m.name = old_value
        m.save()
        Manga.objects.refresh()
        self.assertEqual(
            len(Manga.objects.search('keyword')), 0)

        # Search for specific keyword in alt_name
        q = Manga.objects.search('One')
        self.assertEqual(len(q), 1)
        self.assertEqual(
            iter(q).next(),
            Manga.objects.get(name='Manga 1'))

        q = Manga.objects.search('Two')
        self.assertEqual(len(q), 1)
        self.assertEqual(
            iter(q).next(),
            Manga.objects.get(name='Manga 2'))

        # Search for specific keyword in description
        m = Manga.objects.get(name='Manga 3')
        old_value = m.description
        m.description += ' keyword'
        m.save()
        Manga.objects.refresh()
        q = Manga.objects.search('keyword')
        self.assertEqual(len(q), 1)
        self.assertEqual(iter(q).next(), m)
        m.description = old_value
        m.save()
        Manga.objects.refresh()
        self.assertEqual(
            len(Manga.objects.search('keyword')), 0)

    def test_full_text_search_rank(self):
        """Test FTS ranking."""
        # Initially the materialized view empty
        Manga.objects.refresh()

        # Add the same keywork in the name and in the description.
        # Because the name is more important, the first result must be
        # the one with the keyword in it.
        m1 = Manga.objects.get(name='Manga 3')
        m1.name = 'keyword'
        m1.save()
        m2 = Manga.objects.get(name='Manga 4')
        m2.description += ' keyword'
        m2.save()
        Manga.objects.refresh()

        q = Manga.objects.search('keyword')
        self.assertEqual(len(q), 2)
        _iter = iter(q)
        self.assertEqual(_iter.next(), m1)
        self.assertEqual(_iter.next(), m2)

    def test_full_text_search_index(self):
        """Test indexing (__getitem__) FTS operations."""
        # Initially the materialized view empty
        Manga.objects.refresh()

        ms1 = list(Manga.objects.search('Description'))
        ms2 = list(Manga.objects.search('Description')[1])
        ms3 = list(Manga.objects.search('Description')[1:3])
        self.assertEqual(len(ms1), 4)
        self.assertEqual(len(ms2), 1)
        self.assertEqual(len(ms3), 2)
        self.assertEqual(ms1.index(ms2[0]), 1)
        self.assertEqual(ms1.index(ms3[0]), 1)
        self.assertEqual(ms1.index(ms3[1]), 2)

    def test_latests(self):
        """Test the recovery of updated mangas."""
        # Random order where we expect the mangas
        names = ['Manga 2', 'Manga 4', 'Manga 1', 'Manga 3']
        for name in reversed(names):
            issue = Issue.objects.get(name='%s issue 1' % name.lower())
            issue.name += ' - %s' % name
            issue.save()

        for manga, name in zip(Manga.objects.latests(), names):
            self.assertEqual(manga.name, name)

        ml1 = Manga.objects.latests()
        ml2 = Manga.objects.latests()[1]
        ml3 = Manga.objects.latests()[1:3]
        self.assertEqual(len(ml1), 4)
        self.assertEqual(len(list(ml2)), 1)
        self.assertEqual(len(list(ml3)), 2)
        ml1 = [m.name for m in ml1]
        ml2 = [m.name for m in ml2]
        ml3 = [m.name for m in ml3]
        self.assertEqual(ml1, names)
        self.assertEqual(ml2, names[1:2])
        self.assertEqual(ml3, names[1:3])

    def test_str(self):
        """Test manga representation."""
        self.assertEqual(str(Manga.objects.get(pk=1)),
                         'Manga 1')

    def test_subscribe(self):
        """Test the method to subscrive an user to a manga."""
        # The fixture have 4 mangas and two users.  The last manga
        # have no subscrivers, and `Manga 3` is `deleted`
        user = UserProfile.objects.get(pk=1).user

        self.assertTrue(
            Manga.objects.get(name='Manga 1').is_subscribed(user))
        self.assertTrue(
            Manga.objects.get(name='Manga 2').is_subscribed(user))
        self.assertFalse(
            Manga.objects.get(name='Manga 3').is_subscribed(user))
        self.assertFalse(
            Manga.objects.get(name='Manga 4').is_subscribed(user))

        manga = Manga.objects.get(name='Manga 4')
        manga.subscribe(user)
        self.assertTrue(manga.is_subscribed(user))
        self.assertEqual(manga.subscription_set.count(), 1)
        self.assertEqual(manga.subscription_set.all()[0].user, user)

        manga = Manga.objects.get(name='Manga 3')
        manga.subscribe(user)
        self.assertTrue(manga.is_subscribed(user))
        self.assertEqual(manga.subscription_set.count(), 1)
        self.assertEqual(manga.subscription_set.all()[0].user, user)
        self.assertEqual(
            Subscription.all_objects.filter(user=user).count(), 4)


class AltNameTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test alt name representation."""
        self.assertEqual(str(AltName.objects.get(pk=1)),
                         'Manga One')


class IssueTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test issue representation"""
        self.assertEqual(str(Issue.objects.get(pk=1)),
                         'manga 1 issue 1')

    def test_is_sent(self):
        """Test if an issue was sent to an user."""
        # The fixture have one issue sent to both users. For user 1
        # was a success, but not for user 2.
        #
        # There is also, for user 1, a issue send via the third
        # subscription, that is deleted.
        user1 = UserProfile.objects.get(pk=1).user
        user2 = UserProfile.objects.get(pk=2).user

        issue_sent = Issue.objects.get(name='manga 1 issue 1')
        for issue in Issue.objects.all():
            if issue == issue_sent:
                self.assertTrue(issue.is_sent(user1))
                self.assertFalse(issue.is_sent(user2))
            else:
                self.assertFalse(issue.is_sent(user1))
                self.assertFalse(issue.is_sent(user2))

    def test_history(self):
        """Test the history of an issue."""
        # Read `test_is_sent` for a description of the fixture.
        user1 = UserProfile.objects.get(pk=1).user
        user2 = UserProfile.objects.get(pk=2).user

        issue_sent = Issue.objects.get(name='manga 1 issue 1')
        for issue in Issue.objects.all():
            if issue == issue_sent:
                self.assertEqual(len(issue.history(user1)), 1)
                self.assertEqual(len(issue.history(user2)), 1)
            else:
                self.assertEqual(len(issue.history(user1)), 0)
                self.assertEqual(len(issue.history(user2)), 0)


class SubscriptionTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_subscription_manager(self):
        """Test the subscription manager."""
        # There are six subscriptions, three for each user, and each
        # with a different state (active, paused, deleted)
        #
        # The subsctription manager are expected to filter deleted
        # instances.
        self.assertEqual(Subscription.objects.count(), 4)
        self.assertEqual(Subscription.all_objects.count(), 6)

    def test_latests(self):
        """Test the recovery of updated subscriptions."""
        # There are six subscriptions, three for each user, and each
        # with a different state (active, paused, deleted)
        for subs in Subscription.all_objects.order_by('pk'):
            issue = subs.manga.issue_set.first()
            subs.add_sent(issue)

        # Check that deleted subscriptions are not included
        rqs = Subscription.objects.latests()
        self.assertEqual(len(list(rqs)), 4)
        self.assertEqual(Subscription.all_objects.count(), 6)

        # Check that subscription can be indexed
        self.assertEqual(len(list(rqs[1])), 1)
        self.assertEqual(len(list(rqs[1:3])), 2)

        # Check that subscription can be counted
        self.assertEqual(len(rqs), 4)

        # Now the most up-to-dated subscription is the one with higher
        # `pk`.
        ids = [s.id for s in Subscription.objects.latests()]
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_str(self):
        """Test subscription representation"""
        self.assertEqual(str(Subscription.objects.get(pk=1)),
                         'Manga 1 (4 per day)')

    def test_issues_to_send(self):
        """Test the issues_to_send method"""
        # There are two users with daily limits of 4 and 8.  There are
        # six subscriptions, three for each user, and each with a
        # different state (active, paused, deleted).  Also there are
        # four mangas (in two sources), and each manga have five
        # issues, except Manga 1, that have six (issue 1 in a
        # different language)

        def _test_issues_to_send(subs, issues):
            # Check that is active
            self.assertFalse(subs.paused)
            self.assertFalse(subs.deleted)
            # ... no more than the limit for the subscription
            self.assertTrue(len(issues) <= subs.issues_per_day)
            # ... that all issues are from the same manga
            self.assertTrue(all(i.manga == subs.manga for i in issues))
            # ... no manga previously sent, in processing or failed
            self.assertFalse(
                any(i.history_set.filter(
                    subscription=subs,
                    status__in=(
                        History.PROCESSING,
                        History.SENT,
                        History.FAILED,
                    )).exists()
                    for i in issues))
            # ... all same language than the subscription
            self.assertTrue(all(i.language == subs.language for i in issues))

        for subs in Subscription.active.all():
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

        History.objects.all().delete()
        for subs in Subscription.active.all():
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

            # Add as sent one, so is recent
            subs.add_sent(issues[0])
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

    def test_add_sent(self):
        """Test that a subscription can register a sent."""
        History.objects.all().delete()
        subs = Subscription.active.all()[0]
        issue = subs.manga.issue_set.all()[0]
        subs.add_sent(issue)

        self.assertEqual(History.objects.count(), 1)
        h = History.objects.first()
        self.assertEqual(h.subscription, subs)
        self.assertEqual(h.issue, issue)
        self.assertEqual(h.status, History.SENT)


class HistoryTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_latests(self):
        """Test the recovery of updated history instances."""
        # There are three history items
        for hist in History.objects.order_by('pk'):
            hist.status = History.PROCESSING
            hist.save()

        self.assertEqual(History.objects.count(), 3)
        ids = [h.id for h in History.objects.latests()]
        self.assertEqual(ids, sorted(ids, reverse=True))

        self.assertFalse(History.objects.latests(status=History.SENT).exists())

    def test_modified_last_24hs(self):
        """Test the method to detect last modified instances."""
        user1 = UserProfile.objects.get(pk=1).user
        self.assertEqual(History.objects.modified_last_24hs(user1), 0)

        History.objects.all().delete()
        self.assertEqual(History.objects.modified_last_24hs(user1), 0)

        for i, subs in enumerate(Subscription.active.filter(user=user1)):
            issue = subs.manga.issue_set.all()[0]
            subs.add_sent(issue)
            self.assertEqual(History.objects.modified_last_24hs(user1), i+1)
            self.assertEqual(
                History.objects.modified_last_24hs(user1,
                                                   subscription=subs), 1)
            self.assertEqual(
                History.objects.modified_last_24hs(
                    user1,
                    subscription=subs,
                    status=History.SENT), 1)
            self.assertEqual(
                History.objects.modified_last_24hs(
                    user1,
                    subscription=subs,
                    status=History.FAILED), 0)

    def test_sent_last_24hs(self):
        """Test the method to detect last sent instances."""
        user1 = UserProfile.objects.get(pk=1).user
        self.assertEqual(History.objects.sent_last_24hs(user1), 0)

        History.objects.all().delete()
        self.assertEqual(History.objects.sent_last_24hs(user1), 0)

        for i, subs in enumerate(Subscription.active.filter(user=user1)):
            issue = subs.manga.issue_set.all()[0]
            subs.add_sent(issue)
            self.assertEqual(History.objects.sent_last_24hs(user1), i+1)
            self.assertEqual(
                History.objects.sent_last_24hs(user1, subscription=subs), 1)

    def test_status(self):
        """Test recovery lasts history instances with some status."""
        user1 = UserProfile.objects.get(pk=1).user
        subs = Subscription.active.filter(user=user1).first()

        table = ((History.PENDING, 'pending', 'is_pending'),
                 (History.PROCESSING, 'processing', 'is_processing'),
                 (History.SENT, 'sent', 'is_sent'),
                 (History.FAILED, 'failed', 'is_failed'))
        for status, latest, is_ in table:
            History.objects.all().delete()
            history = History.objects.create(
                issue=subs.manga.issue_set.first(),
                subscription=subs,
                status=status,
            )
            self.assertEqual(getattr(History.objects, latest)().count(), 1)
            self.assertTrue(getattr(history, is_)())

    def test_str(self):
        """Test history representation"""
        self.assertEqual(str(History.objects.get(pk=1)),
                         'manga 1 issue 1 (Sent)')
