from django.http import HttpResponseNotFound, Http404

class schiwagoTestException(Exception):
    """
    Raise an error for test
    """

def raiseerror(request):
    raise schiwagoTestException('just a test error')

def raise404(request):
    raise Http404('testing not found as exception')

def notfound(request):
    return HttpResponseNotFound('just a test for 404')