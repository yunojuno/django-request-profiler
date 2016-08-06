from django.conf.urls import url, include
from django.contrib import admin

from test_app import views

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
        r'^admin/',
        include(admin.site.urls)
    ),
]
