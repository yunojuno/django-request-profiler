# -*- coding: utf-8 -*-
# models definitions for request_profiler
from django.conf import settings

# cache key used to store enabled rulesets.
RULESET_CACHE_KEY = getattr(settings, 'REQUEST_PROFILER_RULESET_CACHE_KEY', "request_profiler__rulesets")  # noqa
# how long to cache them for - defaults to 10s
RULESET_CACHE_TIMEOUT = getattr(settings, 'REQUEST_PROFILER_RULESET_CACHE_TIMEOUT', 10)  # noqa

# This is a function that can be used to override all rules to exclude requests from profiling
# e.g. you can use this to ignore staff, or search engine bots, etc.
GLOBAL_EXCLUDE_FUNC = getattr(
    settings, 'REQUEST_PROFILER_GLOBAL_EXCLUDE_FUNC',
    lambda r: not (hasattr(r, 'user') and r.user.is_staff)
)

# if True (default) then store sessions even for anonymous users
STORE_ANONYMOUS_SESSIONS = getattr(settings, 'REQUEST_PROFILE_STORE_ANONYMOUS_SESSIONS', True)  # noqa
