# -*- coding: utf-8 -*-

from unittest import skipIf

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.contrib.auth.models import User, Group

from django_request_profiler.models import RuleSet, ProfilingRecord

from test_app import views as test_app_views


class RuleSetMatchTestCase(TestCase):

    """Test that RuleSets are matched correctly."""

    def setUp(self):
        self.test_response_dest = reverse('test_response')
        self.test_view_dest = reverse('test_view')
        self.test_404_dest = reverse('test_404')

        self.all_test_dests = [
            self.test_response_dest,
            self.test_view_dest,
            self.test_404_dest
        ]

        # should be nothing to begin with
        self.assertEqual(RuleSet.objects.count(), 0)
        self.assertEqual(ProfilingRecord.objects.count(), 0)

    def _make_all_requests(self):
        for dest in self.all_test_dests:
            self.client.get(dest)

    def test_does_nothing_by_default(self):
        self._make_all_requests()
        
        # there still should be nothing
        self.assertEqual(RuleSet.objects.count(), 0)
        self.assertEqual(ProfilingRecord.objects.count(), 0)

    def test_match_with_catch_all(self):
        catch_all_ruleset = RuleSet(catch_all=True)
        catch_all_ruleset.save()

        # every request should result in a profiler record
        self._make_all_requests()
        self.assertEqual(
            ProfilingRecord.objects.count(),
            len(self.all_test_dests)
        )

    def test_match_uri_regex(self):
        # create a ruleset that matches a single uri (exactly)
        uri_regex_ruleset = RuleSet(uri_regex=self.test_response_dest)
        uri_regex_ruleset.save()

        # request all uris
        self._make_all_requests()

        # only one should match
        record = ProfilingRecord.objects.get()
        self.assertEqual(record.ruleset, uri_regex_ruleset)

    def test_match_user_id(self):
        # create user
        user = User.objects.create_user(
            username="username",
            password="password"
        )

        # create ruleset that matches user id
        user_id_ruleset = RuleSet(user_id=user.id)
        user_id_ruleset.save()

        # get with anon user
        self.client.get(self.test_response_dest)

        # get as logged in user
        self.client.login(username=user.username, password="password")
        self.client.get(self.test_response_dest)

        # only one should match
        record = ProfilingRecord.objects.get()
        self.assertEqual(record.ruleset, user_id_ruleset)

    def test_match_user_group(self):
        # create user in group
        group = Group(name="group")
        group.save()
        user_in_group = User.objects.create_user(
            username="user_in_group",
            password="password"
        )
        user_in_group.groups.add(group)

        # create user not in group
        user_not_in_group = User.objects.create_user(
            username="user_not_in_group",
            password="password"
        )

        # create ruleset that matches group name
        user_group_name_ruleset = RuleSet(user_group_name="group")
        user_group_name_ruleset.save()

        # get with anon user
        self.client.get(self.test_response_dest)

        # get as logged in user
        self.client.login(username=user_not_in_group.username, password="password")
        self.client.get(self.test_response_dest)

        # get as logged in user in group
        self.client.login(username=user_in_group.username, password="password")
        self.client.get(self.test_response_dest)

        # only one should match
        record = ProfilingRecord.objects.get()
        self.assertEqual(record.ruleset, user_group_name_ruleset)

    def test_match_with_always_true_user_function(self):
        # create ruleset that matches user function
        user_function_rule_set = RuleSet(
            user_function_name="test_app.functions.true"
        )
        user_function_rule_set.save()

        # every request should result in a profiler record
        self._make_all_requests()
        self.assertEqual(
            ProfilingRecord.objects.count(),
            len(self.all_test_dests)
        )

    def test_match_with_is_anonymous_user_function(self):
        # create ruleset that matches user function
        user_function_rule_set = RuleSet(
            user_function_name="test_app.functions.is_anonymous"
        )
        user_function_rule_set.save()

        # get with anon user
        self.client.get(self.test_response_dest)

        # get as logged in user
        user = User.objects.create_user(
            username="username",
            password="password"
        )
        self.client.login(username=user.username, password="password")
        self.client.get(self.test_response_dest)

        # only one should match
        record = ProfilingRecord.objects.get()
        self.assertEqual(record.ruleset, user_function_rule_set)

    def test_enabled_by_default(self):
        ruleset = RuleSet()
        self.assertTrue(ruleset.enabled)

    def test_disabled_ruleset(self):
        # create *disabled* catch-all RuleSet
        RuleSet(catch_all=True, enabled=False).save()

        # request test dest
        self.client.get(self.test_response_dest)

        # there should be no record
        self.assertEqual(ProfilingRecord.objects.count(), 0)

    def test_only_one_ruleset_matches(self):
        # create *two* catch-all RuleSets
        RuleSet(catch_all=True).save()
        RuleSet(catch_all=True).save()

        # request test dest
        self.client.get(self.test_response_dest)

        # there should be only one record
        self.assertEqual(ProfilingRecord.objects.count(), 1)


class ProfilingRecordTestCase(TestCase):

    """Test that records are written correctly."""

    def setUp(self):
        self.test_response_dest = reverse('test_response')
        self.test_view_dest = reverse('test_view')
        self.test_404_dest = reverse('test_404')
        self.catch_all_ruleset = RuleSet(catch_all=True)
        self.catch_all_ruleset.save()
        self.test_user = User.objects.create_user(
            username="username",
            password="password"
        )

    def _most_recent_record(self):
        return ProfilingRecord.objects.order_by('-id').first()

    def test_timestamps_are_recorded(self):
        self.client.get(self.test_response_dest)
        record = self._most_recent_record()
        self.assertTrue(record.start_ts < record.end_ts)
        self.assertTrue(record.duration > 0)

    def test_method_is_recorded(self):
        # GET
        self.client.get(self.test_response_dest)
        self.assertEqual(
            self._most_recent_record().method,
            'GET'
        )

        # POST
        self.client.post(self.test_response_dest)
        self.assertEqual(
            self._most_recent_record().method,
            'POST'
        )

    def test_uri_is_recorded(self):
        self.client.get(self.test_response_dest)
        self.assertTrue(
            self._most_recent_record().uri.endswith(
                self.test_response_dest
            )
        )

    def test_remote_addr_is_recorded(self):
        self.client.get(self.test_response_dest)
        self.assertIsNotNone(
            self._most_recent_record().remote_addr
        )

    def test_http_user_agent_is_recorded(self):
        test_user_agent = "test-user-agent"
        self.client.get(
            self.test_response_dest,
            HTTP_USER_AGENT=test_user_agent
        )
        self.assertEqual(
            self._most_recent_record().http_user_agent,
            test_user_agent
        )

    def test_session_key_is_recorded(self):
        # test without session
        self.client.get(self.test_response_dest)
        self.assertIsNone(
            self._most_recent_record().session_key
        )

        # test with session (login as user)
        self.client.login(username="username", password="password")
        self.client.get(self.test_response_dest)
        self.assertIsNotNone(
            self._most_recent_record().session_key
        )

    def test_user_id_is_recorded(self):
        # test without user (anonymous)
        self.client.get(self.test_response_dest)
        self.assertIsNone(
            self._most_recent_record().user_id
        )

        # test with user
        self.client.login(username="username", password="password")
        self.client.get(self.test_response_dest)
        self.assertEqual(
            self._most_recent_record().user_id,
            self.test_user.id
        )

    def test_view_func_name(self):
        self.client.get(self.test_response_dest)
        self.assertEqual(
            ProfilingRecord.objects.get().view_func_name,
            test_app_views.test_response.__name__
        )

    def test_response_status_code(self):
        # test HTTP 200
        self.client.get(self.test_response_dest)
        self.assertEqual(
            self._most_recent_record().response_status_code,
            200
        )

        # test HTTP 404
        self.client.get(self.test_404_dest)
        self.assertEqual(
            self._most_recent_record().response_status_code,
            404
        )

    @skipIf(True, "Skipping until implemented")
    def test_template_render_count(self):
        # test template-less
        self.client.get(self.test_response_dest)
        self.assertEqual(
            self._most_recent_record().template_render_count,
            0
        )

        # test with single template
        self.client.get(self.test_view_dest)
        self.assertEqual(
            self._most_recent_record().template_render_count,
            1
        )


class HTTPHeadersTestCase(TestCase):

    """Test that headers are set as desired."""

    def setUp(self):
        self.test_response_dest = reverse('test_response')
        self.catch_all_ruleset = RuleSet(catch_all=True)

    def test_duration_header_is_set(self):
        resp = self.client.get(self.test_response_dest)
        duration_header_value = resp.get('X-Request-Duration')
        self.assertIsNotNone(duration_header_value)
        self.assertTrue(float(duration_header_value) > 0)
