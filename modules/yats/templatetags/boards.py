# -*- coding: utf-8 -*-
from django import template
from yats.models import boards

register = template.Library()

@register.simple_tag(takes_context=True)
def lookup_seen(context, seen, ticket):
    if seen:
        if ticket.pk in seen:
            result = 1 if not seen[ticket.pk] else 2
        else:
            result = 0
        context['seen'] = result
    return ''

@register.simple_tag(takes_context=True)
def board_list(context):
    user = context['user']

    if user.is_authenticated():
        context['boards'] = boards.objects.filter(c_user=user, active_record=True)
    else:
        context['boards'] = []
    return ''

@register.filter
def multiply(value, arg):
    return value*arg
