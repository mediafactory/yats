# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from django.utils.translation import gettext as _
from django.forms.utils import pretty_name
from yats.diff import generate_patch_html
from yats.shortcuts import has_public_fields, non_previewable_contenttypes
from markdownx.utils import markdownify

import os
import re
try:
    import json
except ImportError:
    from django.utils import simplejson as json

register = template.Library()

@register.filter
def markdown2html(md):
    return markdownify(md)

@register.filter
def hasPreview(mime):
    if not mime:
        return False

    for non in non_previewable_contenttypes:
        if non in mime:
            return False
    return True

@register.filter
def hasPreviewFile(fileid, type):
    if type == 'doc':
        return os.path.isfile('%sdocs/%s.preview' % (settings.FILE_UPLOAD_PATH, fileid))
    else:
        return os.path.isfile('%s%s.preview' % (settings.FILE_UPLOAD_PATH, fileid))

@register.filter
def prettify(value):
    return pretty_name(value)

@register.filter
def contains(value, search):
    if not value or not search:
        return False
    return search in value

@register.filter
def numberToTicketURL(value):
    # https://regex101.com/r/fC1wX4/10
    value = re.sub(u'(?<!&)§([0-9]+)', r'<a href="/docs/view/\1/">§\1</a>', value)
    return re.sub(u'(?<!&)#([0-9]+)', r'<a href="/tickets/view/\1/">#\1</a>', value)

@register.filter
def buildToDoList(value):
    class local:
        counter = 0

    def render_item(match):
        local.counter += 1
        state = match.groups()
        checked = ' checked' if state[0].strip() else ''
        return '<input type="checkbox" value="%s" %s/>' % (local.counter, checked)

    return re.sub('\[([ Xx])\]', render_item, value)

class Diffs(template.Node):
    def __init__(self, line):
        self.line = line

    def render(self, context):
        line = context.get(self.line)
        user = context.get('request').user

        result = {}
        old = json.loads(line.old)
        new = json.loads(line.new)

        if not has_public_fields(old) and not user.is_staff:
            context['elements'] = []
            return ''

        for ele in old:
            if not user.is_staff and ele in settings.TICKET_NON_PUBLIC_FIELDS:
                continue

            if new[ele] == 'None':
                new[ele] = _('unknown')
            if old[ele] == 'None':
                old[ele] = _('unknown')

            if new[ele] == 'True':
                new[ele] = _('yes')
            if old[ele] == 'True':
                old[ele] = _('yes')

            if new[ele] == 'False':
                new[ele] = _('no')
            if old[ele] == 'False':
                old[ele] = _('no')

            result[ele] = generate_patch_html(old[ele], new[ele], ele, 'semantic')

        context['elements'] = result
        return ''

def do_diff(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, line = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    return Diffs(line)

register.tag('diff', do_diff)
