
from django.shortcuts import render
from django.http import HttpResponse, Http404


def test_response(request):
    return HttpResponse(u'this is a test')


def test_view(request):
    return render(request, 'test.html')


def test_404(request):
    raise Http404()
