# -*- coding: utf-8 -*-
# models definitions for request_profiler
from django.conf import settings

# default to ignoring all is_staff requests - otherwise you end up in a
# recursive nightmare when looking at the admin site.
IGNORE_STAFF = getattr(settings, 'REQUEST_PROFILER_IGNORE_STAFF', True)

# cache key used to store enabled rulesets.
RULESET_CACHE_KEY = getattr(settings, 'REQUEST_PROFILER_RULESET_CACHE_KEY', "request_profiler__rulesets")  # noqa
# how long to cache them for - defaults to 10s
RULESET_CACHE_TIMEOUT = getattr(settings, 'REQUEST_PROFILER_RULESET_CACHE_TIMEOUT', 10)  # noqa
