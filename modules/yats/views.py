# -*- coding: utf-8 -*-
from django.http.response import HttpResponseRedirect, HttpResponseNotFound, HttpResponse
from django import get_version as get_django_version
from django.shortcuts import render
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.http import urlquote_plus
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils import timezone
from yats import get_version, get_python_version
from yats.tickets import table
from yats.shortcuts import get_ticket_model, add_breadcrumbs, build_ticket_search
from yats.models import boards
from yats.forms import AddToBordForm, PasswordForm
from yats.yatse import buildYATSFields

import datetime
try:
    import json
except ImportError:
    from django.utils import simplejson as json

def root(request):
    if request.method == 'POST':
        form = PasswordForm(request.POST)
        if form.is_valid():
            request.user.set_password(form.cleaned_data['password'])
        else:
            messages.add_message(request, messages.ERROR, _(u'Password invalid'))

    return table(request)

def info(request):
    from socket import gethostname

    return render(request, 'info.html', {'hostname': gethostname(), 'version': get_version(), 'date': timezone.now(), 'django': get_django_version(), 'python': get_python_version()})

def show_board(request, name):
    # http://bootsnipp.com/snippets/featured/kanban-board

    """
        board structure

        [
            {
                'column': 'closed',
                'query': {'closed': False},
                'limit': 10,
                'extra_filter': 1, # 1 = days since closed, 2 = days since created, 3 = days since last changed, 4 days since last action
                'days': 1, # days
                'order_by': 'id',
                'order_dir': ''
            }
        ]
    """

    if request.method == 'POST':
        if 'method' in request.POST:
            board = boards.objects.get(active_record=True, pk=request.POST['board'], c_user=request.user)
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
                           'order_by': cd['order_by'],
                           'order_dir': cd['order_dir']
                           }
                    if cd.get('extra_filter') and cd.get('days'):
                        col['extra_filter'] = cd['extra_filter']
                        col['days'] = cd['days']
                    columns.append(col)
                    board.columns = json.dumps(columns, cls=DjangoJSONEncoder)
                    board.save(user=request.user)

                else:
                    err_list = []
                    for field in form:
                        for err in field.errors:
                            err_list.append('%s: %s' % (field.name, err))
                    messages.add_message(request, messages.ERROR, _('data invalid: %s') % '\n'.join(err_list))

                return HttpResponseRedirect('/board/%s/' % urlquote_plus(board.name))

        else:
            if boards.objects.filter(active_record=True, c_user=request.user, name=request.POST['boardname']).count() == 0:
                board = boards()
                board.name = request.POST['boardname'].strip()
                board.save(user=request.user)

                return HttpResponseRedirect('/board/%s/' % urlquote_plus(request.POST['boardname']))

            else:
                messages.add_message(request, messages.ERROR, _(u'A board with the name "%s" already exists' % request.POST['boardname']))
                return HttpResponseRedirect('/')

    else:
        board = boards.objects.get(active_record=True, name=name, c_user=request.user)
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

        elif 'method' in request.GET and request.GET['method'] == 'delete':
            board.delete(user=request.user)
            return HttpResponseRedirect('/')

    for column in columns:
        query = get_ticket_model().objects.select_related('type', 'priority').all()
        search_params, query = build_ticket_search(request, query, {}, column['query'])
        column['query'] = query.order_by('%s%s' % (column.get('order_dir', ''), column.get('order_by', 'id')))
        if column['limit']:
            column['query'] = column['query'][:column['limit']]
        if 'extra_filter' in column and 'days' in column and column['extra_filter'] and column['days']:
            if column['extra_filter'] == '1':  # days since closed
                column['query'] = column['query'].filter(close_date__gte=datetime.date.today() - datetime.timedelta(days=column['days'])).exclude(close_date=None)
            if column['extra_filter'] == '2':  # days since created
                column['query'] = column['query'].filter(c_date__gte=datetime.date.today() - datetime.timedelta(days=column['days']))
            if column['extra_filter'] == '3':  # days since last changed
                column['query'] = column['query'].filter(u_date__gte=datetime.date.today() - datetime.timedelta(days=column['days']))
            if column['extra_filter'] == '4':  # days since last action
                column['query'] = column['query'].filter(last_action_date__gte=datetime.date.today() - datetime.timedelta(days=column['days']))
        if not request.user.is_staff:
            column['query'] = column['query'].filter(customer=request.organisation)

    add_breadcrumbs(request, board.pk, '$')
    return render(request, 'board/view.html', {'columns': columns, 'board': board})

def board_by_id(request, id):
    board = boards.objects.get(active_record=True, pk=id, c_user=request.user)
    return show_board(request, board.name)

def yatse_api(request, method):
    if method == 'fields':
        fields = buildYATSFields([])
        return HttpResponse(json.dumps(fields[0]))

    else:
        return HttpResponseNotFound()
