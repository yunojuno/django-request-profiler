from __future__ import annotations

import logging
from typing import Any, Callable

from django.contrib.auth.models import AnonymousUser
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from . import settings
from .models import BadProfilerError, ProfilingRecord, RuleSet
from .signals import request_profile_complete

logger = logging.getLogger(__name__)


class ProfilingMiddleware(MiddlewareMixin):
    """
    Middleware used to time request-response cycle.

    This middleware uses the `process_request` and `process_response`
    methods to both determine whether the request should be profiled
    at all, and then to extract various data for recording as part of
    the profile.

    The `process_request` method is used to start the profile timing; the
    `process_response` method is used to extract the relevant data fields,
    and to stop the profiler.

    """

    def match_rules(self, request: HttpRequest, rules: QuerySet) -> list[RuleSet]:
        """Return subset of a list of rules that match a request."""
        user = getattr(request, "user", AnonymousUser())
        return [
            r for r in rules if r.match_uri(request.path) and r.match_user(user)
        ]  # noqa

    def match_funcs(self, request: HttpRequest) -> bool:
        return any(f(request) for f in settings.CUSTOM_FUNCTIONS)

    def process_request(self, request: HttpRequest) -> None:
        """Start profiling."""
        # force the creation of a valid session by saving it.
        request.profiler = ProfilingRecord().start()
        if (
            hasattr(request, "session")
            and request.session.session_key is None
            and settings.STORE_ANONYMOUS_SESSIONS is True
        ):
            request.session.save()
        request.profiler.process_request(request)

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: Any,
        view_kwargs: Any,
    ) -> None:
        """Add view_func to the profiler info."""
        request.profiler.process_view(request, view_func)

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Add response information and save the profiler record.

        By the time we get here, we've run all the middleware, the view_func
        has been called, and we've rendered the templates.

        This is the last chance to override the profiler and halt the saving
        of the profiler record instance. This is done by sending out a signal
        and aborting the save if any listeners respond False.

        """
        try:
            profiler = request.profiler
        except AttributeError:
            raise BadProfilerError("Request has no profiler attached.")

        # call the global exclude first, as there's no point continuing if this
        # says no.
        if settings.GLOBAL_EXCLUDE_FUNC(request) is False:
            del request.profiler
            return response

        # see if we have any matching rules
        matches_rules = self.match_rules(request, RuleSet.objects.live_rules())
        matches_funcs = self.match_funcs(request)
        log_request = matches_rules or matches_funcs

        # clean up after ourselves
        if not log_request:
            logger.debug(
                "Deleting %r as request matches no live rules.",
                request.profiler,
            )
            del request.profiler
            return response

        # extract properties from response for storing later
        profiler.process_response(response)

        # send signal so that receivers can intercept profiler
        request_profile_complete.send(
            sender=self.__class__,
            request=request,
            response=response,
            instance=profiler,
        )
        # if any signal receivers have called cancel() on the profiler,
        # then we do not want to capture it.
        if profiler.is_running:
            profiler.capture()

        return response
