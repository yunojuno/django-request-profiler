from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any

from django.conf import settings as django_settings
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import connection, models
from django.db.models.query import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from . import settings

if TYPE_CHECKING:
    from django_settings import AUTH_USER_MODEL


logger = logging.getLogger(__name__)


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

    def match_user(self, user: AUTH_USER_MODEL) -> bool:
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

    def save(self, *args: Any, **kwargs: Any) -> ProfilingRecord:
        super().save(*args, **kwargs)
        return self

    def start(self) -> ProfilingRecord:
        """Set start_ts from current datetime."""
        self.start_ts = timezone.now()
        self.end_ts = None
        self.duration = None
        self.query_count = 0
        self._query_count = len(connection.queries)
        self._force_debug_cursor = connection.force_debug_cursor
        connection.force_debug_cursor = settings.FORCE_DEBUG_CURSOR
        return self

    @property
    def elapsed(self) -> float:
        """Time (in seconds) elapsed so far."""
        if self.start_ts is None:
            raise ValueError("You must 'start' before you can get elapsed time.")
        return (timezone.now() - self.start_ts).total_seconds()

    def set_request(self, request: HttpRequest) -> ProfilingRecord:
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
        return self

    def set_response(self, response: HttpResponse) -> ProfilingRecord:
        """Extract values from HttpResponse and store locally."""
        self.response = response
        self.response_status_code = response.status_code
        self.response_content_length = len(response.content)
        return self

    def stop(self) -> ProfilingRecord:
        """Set end_ts and duration from current datetime."""
        if self.start_ts is None:
            raise ValueError("You must 'start' before you can 'stop'")
        self.end_ts = timezone.now()
        self.duration = (self.end_ts - self.start_ts).total_seconds()
        self.query_count = len(connection.queries) - self._query_count
        connection.force_debug_cursor = self._force_debug_cursor
        if hasattr(self, "response"):
            self.response["X-Profiler-Duration"] = self.duration
        return self

    def cancel(self) -> ProfilingRecord:
        """Cancel the profile by setting is_cancelled to True."""
        self.start_ts = None
        self.end_ts = None
        self.duration = None
        self.is_cancelled = True
        return self

    def capture(self) -> ProfilingRecord:
        """Call stop() and save() on the profile if is_cancelled is False."""
        if getattr(self, "is_cancelled", False) is True:
            logger.debug("%r has been cancelled.", self)
            return self
        else:
            self.stop().save()
            return self
