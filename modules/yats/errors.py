# -*- coding: utf-8 -*-
from django.shortcuts import render

def server_error(request):
    # one of the things ‘render’ does is add ‘STATIC_URL’ to
    # the context, making it available from within the template.
    response = render(request, '500.html')
    response.status_code = 500
    return response
