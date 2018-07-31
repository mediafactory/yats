# -*- coding: utf-8 -*-
from django.forms import ChoiceField, FileField
from django.conf import settings

from django import template
register = template.Library()

@register.filter(name='field_value')
def field_value(field):
    """
    Returns the value for this BoundField, as rendered in widgets.
    """
    if field.form.is_bound:
        if isinstance(field.field, FileField) and field.data is None:
            val = field.form.initial.get(field.name, field.field.initial)
        else:
            val = field.data
    else:
        val = field.form.initial.get(field.name, field.field.initial)
        if callable(val):
            val = val()
    if val is None:
        val = ''
    return val

@register.filter(name='display_value')
def display_value(field):
    """
    Returns the displayed value for this BoundField, as rendered in widgets.
    """
    value = field_value(field)
    if isinstance(field.field, ChoiceField):
        for (val, desc) in field.field.choices:
            if val == value:
                return desc
    return value

@register.filter(name='field_is_public')
def field_is_public(field):
    return not field.label.lower().replace(' ', '_') in settings.TICKET_NON_PUBLIC_FIELDS
