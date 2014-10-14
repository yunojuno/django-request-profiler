# -*- coding: utf-8 -*-
# models definitions for request_profiler
from django.conf import settings

# default to ignoring all is_staff requests - otherwise you end up in a
# recursive nightmare when looking at the admin site.
IGNORE_STAFF = getattr(settings, 'REQUEST_PROFILER_IGNORE_STAFF', True)
