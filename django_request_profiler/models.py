
import re
from importlib import import_module

from django.db import models


class RuleSet(models.Model):

    """Set of rules to match a URI and/or User."""

    enabled = models.BooleanField(
        default=True,
        db_index=True
    )
    catch_all = models.BooleanField(
        default=False
    )
    uri_regex = models.TextField(
        blank=True,
        null=True
    )
    user_id = models.IntegerField(
        blank=True,
        null=True
    )
    user_group_name = models.TextField(
        blank=True,
        null=True
    )
    user_function_name = models.TextField(
        blank=True,
        null=True
    )

    def _lookup_function(self):
        """
        Lookup a function from a fully-qualified name,
        e.g. 'my_app.my_module.my_function'.
        """
        if self.user_function_name:
            module_name, function_name = self.user_function_name.rsplit('.', 1)
            module = import_module(module_name)
            function = module.__dict__.get(function_name)
            return function
        else:
            return None

    def matches(self, uri, user):
        """Returns True if this RuleSet matches the uri and/or user."""
        if not self.enabled:
            return False
        if self.catch_all:
            return True
        if self.uri_regex and re.search(self.uri_regex, uri):
            return True
        if self.user_id and user and user.id == self.user_id:
            return True
        if self.user_group_name and user and user.groups.filter(name=self.user_group_name):
            return True
        if self.user_function_name:
            fn = self._lookup_function()
            if fn and fn(user):
                return True
        return False


class ProfilingRecord(models.Model):

    """Record of a request and its response."""

    ruleset = models.ForeignKey(
        'ruleset',
        null=True
    )

    start_ts = models.DateTimeField()
    end_ts = models.DateTimeField()
    duration = models.FloatField()

    method = models.CharField(
        max_length=10,
        null=True,
        blank=True
    )
    uri = models.TextField(
        null=True,
        blank=True
    )
    remote_addr = models.TextField(
        null=True,
        blank=True
    )
    http_user_agent = models.TextField(
        null=True,
        blank=True
    )
    session_key = models.TextField(
        null=True,
        blank=True
    )
    user_id = models.IntegerField(
        null=True,
        blank=True
    )
    view_func_name = models.TextField(
        null=True,
        blank=True
    )
    response_status_code = models.IntegerField(
        null=True,
        blank=True
    )
    template_render_count = models.IntegerField(
        null=True,
        blank=True
    )
