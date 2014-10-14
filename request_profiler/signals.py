# -*- coding: utf-8 -*-
# signal definitions for request_profiler
from django.dispatch import Signal

# Signal sent after profile data has been captured, but before it is
# saved. If any receiving function returns False, the data is not saved.
# This can be used to, for instance, save the data asynchronously, by adding
# the `ProfilingRecord.save()` method call to a queue, and then returning False.
# The `instance` arg sent is a ProfilingRecord instance.
request_profile_complete = Signal(providing_args=['request', 'response', 'instance'])
