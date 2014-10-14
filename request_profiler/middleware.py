# -*- coding: utf-8 -*-
import logging

from django.contrib.auth.models import AnonymousUser

from request_profiler.models import RuleSet, ProfilingRecord
from request_profiler.signals import request_profile_complete

logger = logging.getLogger(__name__)


class ProfilingMiddleware(object):
    """Middleware used to time request-response cycle.

    This middleware uses the `process_request` and `process_response`
    methods to both determine whether the request should be profiled
    at all, and then to extract various data for recording as part of
    the profile.

    The `process_request` method is used to start the profile timing; the
    `process_response` method is used to extract the relevant data fields,
    and to stop the profiler.

    """
    def match_rules(self, request, rules):
        """Return subset of a list of rules that match a request."""
        user = getattr(request, 'user', AnonymousUser())
        return [r for r in rules if r.match_uri(request.path) and r.match_user(user)]

    def process_request(self, request):
        """Start profiling."""
        request.profiler_record = ProfilingRecord().start()

    def process_view(self, request, view_func, view_args, view_kwargs):
        """Add view_func to the profiler info."""
        request.profiler_record.view_func_name = view_func.__name__

    def process_response(self, request, response):
        """Add response information and save the profiler record.

        By the time we get here, we've run all the middleware, the view_func
        has been called, and we've rendered the templates.

        This is the last chance to override the profiler and halt the saving
        of the profiler record instance. This is done by sending out a signal
        and aborting the save if any listeners respond False.

        """
        assert getattr(request, 'profiler_record', None) is not None, (
            u"Request has no profiler_record attached."
        )
        # see if we have any matching rules
        matching_rules = self.match_rules(request, RuleSet.objects.live_rules())

        # clean up after outselves
        if len(matching_rules) == 0:
            del request.profiler_record
            return response

        profiler = request.profiler_record
        profiler.set_request_properties(request)
        profiler.response_status_code = response.status_code
        # send signal so that receivers can intercept profiler
        signal_responses = request_profile_complete.send(
            sender=self.__class__,
            request=request,
            response=response,
            instance=profiler
        )
        # if any signal receivers have returned False, then do **not** save
        if all([s[1] for s in signal_responses]):
            profiler.stop().save()
            response['X-Profiler-Duration'] = profiler.duration or profiler.elapsed
            response['X-Profiler-Rules'] = ','.join(str(r.id) for r in matching_rules)
        else:
            del request.profiler_record

        return response
