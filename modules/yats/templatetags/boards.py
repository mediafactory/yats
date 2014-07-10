from django import template
from yats.models import boards

register = template.Library()

class board_list(template.Node):
    def render(self, context):
        user = context.get('request').user
        context['boards'] = boards.objects.filter(c_user=user, active_record=True)
        return ''
    
def do_board_list(parser, token):
    return board_list()

register.tag('board_list', do_board_list)