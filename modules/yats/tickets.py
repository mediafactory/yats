# -*- coding: utf-8 -*-
from django.shortcuts import render
from django.http.response import HttpResponseRedirect, StreamingHttpResponse, HttpResponse
from django.apps import apps
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from django.contrib.auth.models import User
from yats.forms import TicketsForm, CommentForm, UploadFileForm, SearchForm, TicketCloseForm, TicketReassignForm, AddToBordForm
from yats.models import tickets_files, tickets_comments, tickets_reports, ticket_resolution, tickets_participants, tickets_history, ticket_flow_edges, ticket_flow, get_flow_start, get_flow_end
from yats.shortcuts import resize_image, touch_ticket, mail_ticket, mail_comment, mail_file, clean_search_values, check_references, remember_changes, add_history, prettyValues, add_breadcrumbs, get_ticket_model
import os
import io
import graph
import datetime
try:
    import json
except ImportError:
    from django.utils import simplejson as json

def new(request):
    excludes = ['resolution']

    if request.method == 'POST':
        form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
        if form.is_valid():
            tic = form.save()

            assigned = form.cleaned_data.get('assigned')
            if assigned:
                touch_ticket(assigned, tic.pk)

            for ele in form.changed_data:
                form.initial[ele] = ''
            remember_changes(request, form, tic)

            touch_ticket(request.user, tic.pk)

            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)

            if form.cleaned_data.get('file_addition', False):
                return HttpResponseRedirect('/tickets/upload/%s/' % tic.pk)
            else:
                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)

    else:
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    form.fields['state'].queryset = form.fields['state'].queryset.exclude(type=2)

    return render(request, 'tickets/new.html', {'layout': 'horizontal', 'form': form})

def action(request, mode, ticket):
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    tic = apps.get_model(mod_path, cls_name).objects.get(pk=ticket)

    if mode == 'view':
        if request.method == 'POST':
            form = CommentForm(request.POST)
            if form.is_valid():
                com = tickets_comments()
                com.comment = form.cleaned_data['comment']
                com.ticket_id = ticket
                com.action = 6
                com.save(user=request.user)

                check_references(request, com)

                touch_ticket(request.user, ticket)

                add_history(request, tic, 6, com.comment)

                mail_comment(request, com.pk)

            else:
                if 'resolution' in request.POST:
                    if request.POST['resolution'] and int(request.POST['resolution']) > 0:
                        tic.resolution_id = request.POST['resolution']
                        tic.closed = True
                        tic.close_date = datetime.datetime.now()
                        tic.state = get_flow_end()
                        tic.save(user=request.user)

                        com = tickets_comments()
                        com.comment = _('ticket closed - resolution: %(resolution)s\n\n%(comment)s') % {'resolution': ticket_resolution.objects.get(pk=request.POST['resolution']).name, 'comment': request.POST.get('close_comment', '')}
                        com.ticket_id = ticket
                        com.action = 1
                        com.save(user=request.user)

                        check_references(request, com)

                        touch_ticket(request.user, ticket)

                        add_history(request, tic, 1, request.POST.get('close_comment', ''))

                        mail_comment(request, com.pk)

                    else:
                        messages.add_message(request, messages.ERROR, _('no resolution selected'))

                else:
                    messages.add_message(request, messages.ERROR, _('comment invalid'))

        excludes = []
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id, view_only=True)
        close = TicketCloseForm()
        reassign = TicketReassignForm(initial={'assigned': tic.assigned_id, 'state': tic.state})
        flows = list(ticket_flow_edges.objects.select_related('next').filter(now=tic.state).exclude(next__type=2).values_list('next', flat=True))
        flows.append(tic.state_id)
        reassign.fields['state'].queryset = reassign.fields['state'].queryset.filter(id__in=flows)

        participants = tickets_participants.objects.select_related('user').filter(ticket=ticket)
        comments = tickets_comments.objects.select_related('c_user').filter(ticket=ticket).order_by('c_date')

        close_allowed = ticket_flow_edges.objects.select_related('next').filter(now=tic.state, next__type=2).count() > 0

        files = tickets_files.objects.filter(ticket=ticket)
        paginator = Paginator(files, 10)
        page = request.GET.get('page')
        try:
            files_lines = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            files_lines = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            files_lines = paginator.page(paginator.num_pages)

        add_breadcrumbs(request, ticket, '#')

        return render(request, 'tickets/view.html', {'layout': 'horizontal', 'ticket': tic, 'form': form, 'close': close, 'reassign': reassign, 'files': files_lines, 'comments': comments, 'participants': participants, 'close_allowed': close_allowed})

    elif mode == 'history':
        history = tickets_history.objects.filter(ticket=ticket)
        return render(request, 'tickets/history.html', {'layout': 'horizontal', 'ticket': tic, 'history': history})

    elif mode == 'reopen':
        if tic.closed:
            tic.closed = False
            tic.state = get_flow_start()
            tic.resolution = None
            tic.close_date = None
            tic.save(user=request.user)

            com = tickets_comments()
            com.comment = _('ticket reopend - resolution deleted')
            com.ticket_id = ticket
            com.action = 2
            com.save(user=request.user)

            check_references(request, com)

            touch_ticket(request.user, ticket)

            add_history(request, tic, 2, None)

            mail_comment(request, com.pk)

        return HttpResponseRedirect('/tickets/view/%s/' % ticket)

    elif mode == 'reassign':
        if not tic.closed:
            if 'assigned' in request.POST:
                if request.POST['assigned'] and int(request.POST['assigned']) > 0:
                    old_assigned_user = tic.assigned
                    old_state = tic.state

                    tic.assigned_id = request.POST['assigned']
                    tic.state = ticket_flow.objects.get(pk=request.POST['state'])
                    tic.save(user=request.user)

                    newUser = User.objects.get(pk=request.POST['assigned'])

                    com = tickets_comments()
                    com.comment = _('ticket reassigned to %(user)s\nstate now: %(state)s\n\n%(comment)s') % {'user': newUser, 'comment': request.POST.get('reassign_comment', ''), 'state': tic.state}
                    com.ticket_id = ticket
                    com.action = 7
                    com.save(user=request.user)

                    check_references(request, com)

                    touch_ticket(request.user, ticket)
                    if request.POST['assigned']:
                        touch_ticket(newUser, ticket)

                    history_data = {
                                    'old': {'comment': '', 'assigned': str(old_assigned_user), 'state': str(old_state)},
                                    'new': {'comment': request.POST.get('reassign_comment', ''), 'assigned': str(User.objects.get(pk=request.POST['assigned'])), 'state': str(tic.state)}
                                    }
                    add_history(request, tic, 7, history_data)

                    mail_comment(request, com.pk)
                else:
                    messages.add_message(request, messages.ERROR, _('missing assigned user'))

        return HttpResponseRedirect('/tickets/view/%s/' % ticket)

    elif mode == 'edit':
        excludes = ['resolution']
        if request.method == 'POST':
            form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id)
            if form.is_valid():
                tic = form.save()

                assigned = form.cleaned_data.get('assigned')
                if assigned:
                    touch_ticket(assigned, tic.pk)

                remember_changes(request, form, tic)

                touch_ticket(request.user, tic.pk)

                mail_ticket(request, tic.pk, form)

                return HttpResponseRedirect('/tickets/view/%s/' % ticket)

        else:
            form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id)
        if 'state' in form.fields:
            form.fields['state'].queryset = form.fields['state'].queryset.exclude(type=2)
        return render(request, 'tickets/edit.html', {'ticket': tic, 'layout': 'horizontal', 'form': form})

    elif mode == 'download':
        fileid = request.GET.get('file', -1)
        file_data = tickets_files.objects.get(id=fileid, ticket=ticket)
        src = '%s%s.dat' % (settings.FILE_UPLOAD_PATH, fileid)

        if request.GET.get('resize', 'no') == 'yes' and 'image' in file_data.content_type:
            img = resize_image('%s' % (src), (200, 150), 75)
            output = io.BytesIO()
            img.save(output, 'PNG')
            output.seek(0)
            response = StreamingHttpResponse(output, content_type=smart_str(file_data.content_type))

        else:
            response = StreamingHttpResponse(open('%s' % (src), "rb"), content_type=smart_str(file_data.content_type))
        response['Content-Disposition'] = 'attachment;filename=%s' % smart_str(file_data.name)
        return response

    elif mode == 'upload':
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                f = tickets_files()
                f.name = request.FILES['file'].name
                f.size = request.FILES['file'].size
                f.content_type = request.FILES['file'].content_type
                f.ticket_id = ticket
                f.public = True
                f.save(user=request.user)

                touch_ticket(request.user, ticket)

                add_history(request, tic, 5, request.FILES['file'].name)

                mail_file(request, f.pk)

                dest = settings.FILE_UPLOAD_PATH
                if not os.path.exists(dest):
                    os.makedirs(dest)

                with open('%s%s.dat' % (dest, f.id), 'wb+') as destination:
                    for chunk in request.FILES['file'].chunks():
                        destination.write(chunk)

                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)
        else:
            form = UploadFileForm()

        return render(request, 'tickets/file.html', {'ticketid': ticket, 'layout': 'horizontal', 'form': form})

def table(request, **kwargs):
    search_params = {}
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    tic = apps.get_model(mod_path, cls_name).objects.select_related('type').all()

    if not request.user.is_staff:
        tic = tic.filter(customer=request.organisation)

    if 'search' in kwargs:
        is_search = True
        params = kwargs['search']

        if not request.user.is_staff:
            used_fields = []
            for ele in settings.TICKET_SEARCH_FIELDS:
                if ele not in settings.TICKET_NON_PUBLIC_FIELDS:
                    used_fields.append(ele)
        else:
            used_fields = settings.TICKET_SEARCH_FIELDS

        fulltext = {}
        for field in params:
            if field == 'fulltext':
                if field in used_fields and get_ticket_model()._meta.get_field(field).get_internal_type() == 'CharField':
                    fulltext['%s__icontains' % field] = params[field]

            else:
                if params[field] is not None and params[field] != '':
                    if get_ticket_model()._meta.get_field(field).get_internal_type() == 'CharField':
                        search_params['%s__icontains' % field] = params[field]
                    else:
                        search_params[field] = params[field]

        tic = tic.filter(**search_params)
    else:
        tic = tic.filter(closed=False)
        is_search = False

    pretty = prettyValues(search_params)
    list_caption = kwargs.get('list_caption')
    if 'report' in request.GET:
        list_caption = tickets_reports.objects.get(pk=request.GET['report']).name

    paginator = Paginator(tic, 20)
    page = request.GET.get('page')
    try:
        tic_lines = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tic_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tic_lines = paginator.page(paginator.num_pages)

    board_form = AddToBordForm()
    board_form.fields['board'].queryset = board_form.fields['board'].queryset.filter(c_user=request.user)

    return render(request, 'tickets/list.html', {'lines': tic_lines, 'is_search': is_search, 'pretty': pretty, 'list_caption': list_caption, 'board_form': board_form})

def search(request):
    searchable_fields = settings.TICKET_SEARCH_FIELDS

    if request.method == 'POST' and 'reportname' in request.POST and request.POST['reportname']:
        rep = tickets_reports()
        rep.name = request.POST['reportname']
        rep.search = json.dumps(request.session['last_search'], cls=DjangoJSONEncoder)
        rep.save(user=request.user)

        request.session['last_search'] = clean_search_values(request.session['last_search'])
        request.session['last_search_caption'] = request.POST['reportname']

        return table(request, search=request.session['last_search'], list_caption=request.session['last_search_caption'])

    if request.method == 'POST':
        form = SearchForm(request.POST, include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
        form.is_valid()
        request.session['last_search'] = clean_search_values(form.cleaned_data)
        request.session['last_search_caption'] = ''

        return table(request, search=request.session['last_search'])

    if 'last_search' in request.session and 'new' not in request.GET:
        return table(request, search=request.session['last_search'], list_caption=request.session.get('last_search_caption', ''))

    form = SearchForm(include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)

    return render(request, 'tickets/search.html', {'layout': 'horizontal', 'form': form})

def reports(request):
    if 'report' in request.GET:
        rep = tickets_reports.objects.get(pk=request.GET['report'])
        add_breadcrumbs(request, request.GET['report'], '@')
        request.session['last_search'] = json.loads(rep.search)
        return HttpResponseRedirect('/tickets/search/?report=%s' % request.GET['report'])

    if 'delReport' in request.GET:
        tickets_reports.objects.filter(c_user=request.user, pk=request.GET['delReport']).delete()
        return HttpResponseRedirect('/reports/')

    reps = tickets_reports.objects.filter(c_user=request.user).order_by('name')

    paginator = Paginator(reps, 10)
    page = request.GET.get('page')
    try:
        rep_lines = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        rep_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        rep_lines = paginator.page(paginator.num_pages)

    return render(request, 'tickets/reports.html', {'lines': rep_lines})

def workflow(request):
    if request.method == 'POST':
        if 'method' in request.POST:
            this = int(request.POST['next'].replace('flw', ''))
            now = int(request.POST['now'].replace('flw', ''))
            if request.POST['method'] == 'add':
                try:
                    ticket_flow_edges.objects.get(now=now, next=this)
                except:
                    ticket_flow_edges(now_id=now, next_id=this).save(user=request.user)
                return HttpResponse('OK')

            elif request.POST['method'] == 'del':
                ticket_flow_edges.objects.filter(now=now, next=this).delete()
                return HttpResponse('OK')

    flows = ticket_flow.objects.all()
    edges = ticket_flow_edges.objects.all()
    nodes = {}

    offset_x = 30
    offset_y = 30

    min_x = 0
    min_y = 0
    max_x = 0
    max_y = 0

    g = graph.create()

    for flow in flows:
        g.add_node('flw%s' % flow.pk)

    for edge in edges:
        g.add_edge('flw%s' % edge.now_id, 'flw%s' % edge.next_id)
    g.solve()

    for id in g:
        # print '%s => %s,%s' % (id, g[id].x, g[id].y)
        nodes[id] = (g[id].x, g[id].y)
        min_x = min(min_x, g[id].x)
        min_y = min(min_y, g[id].y)
        max_x = max(max_x, g[id].x)
        max_y = max(max_y, g[id].y)

    if min_x < 0:
        min_x = min_x * (-1)
    if min_y < 0:
        min_y = min_y * (-1)

    for node in nodes:
        (x, y) = nodes[node]
        nodes[node] = (x + min_x + offset_x, y + min_y + offset_y)

    max_x = max_x + min_x + (offset_x * 2)
    max_y = max_y + min_y + (offset_y * 2)

    return render(request, 'tickets/workflow.html', {'layout': 'horizontal', 'flows': flows, 'edges': edges, 'nodes': nodes, 'width': max_x, 'height': max_y})
