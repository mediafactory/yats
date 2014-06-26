# -*- coding: utf-8 -*- 
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.http.response import HttpResponseRedirect, StreamingHttpResponse
from django.db.models import get_model
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from yats.forms import TicketsForm, CommentForm, UploadFileForm, SearchForm, TicketCloseForm
from yats.models import tickets_files, tickets_comments, tickets_reports, ticket_resolution, tickets_participants, tickets_history
from yats.shortcuts import resize_image, touch_ticket, mail_ticket, mail_comment, mail_file, clean_search_values, check_references, remember_changes, add_history, prettyValues
import os
import io
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
            
            touch_ticket(request.user, tic.pk)
            
            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            
            if form.cleaned_data.get('file_addition', False):
                return HttpResponseRedirect('/tickets/upload/%s/' % tic.pk)
            else:
                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)
    
    else:
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    
    return render_to_response('tickets/new.html', {'layout': 'horizontal', 'form': form}, RequestContext(request))    

def action(request, mode, ticket):
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    tic = get_model(mod_path, cls_name).objects.get(pk=ticket)

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
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id)
        close = TicketCloseForm()
        
        participants = tickets_participants.objects.select_related('user').filter(ticket=ticket)

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
        
        comments = tickets_comments.objects.select_related('c_user').filter(ticket=ticket).order_by('c_date')
        paginator = Paginator(comments, 10)
        page = request.GET.get('page')
        try:
            comments_lines = paginator.page(page)
        except PageNotAnInteger:
            # If page is not an integer, deliver first page.
            comments_lines = paginator.page(1)
        except EmptyPage:
            # If page is out of range (e.g. 9999), deliver last page of results.
            comments_lines = paginator.page(paginator.num_pages)

        breadcrumbs = request.session.get('breadcrumbs', [])
        # ignore dupplicates at the end of list
        if len(breadcrumbs) > 0:
            if breadcrumbs[-1] != long(ticket):
                breadcrumbs.append(long(ticket))
        else:
            breadcrumbs.append(long(ticket))
        while len(breadcrumbs) > 10:
            breadcrumbs.pop(0)
        request.session['breadcrumbs'] = breadcrumbs
        
        return render_to_response('tickets/view.html', {'layout': 'horizontal', 'ticket': tic, 'form': form, 'close': close, 'files': files_lines, 'comments': comments_lines, 'participants': participants}, RequestContext(request))

    elif mode == 'history':
        history = tickets_history.objects.filter(ticket=ticket)
        return render_to_response('tickets/history.html', {'layout': 'horizontal', 'ticket': tic, 'history': history}, RequestContext(request))

    elif mode == 'reopen':
        if tic.closed:
            tic.closed = False
            tic.resolution = None
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
        
        return render_to_response('tickets/edit.html', {'ticket': tic, 'layout': 'horizontal', 'form': form}, RequestContext(request))    

    elif mode == 'download':
        fileid = request.GET.get('file', -1)
        file_data = tickets_files.objects.get(id=fileid, ticket=ticket)
        src = '%s%s.dat' % (settings.FILE_UPLOAD_PATH, fileid)
        
        if request.GET.get('resize', 'no') == 'yes' and 'image' in file_data.content_type:
            img = resize_image('%s' % (src), (200, 150), 75)
            output = io.BytesIO()
            img.save(output, 'PNG')
            output.seek(0)
            response = StreamingHttpResponse(output, mimetype=smart_str(file_data.content_type))
            
        else:
            response = StreamingHttpResponse(open('%s' % (src),"rb"), mimetype=smart_str(file_data.content_type))
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
        
        return render_to_response('tickets/file.html', {'ticketid': ticket, 'layout': 'horizontal', 'form': form}, RequestContext(request))    

def table(request, **kwargs):
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    tic = get_model(mod_path, cls_name).objects.select_related('type').all()

    if not request.user.is_staff:
        tic = tic.filter(customer=request.organisation)
        
    if 'search' in kwargs:
        is_search = True

        search_params = {}
    
        params = kwargs['search']
        for field in params:
            if params[field] != None and params[field] != '':
                search_params[field] = params[field]
        tic = tic.filter(**search_params)
    else:
        tic = tic.filter(closed=False)
        is_search = False

    pretty = prettyValues(search_params)
    
    paginator = Paginator(tic, 10)
    page = request.GET.get('page')
    try:
        tic_lines = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        tic_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        tic_lines = paginator.page(paginator.num_pages)

    return render_to_response('tickets/list.html', {'lines': tic_lines, 'is_search': is_search, 'pretty': pretty}, RequestContext(request))

def search(request):
    searchable_fields = settings.TICKET_SEARCH_FIELDS
    
    if request.method == 'POST' and 'reportname' in request.POST and request.POST['reportname']:
        rep = tickets_reports()
        rep.name = request.POST['reportname']
        rep.search = json.dumps(request.session['last_search'])
        rep.save(user=request.user)
    
    if request.method == 'POST':
        form = SearchForm(request.POST, include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
        form.is_valid()
        request.session['last_search'] = clean_search_values(form.cleaned_data)
        
        return table(request, search=request.session['last_search'])

    if 'last_search' in request.session and not 'new' in request.GET:
        return table(request, search=request.session['last_search'])
    
    form = SearchForm(include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    
    return render_to_response('tickets/search.html', {'layout': 'horizontal', 'form': form}, RequestContext(request))

def reports(request):
    if 'report' in request.GET:
        rep = tickets_reports.objects.get(pk=request.GET['report'])
        return table(request, search=json.loads(rep.search))
    
    reps = tickets_reports.objects.filter(c_user=request.user)

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

    return render_to_response('tickets/reports.html', {'lines': rep_lines}, RequestContext(request))