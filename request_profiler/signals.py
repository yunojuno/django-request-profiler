# -*- coding: utf-8 -*-
# signal definitions for request_profiler
from django.dispatch import Signal

# Signal sent after profile data has been captured, but before it is
# saved. This signal can be used to cancel the profiling by calling the
# instance.cancel() method, which sets an internal property telling the
# instance not to save itself when capture() is called.
request_profile_complete = Signal(providing_args=['request', 'response', 'instance'])
