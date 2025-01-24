# -*- coding: utf-8 -*-
from django import template

register = template.Library()

# alternativ mir RE:
# https://stackoverflow.com/questions/30925487/xapian-search-terms-which-exceed-the-245-character-length-invalidargumenterror
@register.filter
def cut_text_for_xapian(text):
    text = text.replace(';', ' ').replace(',', ' ').replace('"', '')
    content = []
    for word in text.split(' '):
        if len(word) <= 240:
            content.append(word)
    return ' '.join(content)
