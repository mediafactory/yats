from django import template
from yats.models import boards

register = template.Library()

@register.simple_tag(takes_context=True)
def board_list(context):
    user = context['user']

    if user.is_authenticated():
        context['boards'] = boards.objects.filter(c_user=user, active_record=True)
        context['boards'] = []
    else:
        context['boards'] = []
    return ''

@register.filter
def multiply(value, arg):
    return value*arg
