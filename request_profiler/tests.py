# -*- coding: utf-8 -*-
# tests for the request_profiler app
import datetime

from django.contrib.auth.models import User, AnonymousUser, Group
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import TestCase, RequestFactory
from django.contrib.auth.tests.utils import skipIfCustomUser

from . import settings
from .middleware import ProfilingMiddleware
from .models import RuleSet, RuleSetManager, ProfilingRecord
from .signals import request_profile_complete

from test_app.models import CustomUser
from test_app.utils import skipIfDefaultUser


def dummy_view_func(request, **kwargs):
    "Fake function to pass into the process_view method."
    pass


class MockSession():
    def __init__(self, session_key):
        self.session_key = session_key


class MockResponse():
    def __init__(self, status_code):
        self.status_code = status_code
        self.content = "Hello, World!"
        self.values = {}

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value


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

    def test_live_rules_with_caching(self):

        settings.RULESET_CACHE_TIMEOUT = 10
        self.assertIsNone(cache.get(settings.RULESET_CACHE_KEY))
        # save a couple of rules
        RuleSet(uri_regex="", enabled=True).save()
        RuleSet(uri_regex="", enabled=True).save()
        self.assertEqual(RuleSet.objects.live_rules().count(), 2)
        self.assertIsNotNone(cache.get(settings.RULESET_CACHE_KEY))
        # cache is full, delete the underlying records and retrieve
        RuleSet.objects.all().delete()
        # we're going to the cache, so even so DB is empty, we get two back
        self.assertEqual(RuleSet.objects.live_rules().count(), 2)
        # clear out cache and confirm we're now going direct to DB
        cache.clear()
        self.assertEqual(RuleSet.objects.live_rules().count(), 0)


class RuleSetModelTests(TestCase):
    """Basic model properrty and method tests."""

    def setUp(self):
        pass

    def test_default_properties(self):
        ruleset = RuleSet()
        props = [
            ('enabled', True),
            ('uri_regex', ""),
            ('user_filter_type', 0),
            ('user_group_filter', ""),
        ]
        for p in props:
            self.assertEqual(getattr(ruleset, p[0]), p[1])
        self.assertIsInstance(RuleSet.objects, RuleSetManager)

    def test_has_group_filter(self):
        ruleset = RuleSet()
        filters = (
            ("", False),
            (" ", False),
            ("test", True),
        )
        for f in filters:
            ruleset.user_group_filter = f[0]
            self.assertEqual(ruleset.has_group_filter, f[1])

    def test_clean(self):
        ruleset = RuleSet(user_group_filter="test")
        for f in (RuleSet.USER_FILTER_ALL, RuleSet.USER_FILTER_AUTH):
            ruleset.user_filter_type = f
            self.assertRaises(ValidationError, ruleset.clean)
        ruleset.user_filter_type = RuleSet.USER_FILTER_GROUP
        ruleset.clean()
        # now try the opposite - user_filter_type set, but no group set
        ruleset.user_group_filter = ""
        self.assertRaises(ValidationError, ruleset.clean)

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

    @skipIfCustomUser
    def test_match_user(self):
        ruleset = RuleSet("")
        self.assertFalse(ruleset.has_group_filter)
        self.assertEqual(ruleset.user_filter_type, RuleSet.USER_FILTER_ALL)

        # start with no user / anonymous
        self.assertTrue(ruleset.match_user(None))
        self.assertTrue(ruleset.match_user(AnonymousUser()))

        # now exclude anonymous
        ruleset.user_filter_type = RuleSet.USER_FILTER_AUTH
        self.assertFalse(ruleset.match_user(None))
        self.assertFalse(ruleset.match_user(AnonymousUser()))

        # create a real user, but still no group filter
        bob = User.objects.create_user("Bob")
        self.assertFalse(bob.groups.exists())
        self.assertFalse(bob.is_staff)
        self.assertTrue(bob.is_authenticated())
        self.assertTrue(ruleset.match_user(bob))

        # now create the filter, and check bob no longer matches
        ruleset.user_filter_type = RuleSet.USER_FILTER_GROUP
        ruleset.user_group_filter = "test"
        test_group = Group(name="test")
        test_group.save()
        self.assertFalse(ruleset.match_user(bob))

        # add bob to the group, and check he now matches
        bob.groups.add(test_group)
        self.assertTrue(bob.groups.filter(name="test").exists())
        self.assertTrue(ruleset.match_user(bob))

        # test setting an invalid value
        ruleset.user_filter_type = -1
        self.assertFalse(ruleset.match_user(bob))
        bob.is_staff = False
        self.assertFalse(ruleset.match_user(bob))
        self.assertFalse(ruleset.match_user(None))
        self.assertFalse(ruleset.match_user(AnonymousUser()))

    @skipIfDefaultUser
    def test_match_custom_user(self):
        ruleset = RuleSet("")
        self.assertFalse(ruleset.has_group_filter)
        self.assertEqual(ruleset.user_filter_type, RuleSet.USER_FILTER_ALL)

        # start with no user / anonymous
        self.assertTrue(ruleset.match_user(None))
        self.assertTrue(ruleset.match_user(AnonymousUser()))

        # now exclude anonymous
        ruleset.user_filter_type = RuleSet.USER_FILTER_AUTH
        self.assertFalse(ruleset.match_user(None))
        self.assertFalse(ruleset.match_user(AnonymousUser()))

        # create a real user, but still no group filter
        bob = CustomUser.objects.create_user(
            mobile_number="+886-999888777",
            password="pass11"
        )
        self.assertFalse(bob.groups.exists())
        self.assertFalse(bob.is_staff)
        self.assertTrue(bob.is_authenticated())
        self.assertTrue(ruleset.match_user(bob))

        # now create the filter, and check bob no longer matches
        ruleset.user_filter_type = RuleSet.USER_FILTER_GROUP
        ruleset.user_group_filter = "test"
        test_group = Group(name="test")
        test_group.save()
        self.assertFalse(ruleset.match_user(bob))

        # add bob to the group, and check he now matches
        bob.groups.add(test_group)
        self.assertTrue(bob.groups.filter(name="test").exists())
        self.assertTrue(ruleset.match_user(bob))

        # test setting an invalid value
        ruleset.user_filter_type = -1
        self.assertFalse(ruleset.match_user(bob))
        bob.is_staff = False
        self.assertFalse(ruleset.match_user(bob))
        self.assertFalse(ruleset.match_user(None))
        self.assertFalse(ruleset.match_user(AnonymousUser()))


class ProfilingRecordModelTests(TestCase):
    """Basic model properrty and method tests."""

    def setUp(self):
        cache.clear()

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
            ('http_referer', ""),
            ('view_func_name', ""),
            ('response_status_code', None),
        ]
        for p in props:
            self.assertEqual(getattr(profile, p[0]), p[1])
        self.assertIsNotNone(unicode(profile))
        self.assertIsNotNone(str(profile))
        self.assertIsNotNone(repr(profile))

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

    def test_cancel(self):
        profile = ProfilingRecord().cancel()
        self.assertIsNone(profile.start_ts)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)
        self.assertTrue(profile.is_cancelled)
        # same thing, but this time post-start
        profile = ProfilingRecord().start().cancel()
        self.assertIsNone(profile.start_ts)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)
        self.assertTrue(profile.is_cancelled)

    def test_capture(self):
        # repeat, but this time cancel before capture
        profile = ProfilingRecord()
        response = MockResponse(200)
        profile.start().set_response(response).capture()
        self.assertIsNotNone(profile.start_ts)
        self.assertIsNotNone(profile.end_ts)
        self.assertIsNotNone(profile.duration)
        self.assertIsNotNone(profile.id)
        self.assertEqual(response['X-Profiler-Duration'], profile.duration)

        profile = ProfilingRecord().cancel().capture()
        self.assertIsNone(profile.start_ts)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)
        self.assertIsNone(profile.id)

    def test_elapsed(self):
        profile = ProfilingRecord()
        with self.assertRaises(AssertionError):
            profile.elapsed
        profile.start()
        self.assertIsNotNone(profile.elapsed)
        self.assertIsNone(profile.end_ts)
        self.assertIsNone(profile.duration)

    @skipIfCustomUser
    def test_set_request(self):

        factory = RequestFactory()
        request = factory.get("/test")
        request.META['HTTP_USER_AGENT'] = "test-browser"
        request.META['HTTP_REFERER'] = "google.com"
        profile = ProfilingRecord()

        profile.set_request(request)
        self.assertEqual(profile.request, request)
        self.assertEqual(profile.http_method, request.method)
        self.assertEqual(profile.request_uri, request.path)
        # for some reason user-agent is a tuple - need to read specs!
        self.assertEqual(profile.http_user_agent, "test-browser")
        self.assertEqual(profile.http_referer, "google.com")
        self.assertEqual(profile.session_key, "")
        self.assertEqual(profile.user, None)

        # test that we can set the session
        request.session = MockSession("test-session-key")
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.session_key, "test-session-key")

        # test that we can set the user
        request.user = User.objects.create_user("bob")
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.user, request.user)

        # but we do not save anonymous users
        request.user = AnonymousUser()
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.user, None)

    @skipIfDefaultUser
    def test_set_request_with_custom_user(self):

        factory = RequestFactory()
        request = factory.get("/test")
        request.META['HTTP_USER_AGENT'] = "test-browser"
        request.META['HTTP_REFERER'] = "google.com"
        profile = ProfilingRecord()

        profile.set_request(request)
        self.assertEqual(profile.request, request)
        self.assertEqual(profile.http_method, request.method)
        self.assertEqual(profile.request_uri, request.path)
        # for some reason user-agent is a tuple - need to read specs!
        self.assertEqual(profile.http_user_agent, "test-browser")
        self.assertEqual(profile.http_referer, "google.com")
        self.assertEqual(profile.session_key, "")
        self.assertEqual(profile.user, None)

        # test that we can set the session
        request.session = MockSession("test-session-key")
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.session_key, "test-session-key")

        # test that we can set the custom user
        request.user = CustomUser.objects.create_user(
            mobile_number="+886-999888777",
            password="pass11"
        )
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.user, request.user)

        # but we do not save anonymous users
        request.user = AnonymousUser()
        profile = ProfilingRecord().set_request(request)
        self.assertEqual(profile.user, None)

    def test_set_response(self):
        response = MockResponse(200)
        profiler = ProfilingRecord().start().set_response(response)
        self.assertEqual(profiler.response, response)
        self.assertEqual(profiler.response_status_code, 200)
        self.assertEqual(profiler.response_content_length, 13)


@skipIfCustomUser
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
        r1 = RuleSet()
        self.assertTrue(r1.match_user(self.anon))

        request = self.factory.get('/')
        request.user = self.anon
        self.assertTrue(r1.match_uri, request.path)

        middleware = ProfilingMiddleware()
        self.assertEqual(middleware.match_rules(request, [r1]), [r1])

        # now change the uri_regex so we no longer get a match
        r1.uri_regex = "^xyz$"
        self.assertEqual(middleware.match_rules(request, [r1]), [])

        # now change the user_groups so we no longer get a match
        request.user = self.bob
        r1.uri_regex = ""
        r1.user_filter_type = RuleSet.USER_FILTER_GROUP
        r1.user_group_filter = "test"
        self.assertEqual(middleware.match_rules(request, [r1]), [])
        # add bob to the group
        self.bob.groups.add(self.test_group)
        self.assertEqual(middleware.match_rules(request, [r1]), [r1])

    def test_process_request(self):
        request = self.factory.get('/')
        ProfilingMiddleware().process_request(request)
        # this implicitly checks that the profile is attached,
        # and that start() has been called.
        self.assertIsNotNone(request.profiler.elapsed)

    def test_process_view(self):
        request = self.factory.get('/')
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, dummy_view_func, [], {})
        self.assertEqual(request.profiler.view_func_name, "dummy_view_func")

    def test_process_response(self):

        request = self.factory.get('/')
        middleware = ProfilingMiddleware()
        with self.assertRaises(AssertionError):
            middleware.process_response(request, None)

        # try no matching rules
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'profiler'))

        # try matching a rule, and checking response values
        r1 = RuleSet()
        r1.save()
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(response)
        self.assertTrue(request.profiler.response_status_code, response.status_code)
        self.assertTrue(response['X-Profiler-Duration'], request.profiler.duration)

    def test_process_response_signal_cancellation(self):

        request = self.factory.get('/')
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()

        # try matching a rule, anc checking response values
        r1 = RuleSet()
        r1.save()

        self.signal_received = False

        def on_request_profile_complete(sender, **kwargs):
            self.signal_received = True
            kwargs.get('instance').cancel()

        request_profile_complete.connect(on_request_profile_complete)
        middleware.process_response(request, MockResponse(200))
        # because we returned False from the signal receiver,
        # we should have stopped profiling.
        self.assertTrue(self.signal_received)
        # because we called cancel(), the record is not saved.
        self.assertIsNone(request.profiler.id)

    def test_global_exclude_function(self):

        # set the func to ignore everything
        RuleSet().save()
        request = self.factory.get('/')
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()
        # process normally, record is saved.
        middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(request.profiler.id)

        # NB for some reason (prb. due to imports, the standard
        # 'override_settings' decorator doesn't work here.)
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: False
        request.profiler = ProfilingRecord().start()
        # process now, and profiler is cancelled
        middleware.process_response(request, MockResponse(200))
        self.assertFalse(hasattr(request, 'profiler'))
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: True


@skipIfDefaultUser
class ProfilingMiddlewareTests(TestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.anon = AnonymousUser()
        self.bob = CustomUser.objects.create_user(
                mobile_number="+886-999888777",
                password="pass11"
        )
        self.god = CustomUser.objects.create_superuser(
                mobile_number="+886-999888000",
                password="pass11"
        )
        self.test_group = Group(name="test")
        self.test_group.save()
        # remove any existing external signal listeners
        request_profile_complete.receivers = []

    def test_match_rules(self):
        # rule1 - to match all users
        r1 = RuleSet()
        self.assertTrue(r1.match_user(self.anon))

        request = self.factory.get('/')
        request.user = self.anon
        self.assertTrue(r1.match_uri, request.path)

        middleware = ProfilingMiddleware()
        self.assertEqual(middleware.match_rules(request, [r1]), [r1])

        # now change the uri_regex so we no longer get a match
        r1.uri_regex = "^xyz$"
        self.assertEqual(middleware.match_rules(request, [r1]), [])

        # now change the user_groups so we no longer get a match
        request.user = self.bob
        r1.uri_regex = ""
        r1.user_filter_type = RuleSet.USER_FILTER_GROUP
        r1.user_group_filter = "test"
        self.assertEqual(middleware.match_rules(request, [r1]), [])
        # add bob to the group
        self.bob.groups.add(self.test_group)
        self.assertEqual(middleware.match_rules(request, [r1]), [r1])

    def test_process_request(self):
        request = self.factory.get('/')
        ProfilingMiddleware().process_request(request)
        # this implicitly checks that the profile is attached,
        # and that start() has been called.
        self.assertIsNotNone(request.profiler.elapsed)

    def test_process_view(self):
        request = self.factory.get('/')
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, dummy_view_func, [], {})
        self.assertEqual(request.profiler.view_func_name, "dummy_view_func")

    def test_process_response(self):

        request = self.factory.get('/')
        middleware = ProfilingMiddleware()
        with self.assertRaises(AssertionError):
            middleware.process_response(request, None)

        # try no matching rules
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, 'profiler'))

        # try matching a rule, and checking response values
        r1 = RuleSet()
        r1.save()
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(response)
        self.assertTrue(request.profiler.response_status_code, response.status_code)
        self.assertTrue(response['X-Profiler-Duration'], request.profiler.duration)

    def test_process_response_signal_cancellation(self):

        request = self.factory.get('/')
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()

        # try matching a rule, anc checking response values
        r1 = RuleSet()
        r1.save()

        self.signal_received = False

        def on_request_profile_complete(sender, **kwargs):
            self.signal_received = True
            kwargs.get('instance').cancel()

        request_profile_complete.connect(on_request_profile_complete)
        middleware.process_response(request, MockResponse(200))
        # because we returned False from the signal receiver,
        # we should have stopped profiling.
        self.assertTrue(self.signal_received)
        # because we called cancel(), the record is not saved.
        self.assertIsNone(request.profiler.id)

    def test_global_exclude_function(self):

        # set the func to ignore everything
        RuleSet().save()
        request = self.factory.get('/')
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()
        # process normally, record is saved.
        middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(request.profiler.id)

        # NB for some reason (prb. due to imports, the standard
        # 'override_settings' decorator doesn't work here.)
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: False
        request.profiler = ProfilingRecord().start()
        # process now, and profiler is cancelled
        middleware.process_response(request, MockResponse(200))
        self.assertFalse(hasattr(request, 'profiler'))
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: True
