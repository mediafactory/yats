# -*- coding: utf-8 -*- 
from django.http.response import HttpResponseRedirect
from django import get_version as get_django_version
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers.json import DjangoJSONEncoder
from yats import get_version, get_python_version
from yats.tickets import table
from yats.shortcuts import get_ticket_model
from yats.models import boards

import datetime
try:
    import json
except ImportError:
    from django.utils import simplejson as json
    
def root(request):
    return table(request)
    #return render_to_response('home.html', {}, RequestContext(request))

def info(request):
    from socket import gethostname

    return render_to_response('info.html', {'hostname': gethostname(), 'version': get_version(), 'date': datetime.datetime.now(), 'django': get_django_version(), 'python': get_python_version()}, RequestContext(request))

def board(request, name):
    # http://bootsnipp.com/snippets/featured/kanban-board
    
    if request.method == 'POST':
        if 'method' in request.POST:
            board = boards.objects.get(pk=request.POST['board'], c_user=request.user)
            try:
                columns = json.loads(board.columns)
            except:
                columns = {}

            if request.POST['method'] == 'add':
                columns[request.POST['column']] = request.session['last_search']
                board.columns = json.dumps(columns, cls=DjangoJSONEncoder)
                board.save(user=request.user)
                
                return HttpResponseRedirect('/board/%s/' % board.name)
                
        else:
            board = boards()
            board.name = request.POST['boardname']
            board.save(user=request.user)
            
            return HttpResponseRedirect('/board/%s/' % request.POST['boardname'])
    
    else:
        board = boards.objects.get(name=name, c_user=request.user)
        try:
            columns = json.loads(board.columns)
        except:
            columns = {}

        if 'method' in request.GET and request.GET['method'] == 'del':
            del columns[request.GET['column']]
            board.columns = json.dumps(columns, cls=DjangoJSONEncoder)
            board.save(user=request.user)
            
            return HttpResponseRedirect('/board/%s/' % name)
            
    for state in columns:
        columns[state] = get_ticket_model().objects.filter(**columns[state])
        
    return render_to_response('board/view.html', {'columns': columns, 'board': board}, RequestContext(request))