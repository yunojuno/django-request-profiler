# -*- coding: utf-8 -*-
# tests for the request_profiler app
import datetime

from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User, AnonymousUser, Group

from request_profiler.middleware import ProfilingMiddleware
from request_profiler.models import RuleSet, RuleSetManager, ProfilingRecord
from request_profiler.signals import request_profile_complete
from request_profiler import settings


def dummy_view_func(request, **kwargs):
    "Fake function to pass into the process_view method."
    pass


class MockSession():
    def __init__(self, session_key):
        self.session_key = session_key


class MockResponse():
    def __init__(self, status_code):
        self.status_code = status_code
        self.values = {}

    def __len__(self):
        return len(self.values)

    def __getitem__(self, key):
        # if key is of invalid type or value, the list values will raise the error
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value

    def __delitem__(self, key):
        del self.values[key]

    def __iter__(self):
        return iter(self.values)

    # def __reversed__(self):
    #     return FunctionalList(reversed(self.values))


class RuleSetManagerTests(TestCase):
    """Basic model manager method tests."""

    def setUp(self):
        pass

    def test_live_rules(self):

        r1 = RuleSet(uri_regex="", enabled=True)
        r1.save()
        self.assertEqual(RuleSet.objects.live_rules().count(), 1)

        r2 = RuleSet(uri_regex="", enabled=True)
        r2.save()
        self.assertEqual(RuleSet.objects.live_rules().count(), 2)

        r2.enabled = False
        r2.save()
        self.assertEqual(RuleSet.objects.live_rules().count(), 1)


class RuleSetModelTests(TestCase):
    """Basic model properrty and method tests."""

    def setUp(self):
        pass

    def test_default_properties(self):
        ruleset = RuleSet()
        props = [
            ('enabled', True),
            ('uri_regex', ""),
            ('user_group_filter', ""),
            ('include_anonymous', True),
        ]
        for p in props:
            self.assertEqual(getattr(ruleset, p[0]), p[1])
        self.assertIsInstance(RuleSet.objects, RuleSetManager)

    def test_has_group_filter(self):
        ruleset = RuleSet("")
        filters = (
            ("", False),
            (" ", False),
            ("test", True),
        )
        for f in filters:
            ruleset.user_group_filter = f[0]
            self.assertEqual(ruleset.has_group_filter, f[1])

    def test_match_uri(self):
        ruleset = RuleSet("")
        uri = "/test/"
        regexes = (
            ("", True),
            (" ", True),
            ("^/test", True),
            (".", True),
            ("/x", False)
        )

        for r in regexes:
            ruleset.uri_regex = r[0]
            self.assertEqual(ruleset.match_uri(uri), r[1])

    def test_match_user(self):
        ruleset = RuleSet("")
        self.assertFalse(ruleset.has_group_filter)
        self.assertTrue(ruleset.include_anonymous)

        # start with no user / anonymous
        self.assertTrue(ruleset.match_user(None))
        self.assertTrue(ruleset.match_user(AnonymousUser()))

        # now exclude anonymous
        ruleset.include_anonymous = False
        self.assertFalse(ruleset.match_user(None))
        self.assertFalse(ruleset.match_user(AnonymousUser()))

        # create a real user, but still no group filter
        bob = User.objects.create_user("Bob")
        self.assertFalse(bob.groups.exists())
        self.assertFalse(bob.is_staff)
        self.assertTrue(bob.is_authenticated())
        self.assertTrue(ruleset.match_user(bob))

        # now create the filter, and check bob no longer matches
        ruleset.user_group_filter = "test"
        test_group = Group(name="test")
        test_group.save()
        self.assertFalse(ruleset.match_user(bob))

        # add bob to the group, and check he now matches
        bob.groups.add(test_group)
        self.assertTrue(bob.groups.filter(name="test").exists())
        self.assertTrue(ruleset.match_user(bob))

        # now make him is_staff, and check that he's no longer allowed
        bob.is_staff = True
        self.assertTrue(settings.IGNORE_STAFF)
        self.assertFalse(ruleset.match_user(bob))

        # and finally, allow staff
        settings.IGNORE_STAFF = False
        self.assertTrue(ruleset.match_user(bob))


class ProfilingRecordModelTests(TestCase):
    """Basic model properrty and method tests."""

    def setUp(self):
        pass

    def test_default_properties(self):
        profile = ProfilingRecord()
        props = [
            ('user', None),
            ('session_key', ""),
            ('start_ts', None),
            ('end_ts', None),
            ('duration', None),
            ('http_method', ""),
            ('request_uri', ""),
            ('remote_addr', ""),
            ('http_user_agent', ""),
            ('view_func_name', ""),
            ('response_status_code', None),
        ]
        for p in props:
            self.assertEqual(getattr(profile, p[0]), p[1])

    def test_start(self):
        profile = ProfilingRecord().start()
        self.assertIsNotNone(profile.start_ts)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)
        # now check again to see that end and duration are cleared
        profile.end_ts = datetime.datetime.utcnow()
        profile.duration = 1
        profile.start()
        self.assertIsNotNone(profile.start_ts)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)

    def test_stop(self):
        profile = ProfilingRecord()
        self.assertRaises(AssertionError, profile.stop)
        profile.start().stop()
        self.assertIsNotNone(profile.start_ts)
        self.assertIsNotNone(profile.end_ts)
        self.assertIsNotNone(profile.duration)
        self.assertTrue(profile.duration > 0)

    def test_elapsed(self):
        profile = ProfilingRecord()
        with self.assertRaises(AssertionError):
            profile.elapsed
        profile.start()
        self.assertIsNotNone(profile.elapsed)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)

    def test_set_request_properties(self):

        factory = RequestFactory()
        request = factory.get("/test")
        request.META['HTTP_USER_AGENT'] = "test-browser"
        profile = ProfilingRecord()

        profile.set_request_properties(request)
        self.assertEqual(profile.http_method, request.method)
        self.assertEqual(profile.request_uri, request.path)
        # for some reason user-agent is a tuple - need to read specs!
        self.assertEqual(profile.http_user_agent, ("test-browser",))
        self.assertEqual(profile.session_key, "")
        self.assertEqual(profile.user, None)

        # test that we can set the session
        request.session = MockSession("test-session-key")
        profile = ProfilingRecord()
        profile.set_request_properties(request)
        self.assertEqual(profile.session_key, "test-session-key")

        # test that we can set the user
        request.user = User.objects.create_user("bob")
        profile = ProfilingRecord()
        profile.set_request_properties(request)
        self.assertEqual(profile.user, request.user)

        # but we do not save anonymous users
        request.user = AnonymousUser()
        profile = ProfilingRecord()
        profile.set_request_properties(request)
        self.assertEqual(profile.user, None)


class ProfilingMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.anon = AnonymousUser()
        self.bob = User.objects.create_user("bob")
        self.god = User.objects.create_superuser("god", "iamthelaw", "")
        self.test_group = Group(name="test")
        self.test_group.save()
        # remove any existing external signal listeners
        request_profile_complete.receivers = []

    def test_match_rules(self):
        # rule1 - to match all users
        r1 = RuleSet(enabled=True, include_anonymous=True)
        self.assertTrue(r1.match_user(self.anon))

        request = self.factory.get('/')
        request.user = self.anon
        self.assertTrue(r1.match_uri, request.path)

        profiler = ProfilingMiddleware()
        self.assertEqual(profiler.match_rules(request, [r1]), [r1])

        # now change the uri_regex so we no longer get a match
        r1.uri_regex = "^xyz$"
        self.assertEqual(profiler.match_rules(request, [r1]), [])

        # now change the user_groups so we no longer get a match
        request.user = self.bob
        r1.uri_regex = ""
        r1.user_group_filter = "test"
        self.assertEqual(profiler.match_rules(request, [r1]), [])
        # add bob to the group
        self.bob.groups.add(self.test_group)
        self.assertEqual(profiler.match_rules(request, [r1]), [r1])

    def test_process_request(self):
        request = self.factory.get('/')
        profiler = ProfilingMiddleware()
        profiler.process_request(request)
        # this implicitly checks that the profile is attached,
        # and that start() has been called.
        self.assertIsNotNone(request.profiler_record.elapsed)

    def test_process_view(self):
        request = self.factory.get('/')
        request.profiler_record = ProfilingRecord()
        profiler = ProfilingMiddleware()
        profiler.process_view(request, dummy_view_func, [], {})
        self.assertEqual(request.profiler_record.view_func_name, "dummy_view_func")

    def test_process_response(self):

        request = self.factory.get('/')
        profiler = ProfilingMiddleware()
        with self.assertRaises(AssertionError):
            profiler.process_response(request, None)

        # try no matching rules
        request.profiler_record = ProfilingRecord().start()
        response = profiler.process_response(request, MockResponse(200))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'profiler_record'))

        # try matching a rule, anc checking response values
        r1 = RuleSet(enabled=True, include_anonymous=True)
        r1.save()
        request.profiler_record = ProfilingRecord().start()
        response = profiler.process_response(request, MockResponse(200))
        self.assertTrue(request.profiler_record.response_status_code, response.status_code)
        self.assertTrue(response['X-Profiler-Duration'], request.profiler_record.duration)
        self.assertTrue(response['X-Profiler-Rules'], r1.id)

    def test_process_response_signal_cancellation(self):

        request = self.factory.get('/')
        request.profiler_record = ProfilingRecord().start()
        profiler = ProfilingMiddleware()

        # try matching a rule, anc checking response values
        r1 = RuleSet(enabled=True, include_anonymous=True)
        r1.save()

        self.signal_received = False

        def on_request_profile_complete(sender, **kwargs):
            self.signal_received = True
            return False

        request_profile_complete.connect(on_request_profile_complete)
        profiler.process_response(request, MockResponse(200))
        # because we returned False from the signal receiver,
        # we should have stopped profiling.
        self.assertTrue(self.signal_received)
        self.assertFalse(hasattr(request, 'profiler_record'))
