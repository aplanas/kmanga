from django.test import TestCase

from core.models import AltName
from core.models import Genre
from core.models import Issue
from core.models import Manga
from core.models import Result
from core.models import Source
from core.models import SourceLanguage
from core.models import Subscription
from registration.models import UserProfile


class SourceTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test source representation."""
        self.assertEqual(str(Source.objects.get(pk=1)), 'Source 1')


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
        self.assertEqual(str(Genre.objects.get(pk=1)), 'source1_genre1')


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
        self.assertQuerysetEqual(q, ['<Manga: keyword>'])
        m.name = old_value
        m.save()
        Manga.objects.refresh()
        self.assertQuerysetEqual(Manga.objects.search('keyword'), [])

        # Search for specific keyword in alt_name
        q = Manga.objects.search('One')
        self.assertQuerysetEqual(q, ['<Manga: Manga 1>'])

        q = Manga.objects.search('Two')
        self.assertQuerysetEqual(q, ['<Manga: Manga 2>'])

        # Search for specific keyword in description
        m = Manga.objects.get(name='Manga 3')
        old_value = m.description
        m.description += ' keyword'
        m.save()
        Manga.objects.refresh()
        q = Manga.objects.search('keyword')
        self.assertQuerysetEqual(q, ['<Manga: Manga 3>'])
        m.description = old_value
        m.save()
        Manga.objects.refresh()
        self.assertQuerysetEqual(Manga.objects.search('keyword'), [])

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
        self.assertQuerysetEqual(q, ['<Manga: keyword>', '<Manga: Manga 4>'])

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
        self.assertEqual(str(Manga.objects.get(pk=1)), 'Manga 1')

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
        self.assertEqual(str(AltName.objects.get(pk=1)), 'Manga One')


class IssueTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_str(self):
        """Test issue representation"""
        self.assertEqual(str(Issue.objects.get(pk=1)), 'manga 1 issue 1')

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

    def test_result(self):
        """Test the result of an issue."""
        # Read `test_is_sent` for a description of the fixture.
        user1 = UserProfile.objects.get(pk=1).user
        user2 = UserProfile.objects.get(pk=2).user

        issue_sent = Issue.objects.get(name='manga 1 issue 1')
        for issue in Issue.objects.all():
            if issue == issue_sent:
                self.assertEqual(len(issue.result(user1)), 1)
                self.assertEqual(len(issue.result(user2)), 1)
            else:
                self.assertEqual(len(issue.result(user1)), 0)
                self.assertEqual(len(issue.result(user2)), 0)


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

        for user_profile in UserProfile.objects.all():
            user = user_profile.user
            # Check that deleted subscriptions are not included
            rqs = Subscription.objects.latests(user)
            self.assertEqual(len(rqs), 2)

            # Check that subscription can be indexed
            self.assertEqual(len(list(rqs[1])), 1)
            self.assertEqual(len(list(rqs[0:2])), 2)
            self.assertEqual(len(list(rqs[0:3])), 2)

            # Now the most up-to-dated subscription is the one with
            # higher `pk`.
            ids = [s.id for s in Subscription.objects.latests(user)]
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
                any(i.result_set.filter(
                    subscription=subs,
                    status__in=(
                        Result.PROCESSING,
                        Result.SENT,
                        Result.FAILED,
                    )).exists()
                    for i in issues))
            # ... all same language than the subscription
            self.assertTrue(all(i.language == subs.language for i in issues))

        for subs in Subscription.actives.all():
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

        Result.objects.all().delete()
        for subs in Subscription.actives.all():
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

            # Add as sent one, so is recent
            subs.add_sent(issues[0])
            issues = subs.issues_to_send()
            _test_issues_to_send(subs, issues)

    def test_add_sent(self):
        """Test that a subscription can register a sent."""
        Result.objects.all().delete()
        subs = Subscription.actives.all()[0]
        issue = subs.manga.issue_set.all()[0]
        subs.add_sent(issue)

        self.assertEqual(Result.objects.count(), 1)
        r = Result.objects.first()
        self.assertEqual(r.subscription, subs)
        self.assertEqual(r.issue, issue)
        self.assertEqual(r.status, Result.SENT)


class ResultTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def test_latests(self):
        """Test the recovery of updated result instances."""
        # There are three result items
        for result in Result.objects.order_by('pk'):
            result.status = Result.PROCESSING
            result.save()

        self.assertEqual(Result.objects.count(), 3)
        ids = [r.id for r in Result.objects.latests()]
        self.assertEqual(ids, sorted(ids, reverse=True))

        self.assertFalse(Result.objects.latests(status=Result.SENT).exists())

    def test_processed_last_24hs(self):
        """Test the method to detect last processed issues."""
        user1 = UserProfile.objects.get(pk=1).user
        self.assertEqual(Result.objects.processed_last_24hs(user1), 0)

        Result.objects.all().delete()
        self.assertEqual(Result.objects.processed_last_24hs(user1), 0)

        for i, subs in enumerate(Subscription.actives.filter(user=user1)):
            issue = subs.manga.issue_set.all()[0]
            subs.add_sent(issue)
            self.assertEqual(Result.objects.processed_last_24hs(user1), i+1)
            self.assertEqual(
                Result.objects.processed_last_24hs(user1, subscription=subs),
                1)

    def test_status(self):
        """Test recovery latest results instances with some status."""
        user1 = UserProfile.objects.get(pk=1).user
        subs = Subscription.actives.filter(user=user1).first()

        table = ((Result.PENDING, 'pending', 'is_pending'),
                 (Result.PROCESSING, 'processing', 'is_processing'),
                 (Result.SENT, 'sent', 'is_sent'),
                 (Result.FAILED, 'failed', 'is_failed'))
        for status, latest, is_ in table:
            Result.objects.all().delete()
            result = Result.objects.create(
                issue=subs.manga.issue_set.first(),
                subscription=subs,
                status=status,
            )
            self.assertEqual(getattr(Result.objects, latest)().count(), 1)
            self.assertTrue(getattr(result, is_)())

    def test_str(self):
        """Test result representation"""
        self.assertEqual(str(Result.objects.get(pk=1)),
                         'manga 1 issue 1 (Sent)')
