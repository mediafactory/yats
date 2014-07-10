# -*- coding: utf-8 -*- 
from django.http.response import HttpResponseRedirect
from django import get_version as get_django_version
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.http import urlquote_plus
from yats import get_version, get_python_version
from yats.tickets import table
from yats.shortcuts import get_ticket_model
from yats.models import boards
from yats.forms import AddToBordForm

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
    
    """
        board structure
        
        [
            {
                'column': 'closed',
                'query': {'closed': False},
                'limit': 10,
                
                'time_filter': 1, # days
                'time_filter_type': 1, # 1 = days since closed, 2 = days since created, 3 = days since last changed, 4 days since last action
                'order_by': 'id',
                'order_dir': ''
            }
        ]
    """
    
    if request.method == 'POST':
        if 'method' in request.POST:
            board = boards.objects.get(pk=request.POST['board'], c_user=request.user)
            try:
                columns = json.loads(board.columns)
            except:
                columns = []

            if request.POST['method'] == 'add':
                form = AddToBordForm(request.POST)
                if form.is_valid():
                    cd = form.cleaned_data 
                    col = {
                           'column': cd['column'],
                           'query': request.session['last_search'],
                           'limit': cd['limit'],
                           }
                    columns.append(col)
                    board.columns = json.dumps(columns, cls=DjangoJSONEncoder)
                    board.save(user=request.user)
                
                return HttpResponseRedirect('/board/%s/' % urlquote_plus(board.name))
                
        else:
            board = boards()
            board.name = request.POST['boardname']
            board.save(user=request.user)
            
            return HttpResponseRedirect('/board/%s/' % urlquote_plus(request.POST['boardname']))
    
    else:
        board = boards.objects.get(name=name, c_user=request.user)
        try:
            columns = json.loads(board.columns)
        except:
            columns = []

        if 'method' in request.GET and request.GET['method'] == 'del':
            new_columns = []
            for col in columns:
                if col['column'] != request.GET['column']:
                    new_columns.append(col)
            board.columns = json.dumps(new_columns, cls=DjangoJSONEncoder)
            board.save(user=request.user)
            
            return HttpResponseRedirect('/board/%s/' % urlquote_plus(name))
            
    for column in columns:
        column['query'] = get_ticket_model().objects.filter(**column['query']).order_by('%s%s' % (column.get('order_dir', ''), column.get('order_by', 'id')))
        if column['limit']:
            column['query'] = column['query'][:column['limit']]
        
    return render_to_response('board/view.html', {'columns': columns, 'board': board}, RequestContext(request))