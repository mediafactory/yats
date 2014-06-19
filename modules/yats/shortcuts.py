from django.db.models import get_model
from django.conf import settings
from django.core.mail import send_mail
from django.contrib import messages
from django.utils.translation import ugettext as _
from yats.models import tickets_participants, tickets_comments, tickets_files

from PIL import Image#, ImageOps
import sys
import datetime

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
    
def get_recipient_list(ticket_id):
    return tickets_participants.objects.select_related('user').filter(ticket=ticket_id).exclude(user__email=None).exclude(user__email='').values_list('user__email', flat=True)
    
def get_ticket_url(request, ticket_id):
    if request.is_secure():
        return 'https://%s/tickets/view/%s/' % (request.get_host(), ticket_id)
    else:
        return 'http://%s/tickets/view/%s/' % (request.get_host(), ticket_id)

def mail_ticket(request, ticket_id, **kwargs):
    rcpt = list(get_recipient_list(ticket_id))
    if 'rcpt' in kwargs and kwargs['rcpt']:
        rcpt.append(kwargs['rcpt'])
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)

    try:    
        send_mail('#%s - %s' % (tic.id, tic.caption), '%s\n\n%s' % (tic.description, get_ticket_url(request, ticket_id)), settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])  
        
def mail_comment(request, comment_id):
    com = tickets_comments.objects.get(pk=comment_id)
    ticket_id = com.ticket_id
    rcpt = get_recipient_list(ticket_id)
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)
    
    try:    
        send_mail('#%s: %s - %s' % (tic.id, _('new comment'), tic.caption), '%s\n\n%s' % (com.comment, get_ticket_url(request, ticket_id)), settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])        

def mail_file(request, file_id):
    io = tickets_files.objects.get(pk=file_id)
    ticket_id = io.ticket_id
    rcpt = get_recipient_list(ticket_id)
    if len(rcpt) == 0:
        return
    tic = get_ticket_model().objects.get(pk=ticket_id)
    body = '%s\n%s: %s\n%s: %s\n%s: %s\n\n%s' % (_('new file added'), _('file name'), io.name, _('file size'), io.size, _('content type'), io.content_type, get_ticket_url(request, ticket_id))

    try:    
        send_mail('#%s: %s - %s' % (tic.id, _('new file'), tic.caption), body, settings.SERVER_EMAIL, rcpt, False)
    except:
        messages.add_message(request, messages.ERROR, _('mail not send: %s') % sys.exc_info()[1])
        
def clean_search_values(search):
    result = {}
    for ele in search:
        if type(search[ele]) not in [bool, int, str, unicode, long, None]:
            print type(search[ele])
            if search[ele]:
                result[ele] = search[ele].pk
    return result         