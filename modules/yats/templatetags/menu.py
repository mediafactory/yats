# -*- coding: utf-8 -*-
from django import template
from django.conf import settings
from urlparse import urlsplit, urlunsplit

register = template.Library()

@register.simple_tag()
def YATSSerch():
    if hasattr(settings, 'SSO_SERVER'):
        parts = list(urlsplit(settings.SSO_SERVER))
        parts[2] = '/tickets/search/'
        return urlunsplit(parts)
    else:
        return ''

@register.simple_tag(takes_context=True)
def SimpleSerch(context):
    if hasattr(settings, 'KEEP_IT_SIMPLE'):
        if settings.KEEP_IT_SIMPLE:
            context['simple_search'] = True
    return ''
