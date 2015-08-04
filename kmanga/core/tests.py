from django.test import TestCase

from core.models import Issue
from core.models import Manga
from core.models import Subscription
from registration.models import UserProfile


class MangaTestCase(TestCase):
    fixtures = ['registration.json', 'core.json']

    def setUp(self):
        pass

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

    def test_latests(self):
        """Test the recovery of updated mangas."""
        # Random order where we expect the mangas
        names = ('Manga 2', 'Manga 4', 'Manga 1', 'Manga 3')
        for name in reversed(names):
            issue = Issue.objects.get(name='%s issue 1' % name.lower())
            issue.name += ' - %s' % name
            issue.save()

        for manga, name in zip(Manga.objects.latests(), names):
            self.assertEqual(manga.name, name)

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
