# -*- coding: utf-8 -*-
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http.response import HttpResponseRedirect, StreamingHttpResponse, HttpResponse, JsonResponse
from django.apps import apps
from django.conf import settings
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.utils.encoding import smart_str
from django.contrib.auth.models import User
from django.utils import timezone
from yats.forms import TicketsForm, CommentForm, UploadFileForm, SearchForm, TicketCloseForm, TicketReassignForm, AddToBordForm, SimpleTickets, ToDo
from yats.models import tickets_files, tickets_comments, tickets_reports, ticket_resolution, tickets_participants, tickets_history, ticket_flow_edges, ticket_flow, get_flow_start, get_flow_end, tickets_ignorants
from yats.shortcuts import resize_image, touch_ticket, mail_ticket, jabber_ticket, mail_comment, jabber_comment, mail_file, jabber_file, clean_search_values, convert_sarch, check_references, remember_changes, add_history, prettyValues, add_breadcrumbs, get_ticket_model, build_ticket_search_ext, convertPDFtoImg, convertOfficeTpPDF
import os
import io
import graph
import re
import copy
try:
    import json
except ImportError:
    from django.utils import simplejson as json

@login_required
def create(request):
    if 'isUsingYATSE' not in request.session:
        request.session['isUsingYATSE'] = True

    if hasattr(settings, 'KEEP_IT_SIMPLE') and settings.KEEP_IT_SIMPLE:
        keep_it_simple = True
    else:
        keep_it_simple = False

    if keep_it_simple:
        return HttpResponseRedirect('/tickets/simple/')
    else:
        return HttpResponseRedirect('/tickets/new/')

@login_required
def new(request):
    excludes = ['resolution']

    if request.method == 'POST':
        form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
        if form.is_valid():
            tic = form.save()
            if tic.keep_it_simple:
                tic.keep_it_simple = False
                tic.save(user=request.user)

            assigned = form.cleaned_data.get('assigned')
            if assigned:
                touch_ticket(assigned, tic.pk)

            for ele in form.changed_data:
                form.initial[ele] = ''
            remember_changes(request, form, tic)

            touch_ticket(request.user, tic.pk)

            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT)

            if form.cleaned_data.get('file_addition', False):
                return HttpResponseRedirect('/tickets/upload/%s/' % tic.pk)
            else:
                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)

    else:
        form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    form.fields['state'].queryset = form.fields['state'].queryset.exclude(type=2)

    return render(request, 'tickets/new.html', {'layout': 'horizontal', 'form': form})

@login_required
def simple(request):
    if request.method == 'POST':
        form = SimpleTickets(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            ticket = get_ticket_model()
            tic = ticket()
            tic.caption = cd['caption']
            tic.description = cd['description'].replace(u"\u00A0", " ")
            tic.priority = cd['priority']
            tic.assigned = cd['assigned']
            if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER') and settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER:
                if settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER == -1:
                    tic.customer = request.organisation
                else:
                    tic.customer_id = settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOME
            tic.component = cd['component']
            if not tic.component_id and hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT') and settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT:
                tic.component_id = settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT
            tic.deadline = cd['deadline']
            tic.save(user=request.user)

            if tic.assigned:
                touch_ticket(tic.assigned, tic.pk)

            for ele in form.changed_data:
                form.initial[ele] = ''
            remember_changes(request, form, tic)

            touch_ticket(request.user, tic.pk)

            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT)

            return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)

    else:
        if request.user.is_staff:
            initial = {'assigned': request.user.id}
        else:
            initial = {}
        form = SimpleTickets(initial=initial)
    return render(request, 'tickets/new.html', {'layout': 'horizontal', 'form': form, 'mode': 'simple'})

@login_required
def action(request, mode, ticket):
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    tic = apps.get_model(mod_path, cls_name).objects.get(pk=ticket)

    if hasattr(settings, 'KEEP_IT_SIMPLE') and settings.KEEP_IT_SIMPLE:
        keep_it_simple = True
    else:
        keep_it_simple = False

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
                jabber_comment(request, com.pk)

            else:
                if 'resolution' in request.POST:
                    if request.POST['resolution'] and int(request.POST['resolution']) > 0:
                        tic.resolution_id = request.POST['resolution']
                        tic.closed = True
                        tic.close_date = timezone.now()
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
                        jabber_comment(request, com.pk)

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

        files = tickets_files.objects.filter(ticket=ticket, active_record=True)
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

        add_breadcrumbs(request, ticket, '#', caption=tic.caption[:20])
        if 'YATSE' in request.GET and 'isUsingYATSE' not in request.session:
            request.session['isUsingYATSE'] = True

        return render(request, 'tickets/view.html', {'layout': 'horizontal', 'ticket': tic, 'form': form, 'close': close, 'reassign': reassign, 'files': files_lines, 'comments': comments, 'participants': participants, 'close_allowed': close_allowed, 'keep_it_simple': keep_it_simple})

    elif mode == 'gallery':
        images = tickets_files.objects.filter(ticket=ticket, active_record=True)
        return render(request, 'tickets/gallery.html', {'layout': 'horizontal', 'ticket': tic, 'images': images})

    elif mode == 'history':
        history = tickets_history.objects.filter(ticket=ticket)
        return render(request, 'tickets/history.html', {'layout': 'horizontal', 'ticket': tic, 'history': history, 'keep_it_simple': keep_it_simple})

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
            jabber_comment(request, com.pk)

        return HttpResponseRedirect('/tickets/view/%s/' % ticket)

    elif mode == 'move':
        if not tic.closed:
            old_state = tic.state

            tic.state = ticket_flow.objects.get(pk=request.POST['state'])
            tic.save(user=request.user)

            touch_ticket(request.user, ticket)

            oldUser = str(User.objects.get(pk=tic.assigned_id)) if tic.assigned_id else None

            history_data = {
                            'old': {'comment': '', 'assigned': oldUser, 'state': str(old_state)},
                            'new': {'comment': _('ticket moved'), 'assigned': oldUser, 'state': str(tic.state)}
                            }
            add_history(request, tic, 7, history_data)

        return HttpResponse('OK')

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

                    mail_comment(request, com.pk)
                    jabber_comment(request, com.pk)

                    history_data = {
                                    'old': {'comment': '', 'assigned': str(old_assigned_user), 'state': str(old_state)},
                                    'new': {'comment': request.POST.get('reassign_comment', ''), 'assigned': str(User.objects.get(pk=request.POST['assigned'])), 'state': str(tic.state)}
                                    }
                    add_history(request, tic, 7, history_data)

                else:
                    messages.add_message(request, messages.ERROR, _('missing assigned user'))

        return HttpResponseRedirect('/tickets/view/%s/' % ticket)

    elif mode == 'edit' or (mode == 'simple' and (not tic.keep_it_simple or tic.closed) and keep_it_simple):
        excludes = ['resolution']
        if request.method == 'POST':
            form = TicketsForm(request.POST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id)
            if form.is_valid():
                tic = form.save()

                if tic.keep_it_simple:
                    tic.keep_it_simple = False
                    tic.save(user=request.user)

                assigned = form.cleaned_data.get('assigned')
                if assigned:
                    touch_ticket(assigned, tic.pk)

                mail_ticket(request, tic.pk, form)
                jabber_ticket(request, tic.pk, form)

                remember_changes(request, form, tic)

                touch_ticket(request.user, tic.pk)

                return HttpResponseRedirect('/tickets/view/%s/' % ticket)

        else:
            form = TicketsForm(exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, instance=tic, customer=request.organisation.id)
        if 'state' in form.fields:
            form.fields['state'].queryset = form.fields['state'].queryset.exclude(type=2)
        return render(request, 'tickets/edit.html', {'ticket': tic, 'layout': 'horizontal', 'form': form})

    elif mode == 'simple':
        if request.method == 'POST':
            form = SimpleTickets(request.POST, initial={
                    'caption': tic.caption,
                    'description': tic.description,
                    'priority': tic.priority,
                    'assigned': tic.assigned
                })
            if form.is_valid():
                cd = form.cleaned_data
                tic.caption = cd['caption']
                tic.description = cd['description'].replace(u"\u00A0", " ")
                tic.priority = cd['priority']
                tic.assigned = cd['assigned']
                tic.deadline = cd['deadline']
                tic.component = cd['component']
                tic.save(user=request.user)

                if cd['assigned']:
                    touch_ticket(cd['assigned'], tic.pk)

                remember_changes(request, form, tic)

                touch_ticket(request.user, tic.pk)

                mail_ticket(request, tic.pk, form)
                jabber_ticket(request, tic.pk, form)

                return HttpResponseRedirect('/tickets/view/%s/' % ticket)

        else:
            form = SimpleTickets(initial={
                    'caption': tic.caption,
                    'description': tic.description,
                    'priority': tic.priority,
                    'assigned': tic.assigned,
                    'deadline': tic.deadline,
                    'component': tic.component,
                })
        return render(request, 'tickets/edit.html', {'ticket': tic, 'layout': 'horizontal', 'form': form, 'mode': mode})

    elif mode == 'download':
        fileid = request.GET.get('file', -1)
        file_data = tickets_files.objects.get(id=fileid, ticket=ticket)
        src = '%s%s.dat' % (settings.FILE_UPLOAD_PATH, fileid)
        content_type = file_data.content_type
        if request.GET.get('preview') == 'yes' and os.path.isfile('%s%s.preview' % (settings.FILE_UPLOAD_PATH, fileid)):
            src = '%s%s.preview' % (settings.FILE_UPLOAD_PATH, fileid)
            content_type = 'imgae/png'

        if request.GET.get('resize', 'no') == 'yes' and ('image' in file_data.content_type or 'pdf' in file_data.content_type):
            img = resize_image('%s' % (src), (200, 150), 75)
            output = io.BytesIO()
            img.save(output, 'PNG')
            output.seek(0)
            response = StreamingHttpResponse(output, content_type='image/png')

        else:
            response = StreamingHttpResponse(open('%s' % (src), "rb"), content_type=content_type)

        if request.GET.get('preview') == 'yes' and os.path.isfile('%s%s.preview' % (settings.FILE_UPLOAD_PATH, fileid)):
            response['Content-Disposition'] = 'attachment;filename=%s' % content_type
        else:
            response['Content-Disposition'] = 'attachment;filename=%s' % smart_str(file_data.name)
        return response

    elif mode == 'upload':
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                if tickets_files.objects.filter(active_record=True, ticket=ticket, checksum=request.FILES['file'].hash).count() > 0:
                    messages.add_message(request, messages.ERROR, _('File already exists: %s') % request.FILES['file'].name)
                    if request.GET.get('Ajax') == '1':
                        return HttpResponse('OK')
                    return HttpResponseRedirect('/tickets/view/%s/' % ticket)
                f = tickets_files()
                f.name = request.FILES['file'].name
                f.size = request.FILES['file'].size
                f.checksum = request.FILES['file'].hash
                f.content_type = request.FILES['file'].content_type
                f.ticket_id = ticket
                f.public = True
                f.save(user=request.user)

                touch_ticket(request.user, ticket)

                add_history(request, tic, 5, request.FILES['file'].name)

                mail_file(request, f.pk)
                jabber_file(request, f.pk)

                dest = settings.FILE_UPLOAD_PATH
                if not os.path.exists(dest):
                    os.makedirs(dest)

                with open('%s%s.dat' % (dest, f.id), 'wb+') as destination:
                    for chunk in request.FILES['file'].chunks():
                        destination.write(chunk)

                if 'pdf' in f.content_type:
                    convertPDFtoImg('%s/%s.dat' % (dest, f.id), '%s/%s.preview' % (dest, f.id))
                else:
                    if 'image' not in f.content_type:
                        tmp = convertOfficeTpPDF('%s/%s.dat' % (dest, f.id))
                        convertPDFtoImg(tmp, '%s/%s.preview' % (dest, f.id))
                        os.unlink(tmp)

                return HttpResponseRedirect('/tickets/view/%s/' % tic.pk)

            else:
                msg = unicode(form.errors['file'])
                msg = re.sub('<[^<]+?>', '', msg)
                messages.add_message(request, messages.ERROR, msg)
                if request.GET.get('Ajax') == '1':
                    return HttpResponse('OK')
                return HttpResponseRedirect('/tickets/view/%s/' % ticket)
        elif request.method == 'PUT':
            # /tickets/upload/XXX/?filename=test1.txt
            upload_handlers = request.upload_handlers
            content_type = str(request.META.get('CONTENT_TYPE', ""))
            content_length = int(request.META.get('CONTENT_LENGTH', 0))

            if content_type == "":
                return HttpResponse('missing ContentType', status=400)
            if content_length == 0:
                # both returned 0
                return HttpResponse('missing ContentLength', status=400)

            content_type = content_type.split(";")[0].strip()
            try:
                charset = content_type.split(";")[1].strip()
            except IndexError:
                charset = ""

            # we can get the file name via the path, we don't actually
            file_name = request.GET['filename']
            field_name = file_name

            counters = [0]*len(upload_handlers)

            for handler in upload_handlers:
                result = handler.handle_raw_input("", request.META, content_length, "", "")

            from django.core.files.uploadhandler import StopFutureHandlers
            for handler in upload_handlers:
                try:
                    handler.new_file(field_name, file_name,
                                     content_type, content_length, charset)
                except StopFutureHandlers:
                    break

            for i, handler in enumerate(upload_handlers):
                while True:
                    chunk = request.read(handler.chunk_size)
                    if chunk:

                        handler.receive_data_chunk(chunk, counters[i])
                        counters[i] += len(chunk)
                    else:
                        # no chunk
                        break

            for i, handler in enumerate(upload_handlers):
                file_obj = handler.file_complete(counters[i])
                if file_obj:
                    f = tickets_files()
                    f.name = file_obj.name
                    f.size = file_obj.size
                    #f.checksum = request.FILES['file'].hash
                    f.content_type = content_type
                    f.ticket_id = ticket
                    f.public = True
                    f.save(user=request.user)

                    touch_ticket(request.user, ticket)

                    add_history(request, tic, 5, file_obj.name)

                    mail_file(request, f.pk)
                    jabber_file(request, f.pk)

                    dest = settings.FILE_UPLOAD_PATH
                    if not os.path.exists(dest):
                        os.makedirs(dest)

                    with open('%s%s.dat' % (dest, f.id), 'wb+') as destination:
                        for chunk in file_obj.chunks():
                            destination.write(chunk)

                    if 'pdf' in f.content_type:
                        convertPDFtoImg('%s/%s.dat' % (dest, f.id), '%s/%s.preview' % (dest, f.id))
                    else:
                        if 'image' not in f.content_type and 'audio' not in f.content_type and not 'javascript' in f.content_type:
                            try:
                                tmp = convertOfficeTpPDF('%s/%s.dat' % (dest, f.id))
                                convertPDFtoImg(tmp, '%s/%s.preview' % (dest, f.id))
                                os.unlink(tmp)
                            except:
                                pass

                        if 'audio' in f.content_type:
                            try:
                                # https://realpython.com/python-speech-recognition/
                                import speech_recognition as sr
                                AUDIO_FILE = '%s%s.dat' % (dest, f.id)
                                r = sr.Recognizer()
                                with sr.AudioFile(AUDIO_FILE) as source:
                                    audio = r.record(source)  # read the entire audio file

                                text = r.recognize_google(audio, language='de-DE')
                                if text:
                                    com = tickets_comments()
                                    com.comment = text
                                    com.ticket_id = ticket
                                    com.action = 6
                                    com.save(user=request.user)
                            except:
                                pass

                    return HttpResponse(status=201)

                else:
                    # some indication this didn't work?
                    return HttpResponse(status=500)

        else:
            form = UploadFileForm()

        return render(request, 'tickets/file.html', {'ticketid': ticket, 'layout': 'horizontal', 'form': form})

    elif mode == 'delfile':
        file = tickets_files.objects.get(pk=request.GET['fileid'], ticket=ticket)
        file.delete(user=request.user)

        touch_ticket(request.user, ticket)

        add_history(request, tic, 8, file.name)

        return HttpResponseRedirect('/tickets/view/%s/#files' % tic.pk)

    elif mode == 'notify':
        tickets_participants.objects.filter(ticket=tic, user=request.user).update(seen=True)
        return HttpResponse('OK')

    elif mode == 'ignore':
        ig = tickets_ignorants()
        ig.ticket = tic
        ig.user=request.user
        ig.save()
        return HttpResponse('OK')

    elif mode == 'todo':
        class local:
            counter = 0

        def ToDoDone(match):
            local.counter += 1
            group = match.groups()
            if local.counter == pos:
                return u'[X]'
            else:
                return u'[%s]' % group[0]

        def ToDoUnDone(match):
            local.counter += 1
            group = match.groups()
            if local.counter == pos:
                return u'[ ]'
            else:
                return u'[%s]' % group[0]

        form = ToDo(request.POST)
        if form.is_valid():
            desc = tic.description

            cd = form.cleaned_data
            text = cd['text']
            pos = cd['item']
            set = cd['set']
            if set:
                tic.description = re.sub(r'\[([ Xx])\]', ToDoDone, desc)
                old = _('undone: %s') % text
                new = _('done: %s') % text
            else:
                tic.description = re.sub(r'\[([ Xx])\]', ToDoUnDone, desc)
                new = _('undone: %s') % text
                old = _('done: %s') % text

            tic.save(user=request.user)

            touch_ticket(request.user, ticket)

            add_history(request, tic, 9, (new, old))

            data = {
                'set': set,
                'item': pos,
                'text': text,
            }
            return JsonResponse(data, safe=False)

@login_required
def table(request, **kwargs):
    def pretty_condition(condition):
        if condition == 'AND':
            return _('AND')
        else:
            return _('OR')

    def pretty_operator(operator):
        if operator == 'is_null':
            return _('is null')
        elif operator == 'is_not_null':
            return _('is not null')
        elif operator == 'equal':
            return _('equal')
        elif operator == 'not_equal':
            return _('not equal')
        elif operator == 'begins_with':
            return _('begins with')
        elif operator == 'not_begins_with':
            return _('not begins with')
        elif operator == 'contains':
            return _('contains')
        elif operator == 'not_contains':
            return _('not contains')
        elif operator == 'ends_with':
            return _('ends with')
        elif operator == 'not_ends_with':
            return _('not ends with')
        elif operator == 'is_empty':
            return _('is empty')
        elif operator == 'is_not_empty':
            return _('is not empty')
        elif operator == 'less_or_equal':
            return _('less or equal')
        elif operator == 'less':
            return _('less')
        elif operator == 'greater_or_equal':
            return _('greater or equal')
        elif operator == 'greater':
            return _('greater')
        elif operator == 'between':
            return _('between')
        elif operator == 'not_between':
            return _('not between')

        return operator

    def pretty_value(value):
        if value is None:
            return ''
        if isinstance(value, (bool)):
            if value:
                return _('yes')
            else:
                return _('no')
        return unicode(value)

    def formatQuery(rules, condition):
        result = '('
        for rule in rules:
            if 'rules' in rule:
                result = ('%s %s %s' % (result, pretty_condition(condition), formatQuery(rule['rules'], rule['condition']))).strip()
                continue

            param = ('%s %s %s' % (rule['label'], pretty_operator(rule['operator']), pretty_value(rule['value']))).strip()
            if result != '(':
                result = '%s %s %s' % (result, pretty_condition(condition), param)
            else:
                result = ('%s%s' % (result, param)).strip()

        return '%s)' % result

    tic = get_ticket_model().objects.select_related('type').all()

    if 'search' in kwargs:
        is_search = True
        search_params, tic = build_ticket_search_ext(request, tic, kwargs['search'])

    else:
        tic = tic.filter(closed=False).order_by('-id')
        search_params = convert_sarch({'closed':False})
        is_search = False

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
    pretty_params = prettyValues(copy.deepcopy(search_params))
    pretty_query = formatQuery(pretty_params['rules'], pretty_params['condition'])
    return render(request, 'tickets/list.html', {'lines': tic_lines, 'is_search': is_search, 'search_params': pretty_params, 'list_caption': list_caption, 'board_form': board_form, 'query': json.dumps(search_params), 'sql': tic.query, 'pretty_query': pretty_query})

@login_required
def search(request):
    searchable_fields = settings.TICKET_SEARCH_FIELDS

    if request.method == 'POST' and 'reportname' in request.POST and request.POST['reportname']:
        rep = tickets_reports()
        rep.name = request.POST['reportname']
        rep.search = json.dumps(request.session['last_search'], cls=DjangoJSONEncoder)
        rep.save(user=request.user)

        request.session['last_search'] = convert_sarch(clean_search_values(request.session['last_search']))
        request.session['last_search_caption'] = request.POST['reportname']

        return table(request, search=request.session['last_search'], list_caption=request.session['last_search_caption'])

    if request.method == 'POST':
        form = SearchForm(request.POST, include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
        form.is_valid()
        request.session['last_search'] = convert_sarch(clean_search_values(form.cleaned_data))
        request.session['last_search_caption'] = ''

        return table(request, search=request.session['last_search'])

    if 'last_search' in request.session and 'new' not in request.GET:
        return table(request, search=request.session['last_search'], list_caption=request.session.get('last_search_caption', ''))

    return HttpResponseRedirect('/tickets/search/extended/')

@login_required
def search_simple(request):
    searchable_fields = settings.TICKET_SEARCH_FIELDS
    form = SearchForm(include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)

    return render(request, 'tickets/search.html', {'layout': 'horizontal', 'form': form})

@login_required
def search_ex(request):
    searchable_fields = settings.TICKET_SEARCH_FIELDS

    if request.method == 'POST':
        request.session['last_search'] = json.loads(request.POST['query'])
        return table(request, search=request.session['last_search'])

    if request.method == 'GET' and 'page' in request.GET:
        return table(request, search=request.session['last_search'])

    form = SearchForm(include_list=searchable_fields, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    return render(request, 'tickets/querybuilder.html', {'form': form})

@login_required
def reports(request):
    if 'report' in request.GET:
        rep = tickets_reports.objects.get(pk=request.GET['report'])
        add_breadcrumbs(request, request.GET['report'], '@', caption=rep.name[:20])
        request.session['last_search'] = json.loads(rep.search)
        return HttpResponseRedirect('/tickets/search/?report=%s' % request.GET['report'])

    if 'delReport' in request.GET:
        tickets_reports.objects.get(c_user=request.user, pk=request.GET['delReport']).delete(user=request.user)
        return HttpResponseRedirect('/reports/')

    reps = tickets_reports.objects.filter(active_record=True, c_user=request.user).order_by('name')

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

@login_required
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

def log(request):
    history = tickets_history.objects.filter(c_user=request.user).order_by('-c_date')

    paginator = Paginator(history, 10)
    page = request.GET.get('page')
    try:
        history_lines = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        history_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        history_lines = paginator.page(paginator.num_pages)

    return render(request, 'tickets/log.html', {'history': history_lines})
