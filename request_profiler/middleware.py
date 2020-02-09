from __future__ import annotations

import logging
from typing import Any, Callable, List

from django.contrib.auth.models import AnonymousUser
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.utils.deprecation import MiddlewareMixin

from . import settings
from .models import ProfilingRecord, RuleSet
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

    def match_rules(self, request: HttpRequest, rules: QuerySet) -> List[RuleSet]:
        """Return subset of a list of rules that match a request."""
        user = getattr(request, "user", AnonymousUser())
        return [
            r for r in rules if r.match_uri(request.path) and r.match_user(user)
        ]  # noqa

    def process_request(self, request: HttpRequest) -> None:
        """Start profiling."""
        request.profiler = ProfilingRecord().start()

    def process_view(
        self,
        request: HttpRequest,
        view_func: Callable,
        view_args: Any,
        view_kwargs: Any,
    ) -> None:
        """Add view_func to the profiler info."""
        # force the creation of a valid session by saving it.
        if (
            hasattr(request, "session")
            and request.session.session_key is None
            and settings.STORE_ANONYMOUS_SESSIONS is True
        ):
            request.session.save()

        if hasattr(view_func, "__name__"):
            request.profiler.view_func_name = view_func.__name__
        else:
            request.profiler.view_func_name = view_func.__class__.__name__

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
        if not getattr(request, "profiler", None):
            raise ValueError("Request has no profiler attached.")

        # call the global exclude first, as there's no point continuing if this
        # says no.
        if settings.GLOBAL_EXCLUDE_FUNC(request) is False:
            del request.profiler
            return response

        # see if we have any matching rules
        rules = self.match_rules(request, RuleSet.objects.live_rules())

        # clean up after outselves
        if len(rules) == 0:
            logger.debug(
                "Deleting %r as request matches no live rules.", request.profiler
            )  # noqa
            del request.profiler
            return response

        # extract properties from request and response for storing later
        profiler = request.profiler.set_request(request).set_response(response)

        # send signal so that receivers can intercept profiler
        request_profile_complete.send(
            sender=self.__class__, request=request, response=response, instance=profiler
        )
        # if any signal receivers have called cancel() on the profiler, then
        # this method will _not_ save it.
        profiler.capture()

        return response
