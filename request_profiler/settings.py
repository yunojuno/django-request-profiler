# models definitions for request_profiler
from django.conf import settings

# cache key used to store enabled rulesets.
RULESET_CACHE_KEY = getattr(
    settings, "REQUEST_PROFILER_RULESET_CACHE_KEY", "request_profiler__rulesets"
)  # noqa

# how long to cache them for - defaults to 10s
RULESET_CACHE_TIMEOUT = getattr(
    settings, "REQUEST_PROFILER_RULESET_CACHE_TIMEOUT", 10
)  # noqa

# set to True to force the use of a debug cursor so that queries can be counted
# use with caution - this will force the db.connection to store queries
FORCE_DEBUG_CURSOR = getattr(settings, "REQUEST_PROFILER_FORCE_DEBUG_CURSOR", False)

# This is a function that can be used to override all rules to exclude requests
# from profiling e.g. you can use this to ignore staff, or search engine bots, etc.
GLOBAL_EXCLUDE_FUNC = getattr(
    settings,
    "REQUEST_PROFILER_GLOBAL_EXCLUDE_FUNC",
    lambda r: not (hasattr(r, "user") and r.user.is_staff),
)

# if True (default) then store sessions even for anonymous users
STORE_ANONYMOUS_SESSIONS = getattr(
    settings, "REQUEST_PROFILE_STORE_ANONYMOUS_SESSIONS", True
)  # noqa
