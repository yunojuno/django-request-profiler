from django.http import Http404, HttpResponse
from django.shortcuts import render
from django.views import View


def test_response(request):
    return HttpResponse("this is a test")


def test_view(request):
    return render(request, "test.html")


def test_404(request):
    raise Http404()


class TestView(View):
    def get(self, request):
        return HttpResponse("this is a response of CBV")


class CallableTestView(object):
    def __init__(self, response_text="this is a test"):
        self._response_text = response_text

    def __call__(self, request):
        return HttpResponse(self._response_text)
