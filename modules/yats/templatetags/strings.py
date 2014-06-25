from django import template
from django.utils.translation import ugettext as _
from yats.diff import generate_patch_html

import re
try:
    import json
except ImportError:
    from django.utils import simplejson as json
    
register = template.Library()

def contains(value, search):
    if not value or not search:
        return False
    return search in value
register.filter('contains', contains)

def numberToTicketURL(value):
    return re.sub('#([0-9]+)', r'<a href="/tickets/view/\1/">#\1</a>', value)
register.filter('numberToTicketURL', numberToTicketURL)

class Diffs(template.Node):
    def __init__(self, line):
        self.line = line
        
    def render(self, context):
        line = context.get(self.line)
        result = {}
        old = json.loads(line.old)
        new = json.loads(line.new)
        
        for ele in old:
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