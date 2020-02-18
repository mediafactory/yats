# -*- coding: utf-8 -*-
from socket import gethostname

def ResponseInjectHeader(get_response):

    def middleware(request):
        setattr(request, '_dont_enforce_csrf_checks', True)

        response = get_response(request)

        # response['Access-Control-Allow-Origin'] = '*'
        # response['Access-Control-Allow-Methods'] = 'GET, POST'
        response['X-ProcessedBy'] = gethostname()
        response['Cache-Control'] = 'no-cache, must-revalidate'
        response['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
        return response

    return middleware
