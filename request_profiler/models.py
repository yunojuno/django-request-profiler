# -*- coding: utf-8 -*-
# models definitions for request_profiler
import re

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from request_profiler import settings


class RuleSetManager(models.Manager):
    """Custom model manager for RuleSet instances."""
    def live_rules(self):
        """Return enabled rules.

        TODO: cache results.
        """
        return self.get_queryset().filter(enabled=True)


class RuleSet(models.Model):
    """Set of rules to match a URI and/or User."""

    enabled = models.BooleanField(
        default=True,
        db_index=True,
    )
    uri_regex = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text=u"Regex used to filter by request URI."
    )
    user_group_filter = models.CharField(
        blank=True,
        default="",
        max_length=100,
        help_text=u"Name of a group used to filter users to profile.",
        verbose_name=u"User Group Filter"
    )
    include_anonymous = models.BooleanField(
        default=True,
        help_text=u"Include anonymous users (ignore group filters)."
    )
    # use the custom model manager
    objects = RuleSetManager()

    @property
    def has_group_filter(self):
        return len(self.user_group_filter.strip()) > 0

    def match_uri(self, request_uri):
        """Return True if there is a uri_regex and it matches.

        Args:
            request_uri: string, the HttpRequest.build_absolute_uri(), used
                to match against all the uri_regex.

        Returns True if there is a uri_regex and it matches, or if there
            there is no uri_regex, in which the match is implicit.

        """
        regex = self.uri_regex.strip()
        if regex == "":
            return True
        else:
            return re.search(regex, request_uri) is not None

    def match_user(self, user):
        """Return True if the user passes the various user filters.

        Match user against anonymous and group filters.
        """
        # if the user is anonymous, then they'll have no groups, and
        # the group filter is irrelevant - if you're including anonymous
        # that's all that counts
        if user is None or user.is_anonymous():
            return self.include_anonymous
        elif user.is_staff and settings.IGNORE_STAFF:
            return False

        # user is authenticated and not staff - do we have a group filter?
        if self.has_group_filter:
            # does the group exist in the user's groups
            return self.user_group_filter.strip() in [g.name for g in user.groups.all()]

        return True


class ProfilingRecord(models.Model):

    """Record of a request and its response."""
    user = models.ForeignKey(User, null=True, blank=True)
    session_key = models.CharField(blank=True, max_length=40)
    start_ts = models.DateTimeField(verbose_name="Request started at")
    end_ts = models.DateTimeField(verbose_name="Request ended at")
    duration = models.FloatField(verbose_name="Request duration (sec)")
    http_method = models.CharField(max_length=10)
    request_uri = models.URLField(verbose_name="Request path")
    remote_addr = models.CharField(max_length=100)
    http_user_agent = models.CharField(max_length=400)
    view_func_name = models.CharField(max_length=100, verbose_name="View function")
    response_status_code = models.IntegerField()

    def start(self):
        """Set start_ts from current datetime."""
        self.start_ts = timezone.now()
        self.end_ts = None
        self.duration = None
        return self

    @property
    def elapsed(self):
        """Calculated time elapsed so far."""
        assert self.start_ts is not None, u"You must 'start' before you can get elapsed time."
        return (timezone.now() - self.start_ts).total_seconds()

    def set_request_properties(self, request):
        """Extract values from HttpRequest and store locally."""
        self.http_method = request.method
        self.request_uri = request.path
        self.http_user_agent = request.META.get('HTTP_USER_AGENT'),
        # X-Forwarded-For is used by convention when passing through
        # load balancers etc., as the REMOTE_ADDR is rewritten in transit
        self.remote_addr = (
            request.META.get('X-Forwarded-For')
            if 'X-Forwarded-For' in request.META
            else request.META.get('REMOTE_ADDR')
        )
        # these two require middleware, so may not exist
        if hasattr(request, 'session'):
            self.session_key = request.session.session_key or ""
        # NB you can't store AnonymouseUsers, so don't bother trying
        if hasattr(request, 'user') and request.user.is_authenticated():
            self.user = request.user

    def stop(self):
        """Set end_ts and duration from current datetime."""
        assert self.start_ts is not None, u"You must 'start' before you can 'stop'"
        self.end_ts = timezone.now()
        self.duration = (self.end_ts - self.start_ts).total_seconds()
        return self
