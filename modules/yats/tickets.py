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
from yats.forms import TicketsForm, CommentForm, UploadFileForm, SearchForm
from yats.models import tickets_files, tickets_comments, tickets_reports
from yats.shortcuts import resize_image, touch_ticket, mail_ticket, mail_comment, mail_file
import os
import io
try:
    import json
except ImportError:
    from django.utils import simplejson as json

def new(request):
    excludes = ['resolution']
    
    if request.method == 'POST':
        form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user)
        if form.is_valid():
            tic = form.save()

            assigned = form.cleaned_data.get('assigned')
            if assigned:
                touch_ticket(assigned, tic.pk)
            
            touch_ticket(request.user, tic.pk)
            
            mail_ticket(request, tic.pk, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            
            if form.cleaned_data.get('file_addition', False):
                return HttpResponseRedirect('/tickets/upload/%s/' % tic.pk)
            else:
                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)
    
    else:
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user)
    
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
                com.save(user=request.user)
                
                touch_ticket(request.user, ticket)
                
                mail_comment(request, com.pk)

            else:
                messages.add_message(request, messages.ERROR, _('comment invalid'))
        
        excludes = []        
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic)
        
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
        
        comments = tickets_comments.objects.select_related('c_user').filter(ticket=ticket)
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

        return render_to_response('tickets/view.html', {'layout': 'horizontal', 'ticket': tic, 'form': form, 'files': files_lines, 'comments': comments_lines}, RequestContext(request))

    elif mode == 'edit':
        excludes = ['resolution']
        if request.method == 'POST':
            form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic)
            if form.is_valid():
                tic = form.save()
                
                assigned = form.cleaned_data.get('assigned')
                if assigned:
                    touch_ticket(assigned, tic.pk)
                    
                touch_ticket(request.user, tic.pk)
                
                mail_ticket(request, tic.pk)
                
                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)
        
        else:
            form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic)
        
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
        is_search = False

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

    return render_to_response('tickets/list.html', {'lines': tic_lines, 'is_search': is_search}, RequestContext(request))

def search(request):
    searchable_fields = ['c_user', 'priority', 'type', 'component', 'deadline', 'billing_needed']
    
    if request.method == 'POST' and 'reportname' in request.POST and request.POST['reportname']:
        rep = tickets_reports()
        rep.name = request.POST['reportname']
        rep.search = json.dumps(request.session['last_search'])
        rep.save(user=request.user)
    
    if request.session.get('last_search') and not 'new' in request.GET:
        return table(request, search=request.session['last_search'])
    
    if request.method == 'POST':
        form = SearchForm(request.POST, include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user)
        form.is_valid()
        request.session['last_search'] = form.cleaned_data
        
        return table(request, search=form.cleaned_data)
    else:
        form = SearchForm(include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user)
    
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