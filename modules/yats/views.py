# -*- coding: utf-8 -*-
from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect, HttpResponseNotFound, HttpResponse, HttpResponseForbidden, JsonResponse
from django import get_version as get_django_version
from django.shortcuts import render
from django.core.serializers.json import DjangoJSONEncoder
from django.utils.http import urlquote_plus
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils import timezone
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login as auth_login, logout as aut_logout
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.conf import settings
from django.utils import translation
from yats import get_version, get_python_version
from yats.tickets import table
from yats.shortcuts import get_ticket_model, add_breadcrumbs, build_ticket_search_ext, convert_sarch
from yats.models import boards, tickets_participants, ticket_flow, ticket_flow_edges, tickets_ignorants, UserProfile
from yats.forms import AddToBordForm, PasswordForm, TicketCloseForm, TicketReassignForm
from yats.yatse import api_login, buildYATSFields, YATSSearch

from haystack.query import SearchQuerySet
import datetime
import locale
try:
    import json
except ImportError:
    from django.utils import simplejson as json

from urllib.parse import unquote_plus

def root(request, form=None):
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = PasswordForm(request.POST)
            if form.is_valid():
                request.user.set_password(form.cleaned_data['password'])
                request.user.save()
                messages.add_message(request, messages.SUCCESS, _(u'Successfully changed password'))
            else:
                messages.add_message(request, messages.ERROR, _(u'Password invalid'))

        return table(request)

    else:
        return HttpResponseRedirect('/local_login/')

def login(request):
    if request.user.is_authenticated:
        if 'next' in request.GET:
            return HttpResponseRedirect(request.GET['next'])
        else:
            return HttpResponseRedirect('/')

    if request.method == 'POST':
        form = AuthenticationForm(request.POST)
        user = authenticate(request, username=request.POST['username'], password=request.POST['password'])
        if user:
            auth_login(request, user)
            return HttpResponseRedirect('/')
        else:
            messages.add_message(request, messages.ERROR, _(u'Data invalid'))
    form = AuthenticationForm()
    if hasattr(settings, 'SSO_PRIVATE_KEY') and settings.SSO_PRIVATE_KEY:
        sso = True
    else:
        sso = False
    return render(request, 'login.html', {'form': form, 'sso': sso})

def logout(request):
    aut_logout(request)
    return HttpResponseRedirect('/local_login/')

@login_required
def info(request):
    from socket import gethostname

    return render(request, 'info.html', {'hostname': gethostname(), 'version': get_version(), 'date': timezone.now(), 'django': get_django_version(), 'python': get_python_version()})

@login_required
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

    name = unquote_plus(name)

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
            if request.POST['boardname'].strip() != '':
                if boards.objects.filter(active_record=True, c_user=request.user, name=request.POST['boardname']).count() == 0 and request.POST['boardname']:
                        board = boards()
                        board.name = request.POST['boardname'].strip()
                        board.save(user=request.user)

                        return HttpResponseRedirect('/board/%s/' % urlquote_plus(request.POST['boardname']))

                else:
                    messages.add_message(request, messages.ERROR, _(u'A board with the name "%s" already exists' % request.POST['boardname']))
                    return HttpResponseRedirect('/')
            else:
                messages.add_message(request, messages.ERROR, _(u'No name for a board given'))
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
        query = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
        search_params, query = build_ticket_search_ext(request, query, column['query'])
        column['query'] = query.order_by('%s%s' % (column.get('order_dir', ''), column.get('order_by', 'id')))
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

        seen_elements = {}
        seen = tickets_participants.objects.filter(user=request.user, ticket__in=column['query'].values_list('id', flat=True)).values_list('ticket_id', 'seen')
        for see in seen:
            seen_elements[see[0]] = see[1]

        seen = tickets_ignorants.objects.filter(user=request.user, ticket__in=column['query'].values_list('id', flat=True)).values_list('ticket_id')
        for see in seen:
            seen_elements[see[0]] = True

        if column['limit']:
            column['query'] = column['query'][:column['limit']]
        column['seen'] = seen_elements

    add_breadcrumbs(request, board.pk, '$')
    return render(request, 'board/view.html', {'columns': columns, 'board': board})

@login_required
def board_by_id(request, id):
    board = boards.objects.get(active_record=True, pk=id, c_user=request.user)
    return show_board(request, board.name)

def yatse_api(request):
    try:
        if request.method != 'PROPFIND':
            api_login(request)

    except PermissionDenied:
        return HttpResponseForbidden(request.META.get('HTTP_API_USER'))

    if request.method == 'PROPPATCH':
        data = json.loads(request.body)
        if 'ticket' in data and 'method' in data:
            if data['method'] == 'notify':
                tickets_participants.objects.filter(ticket=data['ticket'], user=request.user).update(seen=True)
                return HttpResponse('OK')
        return HttpResponseNotFound('invalid method\n\n%s' % request.body)

    elif request.method == 'PROPFIND':
        fields = buildYATSFields([])
        return JsonResponse(fields[0], safe=False)

    elif request.method == 'SEARCH':
        return JsonResponse(YATSSearch(request), safe=False)

    else:
        return HttpResponseNotFound('invalid method')

@login_required
def kanban(request):
    flows = ticket_flow.objects.all().order_by('type')
    columns = []
    finish_state = -1
    days = UserProfile.objects.get(user=request.user).day_since_closed_tickets

    query = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()

    for flow in flows:
        search_params, flow.data = build_ticket_search_ext(request, query, convert_sarch({'state': flow.pk}))
        flow.data = flow.data.filter(Q(show_start=None) | Q(show_start__lte=timezone.now()))

        if flow.type == 2:
            flow.data = flow.data.filter(Q(assigned=None) | Q(assigned=request.user)).order_by('-close_date')
        else:
            flow.data = flow.data.filter(Q(assigned=None) | Q(assigned=request.user)).extra(select={'prio': 'COALESCE(caldav, 10)'}, order_by=['prio', '-c_date'])

        if flow.type == 1:
            columns.insert(0, flow)
        else:
            columns.append(flow)
            if flow.type == 2:
                finish_state = flow.pk
                flow.data = flow.data.filter(close_date__gte=datetime.date.today() - datetime.timedelta(days=days))

        seen_elements = {}
        seen = tickets_participants.objects.filter(user=request.user, ticket__in=flow.data.values_list('id', flat=True)).values_list('ticket_id', 'seen')
        for see in seen:
            seen_elements[see[0]] = see[1]

        seen = tickets_ignorants.objects.filter(user=request.user, ticket__in=flow.data.values_list('id', flat=True)).values_list('ticket_id')
        for see in seen:
            seen_elements[see[0]] = True

        flow.seen = seen_elements

    close = TicketCloseForm()
    reassign = TicketReassignForm()
    edges = ticket_flow_edges.objects.all().order_by('now')
    add_breadcrumbs(request, 0, 'k')
    cur_language = translation.get_language()
    return render(request, 'board/kanban.html', {'layout': 'horizontal', 'columns': columns, 'edges': edges, 'finish_state': finish_state, 'close': close, 'reassign': reassign, 'cur_language': cur_language})

@login_required
def xptest(request, test):
    if test == 'xmpp':
        from pyxmpp2.simple import send_message
        send_message(settings.JABBER_HOST_USER, settings.JABBER_HOST_PASSWORD, settings.JABBER_TEST_RECIPIENT, 'moin 1')
        import time
        time.sleep(2)
        send_message(settings.JABBER_HOST_USER, settings.JABBER_HOST_PASSWORD, settings.JABBER_TEST_RECIPIENT, 'moin, moin 2')
        return HttpResponse('OK')

    if test == 'signal':
        from yats.shortcuts import send_signal
        send_signal('moin 1 - äöüß', [settings.SIGNAL_TEST_RECIPIENT])
        send_signal('moin, moin 2 - äöüß', [settings.SIGNAL_TEST_RECIPIENT])
        return HttpResponse('OK')

    else:
        return HttpResponseNotFound(test)

def robots(request):
    return HttpResponse('User-agent: *\nDisallow: /', content_type='text/plain')

@login_required
def autocomplete(request):
    # for datetime format
    locale.setlocale(locale.LC_ALL, 'de_DE.UTF-8')

    args = []
    models = request.GET.getlist('models')
    for model in models:
        args.append(apps.get_model(model))

    sqs = SearchQuerySet().models(*set(args))
    # only open tickets in autocomplete
    sqs = sqs.filter(closed=False)
    if not request.user.is_staff:
        sqs = sqs.filter(customer=request.organisation.pk)

    q = request.GET.get('q', '').split(' ')
    for word in q:
        word = word.strip()
        if word:
            sqs = sqs.filter(content_auto__contains=word)

    if len(models) == 1 and models[0] == 'web.test':
        sqs = sqs.order_by('-last_action_date')

    result = []
    if 'suggestions' in request.GET:
        suggestion = sqs.spelling_suggestion()
        if suggestion:
            result.append({'caption': suggestion})

    else:
        for ele in sqs:
            data = {
                'caption': str(ele.caption),
                'id': ele.pk
            }
            if hasattr(ele, 'closed') and ele.closed:
                data['closed'] = ele.closed
            result.append(data)

    return JsonResponse(result, safe=False)
