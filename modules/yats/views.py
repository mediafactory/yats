# -*- coding: utf-8 -*- 
from django import get_version as get_django_version
from django.shortcuts import render_to_response
from django.template import RequestContext
from yats import get_version, get_python_version

import datetime

def root(request):
    return render_to_response('home.html', {}, RequestContext(request))

def info(request):
    from socket import gethostname

    return render_to_response('info.html', {'hostname': gethostname(), 'version': get_version(), 'date': datetime.datetime.now(), 'django': get_django_version(), 'python': get_python_version()}, RequestContext(request))
