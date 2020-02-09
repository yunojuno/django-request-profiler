import datetime

from django.apps import apps
from django.contrib.auth.models import AnonymousUser, Group, User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.migrations.autodetector import MigrationAutodetector
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.state import ProjectState
from django.test import RequestFactory, TestCase
from request_profiler import settings
from request_profiler.middleware import ProfilingMiddleware, request_profile_complete
from request_profiler.models import ProfilingRecord, RuleSet, RuleSetQuerySet

from .models import CustomUser
from .utils import skipIfCustomUser, skipIfDefaultUser


def dummy_view_func(request, **kwargs):
    """Fake function to pass into the process_view method."""
    pass


class DummyView(object):
    """Fake callable object to pass into the process_view method."""

    def __call__(self, request, **kwargs):
        pass


class MockSession:
    def __init__(self, session_key):
        self.session_key = session_key


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code
        self.content = "Hello, World!"
        self.values = {}

    def __getitem__(self, key):
        return self.values[key]

    def __setitem__(self, key, value):
        self.values[key] = value


@skipIfCustomUser
class ProfilingMiddlewareDefaultUserTests(TestCase):
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

        request = self.factory.get("/")
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
        request = self.factory.get("/")
        ProfilingMiddleware().process_request(request)
        # this implicitly checks that the profile is attached,
        # and that start() has been called.
        self.assertIsNotNone(request.profiler.elapsed)

    def test_process_view(self):
        request = self.factory.get("/")
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, dummy_view_func, [], {})
        self.assertEqual(request.profiler.view_func_name, "dummy_view_func")

    def test_process_view__as_callable_object(self):
        request = self.factory.get("/")
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, DummyView(), [], {})
        self.assertEqual(request.profiler.view_func_name, "DummyView")

    def test_process_response(self):

        request = self.factory.get("/")
        middleware = ProfilingMiddleware()
        with self.assertRaises(ValueError):
            middleware.process_response(request, None)

        # try no matching rules
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, "profiler"))

        # try matching a rule, and checking response values
        r1 = RuleSet()
        r1.save()
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(response)
        self.assertTrue(request.profiler.response_status_code, response.status_code)
        self.assertTrue(response["X-Profiler-Duration"], request.profiler.duration)

    def test_process_response_signal_cancellation(self):

        request = self.factory.get("/")
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()

        # try matching a rule, anc checking response values
        r1 = RuleSet()
        r1.save()

        self.signal_received = False

        def on_request_profile_complete(sender, **kwargs):
            self.signal_received = True
            kwargs.get("instance").cancel()

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
        request = self.factory.get("/")
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
        self.assertFalse(hasattr(request, "profiler"))
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: True


@skipIfDefaultUser
class ProfilingMiddlewareCustomUserTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.anon = AnonymousUser()
        self.bob = CustomUser.objects.create_user(
            mobile_number="+886-999888777", password="pass11"
        )
        self.god = CustomUser.objects.create_superuser(
            mobile_number="+886-999888000", password="pass11"
        )
        self.test_group = Group(name="test")
        self.test_group.save()
        # remove any existing external signal listeners
        request_profile_complete.receivers = []

    def test_match_rules(self):
        # rule1 - to match all users
        r1 = RuleSet()
        self.assertTrue(r1.match_user(self.anon))

        request = self.factory.get("/")
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
        request = self.factory.get("/")
        ProfilingMiddleware().process_request(request)
        # this implicitly checks that the profile is attached,
        # and that start() has been called.
        self.assertIsNotNone(request.profiler.elapsed)

    def test_process_view(self):
        request = self.factory.get("/")
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, dummy_view_func, [], {})
        self.assertEqual(request.profiler.view_func_name, "dummy_view_func")

    def test_process_view__as_callable_object(self):
        request = self.factory.get("/")
        request.profiler = ProfilingRecord()
        ProfilingMiddleware().process_view(request, DummyView(), [], {})
        self.assertEqual(request.profiler.view_func_name, "DummyView")

    def test_process_response(self):

        request = self.factory.get("/")
        middleware = ProfilingMiddleware()
        with self.assertRaises(AssertionError):
            middleware.process_response(request, None)

        # try no matching rules
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, "profiler"))

        # try matching a rule, and checking response values
        r1 = RuleSet()
        r1.save()
        request.profiler = ProfilingRecord().start()
        response = middleware.process_response(request, MockResponse(200))
        self.assertIsNotNone(response)
        self.assertTrue(request.profiler.response_status_code, response.status_code)
        self.assertTrue(response["X-Profiler-Duration"], request.profiler.duration)

    def test_process_response_signal_cancellation(self):

        request = self.factory.get("/")
        request.profiler = ProfilingRecord().start()
        middleware = ProfilingMiddleware()

        # try matching a rule, anc checking response values
        r1 = RuleSet()
        r1.save()

        self.signal_received = False

        def on_request_profile_complete(sender, **kwargs):
            self.signal_received = True
            kwargs.get("instance").cancel()

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
        request = self.factory.get("/")
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
        self.assertFalse(hasattr(request, "profiler"))
        settings.GLOBAL_EXCLUDE_FUNC = lambda x: True


class MigrationsTests(TestCase):
    def test_for_missing_migrations(self):
        """Checks if there're models changes which aren't reflected in migrations."""
        migrations_loader = MigrationExecutor(connection).loader
        migrations_detector = MigrationAutodetector(
            from_state=migrations_loader.project_state(),
            to_state=ProjectState.from_apps(apps),
        )
        if migrations_detector.changes(graph=migrations_loader.graph):
            self.fail(
                "Your models have changes that are not yet reflected "
                "in a migration. You should add them now."
            )
