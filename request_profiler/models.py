from __future__ import annotations

import logging
import re
from typing import Any, Callable

from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _lazy

from . import settings

logger = logging.getLogger(__name__)


class BadProfilerError(ValueError):
    pass


class RuleSetQuerySet(models.query.QuerySet):
    """Custom QuerySet for RuleSet instances."""

    def live_rules(self) -> QuerySet:
        """Return enabled rules."""
        rulesets = cache.get(settings.RULESET_CACHE_KEY)
        if rulesets is None:
            rulesets = self.filter(enabled=True)
            cache.set(
                settings.RULESET_CACHE_KEY, rulesets, settings.RULESET_CACHE_TIMEOUT
            )
        return rulesets


class RuleSet(models.Model):
    """Set of rules to match a URI and/or User."""

    # property used to determine how to filter users
    USER_FILTER_ALL = 0
    USER_FILTER_AUTH = 1
    USER_FILTER_GROUP = 2

    USER_FILTER_CHOICES = (
        (USER_FILTER_ALL, "All users (inc. None)"),
        (USER_FILTER_AUTH, "Authenticated users only"),
        (USER_FILTER_GROUP, "Users in a named group"),
    )

    enabled = models.BooleanField(default=True, db_index=True)
    uri_regex = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text="Regex used to filter by request URI.",
        verbose_name="Request path regex",
    )
    user_filter_type = models.IntegerField(
        default=0,
        choices=USER_FILTER_CHOICES,
        help_text="Filter requests by type of user.",
        verbose_name="User type filter",
    )
    user_group_filter = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text="Group used to filter users.",
        verbose_name="User group filter",
    )
    # use the custom model manager
    objects = RuleSetQuerySet.as_manager()

    def __str__(self) -> str:
        return "Profiling rule #{}".format(self.pk)

    @property
    def has_group_filter(self) -> bool:
        return len(self.user_group_filter.strip()) > 0

    def clean(self) -> None:
        """Ensure that user_filter_group and user_filter_type values are appropriate."""
        if self.has_group_filter and self.user_filter_type != RuleSet.USER_FILTER_GROUP:
            raise ValidationError(
                "User filter type must be 'group' if you specify a group."
            )
        if (
            self.user_filter_type == RuleSet.USER_FILTER_GROUP
            and not self.has_group_filter
        ):
            raise ValidationError(
                "You must specify a group if the filter type is 'group'."
            )
        # check regex is a valid regex
        try:
            re.search(self.uri_regex, "/")
        except re.error as ex:
            raise ValidationError(f"Invalid uri_regex (r'{self.uri_regex}'): {ex}")

    def match_uri(self, request_uri: str) -> bool:
        """
        Return True if there is a uri_regex and it matches.

        Args:
            request_uri: the HttpRequest.build_absolute_uri(), used
                to match against all the uri_regex.

        Returns True if there is a uri_regex and it matches, or if there
        there is no uri_regex, in which the match is implicit.

        """
        regex = self.uri_regex.strip()
        if regex == "":
            return True
        try:
            return re.search(regex, request_uri) is not None
        except re.error:
            logger.exception("Regex error running request profiler.")
        return False

    def match_user(self, user: django_settings.AUTH_USER_MODEL) -> bool:
        """Return True if the user passes the various user filters."""
        # treat no user (i.e. has not been added) as AnonymousUser()
        user = user or AnonymousUser()

        if self.user_filter_type == RuleSet.USER_FILTER_ALL:
            return True

        if self.user_filter_type == RuleSet.USER_FILTER_AUTH:
            return user.is_authenticated

        if self.user_filter_type == RuleSet.USER_FILTER_GROUP:
            group = self.user_group_filter.strip()
            return user.groups.filter(name__iexact=group).exists()

        # if we're still going, then it's a no. it's also an invalid
        # user_filter_type, so we may want to think about a warning
        return False


class ProfilingRecord(models.Model):
    """Record of a request and its response."""

    user = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    session_key = models.CharField(blank=True, max_length=40)
    start_ts = models.DateTimeField(verbose_name="Request started at")
    end_ts = models.DateTimeField(verbose_name="Request ended at")
    duration = models.FloatField(verbose_name="Request duration (sec)")
    http_method = models.CharField(max_length=10)
    request_uri = models.URLField(verbose_name="Request path")
    query_string = models.TextField(null=False, blank=True, verbose_name="Query string")
    remote_addr = models.CharField(max_length=100)
    http_user_agent = models.CharField(max_length=400)
    http_referer = models.CharField(max_length=400, default="")
    view_func_name = models.CharField(max_length=100, verbose_name="View function")
    response_status_code = models.IntegerField()
    response_content_length = models.IntegerField()
    query_count = models.IntegerField(
        help_text="Number of database queries logged during request.",
        blank=True,
        null=True,
    )

    def __str__(self) -> str:
        return "Profiling record #{}".format(self.pk)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self.is_running = False
        super().__init__(*args, **kwargs)

    def save(self, *args: Any, **kwargs: Any) -> ProfilingRecord:
        super().save(*args, **kwargs)
        return self

    @property
    def elapsed(self) -> float:
        """Time (in seconds) elapsed so far."""
        self.check_is_running()
        return (timezone.now() - self.start_ts).total_seconds()

    def process_request(self, request: HttpRequest) -> None:
        """Extract values from HttpRequest and store locally."""
        self.request = request
        self.http_method = request.method
        self.request_uri = request.path
        self.query_string = request.META.get("QUERY_STRING", "")
        self.http_user_agent = request.META.get("HTTP_USER_AGENT", "")[:400]
        # we care about the domain more than the URL itself, so truncating
        # doesn't lose much useful information
        self.http_referer = request.META.get("HTTP_REFERER", "")[:400]
        # X-Forwarded-For is used by convention when passing through
        # load balancers etc., as the REMOTE_ADDR is rewritten in transit
        self.remote_addr = (
            request.META.get("HTTP_X_FORWARDED_FOR")
            if "HTTP_X_FORWARDED_FOR" in request.META
            else request.META.get("REMOTE_ADDR")
        )
        # these two require middleware, so may not exist
        if hasattr(request, "session"):
            self.session_key = request.session.session_key or ""
        # NB you can't store AnonymouseUsers, so don't bother trying
        if hasattr(request, "user") and request.user.is_authenticated:
            self.user = request.user

    def _extract_view_func_name(self, view_func: Callable) -> str:
        # the View.as_view() method sets this
        if hasattr(view_func, "view_class"):
            return view_func.view_class.__name__
        return (
            view_func.__name__
            if hasattr(view_func, "__name__")
            else view_func.__class__.__name__
        )

    def _content_length(self, response: HttpResponse) -> int:
        """Return the response content length."""
        if isinstance(response, StreamingHttpResponse):
            return -1
        return len(response.content)

    def process_view(self, request: HttpRequest, view_func: Callable) -> None:
        """Handle the process_view middleware event."""
        self.view_func_name = self._extract_view_func_name(view_func)

    def process_response(self, response: HttpResponse) -> None:
        """Extract values from HttpResponse and store locally."""
        self.response = response
        self.response_status_code = response.status_code
        self.response_content_length = self._content_length(response)

    def check_is_running(self) -> ProfilingRecord:
        """Raise BadProfilerError if profile is not running."""
        if self.start_ts is None:
            raise BadProfilerError(_lazy("RequestProfiler has not started."))
        if not self.is_running:
            raise BadProfilerError(_lazy("RequestProfiler is no longer running."))
        return self

    def start(self) -> ProfilingRecord:
        """Set start_ts from current datetime."""
        self.is_running = True
        self.start_ts = timezone.now()
        self.end_ts = None
        self.duration = None
        self.query_count = 0
        self._query_count = len(connection.queries)
        self._force_debug_cursor = connection.force_debug_cursor
        connection.force_debug_cursor = settings.FORCE_DEBUG_CURSOR
        return self

    def stop(self) -> ProfilingRecord:
        """Set end_ts and duration from current datetime."""
        self.check_is_running()
        self.end_ts = timezone.now()
        self.duration = (self.end_ts - self.start_ts).total_seconds()
        self.query_count = len(connection.queries) - self._query_count
        connection.force_debug_cursor = self._force_debug_cursor
        if hasattr(self, "response"):
            self.response["X-Profiler-Duration"] = self.duration
        self.is_running = False
        return self

    def cancel(self) -> ProfilingRecord:
        """Cancel the profile by setting is_running to False."""
        self.start_ts = None
        self.end_ts = None
        self.duration = None
        self.is_running = False
        return self

    def capture(self) -> ProfilingRecord:
        """Call stop and save."""
        return self.check_is_running().stop().save()
