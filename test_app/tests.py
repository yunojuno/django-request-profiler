# -*- coding: utf-8 -*-
from django.core.urlresolvers import reverse
from django.test import TestCase

from request_profiler import settings
from request_profiler.models import RuleSet, ProfilingRecord


class ViewTests(TestCase):

    def setUp(self):
        # set up one, catch-all rule.
        self.rule = RuleSet(enabled=True)
        self.rule.save()

    def test_rules_match_response(self):
        url = reverse('test_response')
        response = self.client.get(url)
        self.assertTrue(response.has_header('X-Profiler-Duration'))
        record = ProfilingRecord.objects.get()
        self.assertIsNone(record.user)
        # session is save even if user is Anonymous
        self.assertNotEqual(record.session_key, '')
        self.assertEqual(record.http_user_agent, "")
        self.assertEqual(record.http_referer, u'')
        self.assertEqual(record.http_method, 'GET')
        self.assertEqual(record.view_func_name, 'test_response')
        self.assertEqual(str(record.duration), response['X-Profiler-Duration'])
        self.assertEqual(record.response_status_code, 200)

    def test_rules_match_view(self):
        url = reverse('test_view')
        response = self.client.get(url)
        self.assertTrue(response.has_header('X-Profiler-Duration'))
        record = ProfilingRecord.objects.get()
        self.assertIsNone(record.user)
        self.assertNotEqual(record.session_key, '')
        self.assertEqual(record.http_user_agent, "")
        self.assertEqual(record.http_referer, u'')
        self.assertEqual(record.http_method, 'GET')
        self.assertEqual(record.view_func_name, 'test_view')
        self.assertEqual(str(record.duration), response['X-Profiler-Duration'])
        self.assertEqual(record.response_status_code, 200)

    def test_rules_match_view_no_session(self):
        url = reverse('test_view')
        settings.STORE_ANONYMOUS_SESSIONS = False
        response = self.client.get(url)
        self.assertTrue(response.has_header('X-Profiler-Duration'))
        record = ProfilingRecord.objects.get()
        self.assertIsNone(record.user)
        self.assertEqual(record.session_key, '')

    def test_no_rules_match(self):
        self.rule.delete()
        url = reverse('test_response')
        response = self.client.get(url)
        self.assertFalse(response.has_header('X-Profiler-Duration'))
        self.assertFalse(ProfilingRecord.objects.exists())

    def test_404(self):
        # Validate that the profiler handles an error page
        url = reverse('test_404')
        response = self.client.get(url)
        self.assertTrue(response.has_header('X-Profiler-Duration'))
        self.assertEqual(ProfilingRecord.objects.get().response_status_code, 404)
