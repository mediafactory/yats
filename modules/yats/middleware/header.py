# -*- coding: utf-8 -*- 
from socket import gethostname

class ResponseInjectHeader(object):
    def process_request(self, request):
        setattr(request, '_dont_enforce_csrf_checks', True)
        return None

    def process_response(self, request, response):
        # response['Access-Control-Allow-Origin'] = '*'
        # response['Access-Control-Allow-Methods'] = 'GET, POST'
        response['X-ProcessedBy'] = gethostname()
        response['Cache-Control'] = 'no-cache, must-revalidate'
        response['Expires'] = 'Sat, 26 Jul 1997 05:00:00 GMT'
        return response