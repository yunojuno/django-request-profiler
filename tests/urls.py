from django.contrib import admin
from django.urls import path

from . import views

admin.autodiscover()

urlpatterns = [
    path("admin/", admin.site.urls),
    path("test/response/", views.test_response, name="test_response"),
    path("test/view/", views.test_view, name="test_view"),
    path("test/404/", views.test_404, name="test_404"),
    path("test/class-based-view/", views.TestView.as_view(), name="test_cbv"),
    path("test/callable-view/", views.CallableTestView(), name="test_callable_view"),
]
