from django.contrib import admin
try:
    from django.urls import re_path, include
except ImportError:
    from django.conf.urls import url as re_path, include

from . import views

admin.autodiscover()

urlpatterns = [
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^test/response', views.test_response, name='test_response'),
    re_path(r'^test/view', views.test_view, name='test_view'),
    re_path(r'^test/404', views.test_404, name='test_404'),
    re_path(r'^test/class-based-view$', views.TestView.as_view(), name='test_cbv'),
    re_path(r'^test/callable-view$', views.CallableTestView(), name='test_callable_view'),
]
