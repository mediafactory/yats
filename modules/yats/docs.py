# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http.response import HttpResponseRedirect, StreamingHttpResponse, HttpResponse
from django.shortcuts import render
from django.utils.encoding import smart_str
from django.contrib import messages
from django.utils.translation import ugettext as _
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import get_object_or_404
from yats.models import docs, docs_files, tickets_comments
from yats.forms import DocsForm, UploadFileForm
from yats.shortcuts import resize_image, add_breadcrumbs, get_ticket_model, convertPDFtoImg, convertOfficeTpPDF, isPreviewable
import re
import os
import io

def docs_search(request):
    documents = docs.objects.all()

    paginator = Paginator(documents, 20)
    page = request.GET.get('page')
    try:
        docs_lines = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        docs_lines = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        docs_lines = paginator.page(paginator.num_pages)

    return render(request, 'docs/list.html', {'lines': docs_lines})

def get_doc_files_folder():
    return os.path.join(settings.FILE_UPLOAD_PATH, 'docs/')

def docs_new(request):
    if request.method == 'POST':
        form = DocsForm(request.POST, user=request.user)
        if form.is_valid():
            doc = form.save()
            return HttpResponseRedirect('/docs/view/%s/' % doc.pk)

    else:
        form = DocsForm(user=request.user)
    return render(request, 'docs/new.html', {'layout': 'horizontal', 'form': form})

@login_required
def docs_action(request, mode, docid):
    doc = docs.objects.get(pk=docid)
    if mode == 'view':
        form = DocsForm(user=request.user, instance=doc, view_only=True)
        add_breadcrumbs(request, docid, '*', caption=doc.caption[:20])

        files = docs_files.objects.filter(doc=doc, active_record=True)
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

        return render(request, 'docs/view.html', {'layout': 'horizontal', 'form': form, 'doc': doc, 'files': files_lines})

    elif mode == 'edit':
        if request.method == 'POST':
            form = DocsForm(request.POST, user=request.user, instance=doc)
            if form.is_valid():
                doc = form.save()
                return HttpResponseRedirect('/docs/view/%s/' % doc.pk)

        form = DocsForm(user=request.user, instance=doc)
        return render(request, 'docs/edit.html', {'layout': 'horizontal', 'form': form, 'doc': doc})

    elif mode == 'delete':
        doc.delete(user=request.user)
        return HttpResponseRedirect('/search/?q=%s&models=yats.docs&models=web.test' % request.session.get('last_fulltextsearch', '*'))

    elif mode == 'ticket':
        ticket = get_ticket_model()
        tic = ticket()
        tic.caption = doc.caption
        tic.description = doc.text
        if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER') and settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER:
            if settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER == -1:
                tic.customer = request.organisation
            else:
                tic.customer_id = settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOME
        if not tic.component_id and hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT') and settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT:
            tic.component_id = settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT
        tic.save(user=request.user)

        # add ref to doc
        com = tickets_comments()
        com.comment = _(u'see §%s') % docid
        com.ticket_id = tic.pk
        com.action = 3
        com.save(user=request.user)

        add_breadcrumbs(request, str(tic.pk), '#', caption=tic.caption[:20])

        if hasattr(settings, 'KEEP_IT_SIMPLE') and settings.KEEP_IT_SIMPLE:
            return HttpResponseRedirect('/tickets/simple/%s/' % tic.pk)
        else:
            return HttpResponseRedirect('/tickets/edit/%s/' % tic.pk)

    elif mode == 'download':
        fileid = request.GET.get('file', -1)
        file_data = docs_files.objects.get(id=fileid, doc=doc)
        src = '%s%s.dat' % (get_doc_files_folder(), fileid)
        content_type = file_data.content_type
        if request.GET.get('preview') == 'yes' and os.path.isfile('%s%s.preview' % (get_doc_files_folder(), fileid)):
            src = '%s%s.preview' % (get_doc_files_folder(), fileid)
            content_type = 'imgae/png'

        if request.GET.get('resize', 'no') == 'yes' and ('image' in file_data.content_type or 'pdf' in file_data.content_type):
            img = resize_image('%s' % (src), (200, 150), 75)
            output = io.BytesIO()
            img.save(output, 'PNG')
            output.seek(0)
            response = StreamingHttpResponse(output, content_type='image/png')

        else:
            response = StreamingHttpResponse(open('%s' % (src), "rb"), content_type=content_type)

        if 'noDisposition' not in request.GET:
            if request.GET.get('preview') == 'yes' and os.path.isfile('%s%s.preview' % (get_doc_files_folder(), fileid)):
                response['Content-Disposition'] = 'attachment;filename=%s' % content_type
            else:
                response['Content-Disposition'] = 'attachment;filename=%s' % smart_str(file_data.name)
        return response

    elif mode == 'upload':
        if request.method == 'POST':
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                if docs_files.objects.filter(active_record=True, doc=doc, checksum=request.FILES['file'].hash).count() > 0:
                    messages.add_message(request, messages.ERROR, _('File already exists: %s') % request.FILES['file'].name)
                    if request.GET.get('Ajax') == '1':
                        return HttpResponse('OK')
                    return HttpResponseRedirect('/docs/view/%s/' % doc.id)
                f = docs_files()
                f.name = request.FILES['file'].name
                f.size = request.FILES['file'].size
                f.checksum = request.FILES['file'].hash
                f.content_type = request.FILES['file'].content_type
                f.doc_id = doc.id
                f.public = True
                f.save(user=request.user)

                # add_history(request, tic, 5, request.FILES['file'].name)

                dest = get_doc_files_folder()
                if not os.path.exists(dest):
                    os.makedirs(dest)

                with open('%s%s.dat' % (dest, f.id), 'wb+') as destination:
                    for chunk in request.FILES['file'].chunks():
                        destination.write(chunk)

                if 'pdf' in f.content_type:
                    convertPDFtoImg('%s/%s.dat' % (dest, f.id), '%s/%s.preview' % (dest, f.id))
                else:
                    if 'image' not in f.content_type and isPreviewable(f.content_type):
                        tmp = convertOfficeTpPDF('%s/%s.dat' % (dest, f.id))
                        convertPDFtoImg(tmp, '%s/%s.preview' % (dest, f.id))
                        if os.path.isfile(tmp):
                            os.unlink(tmp)

                return HttpResponseRedirect('/docs/view/%s/' % doc.pk)

            else:
                msg = unicode(form.errors['file'])
                msg = re.sub('<[^<]+?>', '', msg)
                messages.add_message(request, messages.ERROR, msg)
                if request.GET.get('Ajax') == '1':
                    return HttpResponse('OK')
                return HttpResponseRedirect('/docs/view/%s/' % doc.pk)

        else:
            form = UploadFileForm()

        return render(request, 'docs/file.html', {'docid': doc, 'layout': 'horizontal', 'form': form})

    elif mode == 'delfile':
        file = docs_files.objects.get(pk=request.GET['fileid'], doc=doc)
        file.delete(user=request.user)

        # add_history(request, tic, 8, file.name)

        return HttpResponseRedirect('/docs/view/%s/#files' % doc.pk)

def docs_wiki(request, wiki):
    doc = get_object_or_404(docs, wiki=wiki)
    return HttpResponseRedirect('/docs/view/%s/' % doc.pk)
