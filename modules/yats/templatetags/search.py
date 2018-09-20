# -*- coding: utf-8 -*-
from django import template

register = template.Library()

@register.filter
def cut_text_for_xapian(text):
    text = text.replace(';', ' ').replace(',', ' ').replace('"', '')
    content = []
    for word in text.split(' '):
        if len(word) <= 245:
            content.append(word)
    return ' '.join(content)
