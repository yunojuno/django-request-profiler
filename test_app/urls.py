from django.conf.urls import url, include
from django.contrib import admin

from . import views


admin.autodiscover()

urlpatterns = [
    url(
        r'^test/response',
        views.test_response,
        name='test_response'
    ),
    url(
        r'^test/view',
        views.test_view,
        name='test_view'
    ),
    url(
        r'^test/404',
        views.test_404,
        name='test_404'
    ),
    url(
        r'^test/class-based-view$',
        views.TestView.as_view(),
        name='test_cbv'
    ),
    url(
        r'^test/callable-view$',
        views.CallableTestView(),
        name='test_callable_view'
    ),

    url(
        r'^admin/',
        include(admin.site.urls)
    ),
]
