# -*- coding: utf-8 -*-
try:
    from django.urls import reverse, resolve
except ImportError:
    from django.core.urlresolvers import reverse, resolve  # noqa

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # Fallback for Django < 1.10
    MiddlewareMixin = object
