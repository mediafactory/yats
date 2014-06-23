from django.db.models import get_model
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.translation import ugettext as _
from yats.models import tickets_participants, tickets_comments, tickets_files

from PIL import Image#, ImageOps
import sys
import datetime
import re

def resize_image(filename, size=(200, 150), dpi=75):
    image = Image.open(filename)
    pw = image.size[0]
    ph = image.size[1]
    nw = size[0]
    nh = size[1]

    # icon generell too small or equal
    if (pw < nw and ph < nh) or (pw == nw and ph == nh):
        if image.format.lower() == 'jpg' or image.format.lower() == 'jpeg':
            return image
                     
    else:
        pr = float(pw) / float(ph)
        nr = float(nw) / float(nh)
        
        if pr > nr:
            # icon aspect is wider than destination ratio
            tw = int(round(nh * pr))
            image = image.resize((tw, nh), Image.ANTIALIAS)
            l = int(round(( tw - nw ) / 2.0))
            image = image.crop((l, 0, l + nw, nh))
        elif pr < nr:
            # icon aspect is taller than destination ratio
            th = int(round(nw / pr))
            image = image.resize((nw, th), Image.ANTIALIAS)
            t = int(round(( th - nh ) / 2.0))
            image = image.crop((0, t, nw, t + nh))
        else:
            # icon aspect matches the destination ratio
            image = image.resize(size, Image.ANTIALIAS)
            
    if image.mode != "RGB":
        # http://packages.debian.org/search?keywords=python-imaging
        # if thumb_image.mode == "CMYK":
        #    thumb_image = ImageOps.invert(thumb_image)
        image = image.convert('RGB')
    return image

def get_ticket_model():
    mod_path, cls_name = settings.TICKET_CLASS.rsplit('.', 1)
    mod_path = mod_path.split('.').pop(0)
    return get_model(mod_path, cls_name)

def touch_ticket(user, ticket_id):
    tickets_participants.objects.get_or_create(ticket_id=ticket_id, user=user)
    
def get_recipient_list(request, ticket_id):
    result = []
    error = []
    rcpts = tickets_participants.objects.select_related('user').filter(ticket=ticket_id)
    for rcpt in rcpts:
        if rcpt.user.email:
            result.append(rcpt.user.email)
        else:
            error.append(unicode(rcpt.user))
    if len(error) > 0:
        messages.add_message(request, messages.ERROR, _('the following participants could not be reached by mail (address missing): %s') % ', '.join(error))
    return result
    
def get_ticket_url(request, ticket_id):
    if request.is_secure():
        return 'https://%s/tickets/view/%s/' % (request.get_host(), ticket_id)
    else:
        return 'http://%s/tickets/view/%s/' % (request.get_host(), ticket_id)

def mail_ticket(request, ticket_id, **kwargs):
    rcpt = list(get_recipient_list(request, ticket_id))
    if 'rcpt' in kwargs and kwargs['rcpt']:
        rcpt.append(kwargs['rcpt'])
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)

    try:    
        send_mail('%s#%s - %s' % (settings.EMAIL_SUBJECT_PREFIX, tic.id, tic.caption), '%s\n\n%s' % (tic.description, get_ticket_url(request, ticket_id)), settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])  
        
def mail_comment(request, comment_id):
    com = tickets_comments.objects.get(pk=comment_id)
    ticket_id = com.ticket_id
    rcpt = get_recipient_list(request, ticket_id)
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)
    
    try:    
        send_mail('%s#%s: %s - %s' % (settings.EMAIL_SUBJECT_PREFIX, tic.id, _('new comment'), tic.caption), '%s\n\n%s' % (com.comment, get_ticket_url(request, ticket_id)), settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])        

def mail_file(request, file_id):
    io = tickets_files.objects.get(pk=file_id)
    ticket_id = io.ticket_id
    rcpt = get_recipient_list(request, ticket_id)
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)
    body = '%s\n%s: %s\n%s: %s\n%s: %s\n\n%s' % (_('new file added'), _('file name'), io.name, _('file size'), io.size, _('content type'), io.content_type, get_ticket_url(request, ticket_id))

    try:    
        send_mail('%s#%s: %s - %s' % (settings.EMAIL_SUBJECT_PREFIX, tic.id, _('new file'), tic.caption), body, settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])
        
def clean_search_values(search):
    result = {}
    for ele in search:
        if type(search[ele]) not in [bool, int, str, unicode, long, None, datetime.date]:
            if search[ele]:
                result[ele] = search[ele].pk
        else:
            result[ele] = search[ele]
    return result         

def check_references(request, src_com):
    refs = re.findall('#([0-9]+)', src_com.comment) 
    for ref in refs:
        com = tickets_comments()
        com.comment = _('ticket mentioned by #%s' % src_com.ticket_id)
        com.ticket_id = ref
        com.action = 3
        com.save(user=request.user)
        
        touch_ticket(request.user, ref)
        
        #mail_comment(request, com.pk)
    