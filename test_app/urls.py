from django.conf.urls import patterns, url, include
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns(
    'test_app.views',
    url(
        r'^test/response',
        'test_response',
        name='test_response'
    ),
    url(
        r'^test/view',
        'test_view',
        name='test_view'
    ),
    url(
        r'^test/404',
        'test_404',
        name='test_404'
    ),

    url(
        r'^admin/',
        include(admin.site.urls)
    ),
)

