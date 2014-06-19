from django.template import Library
import re

register = Library()

def contains(value, search):
    if not value or not search:
        return False
    return search in value
register.filter('contains', contains)

def numberToTicketURL(value):
    return re.sub('#([0-9]+)', r'<a href="/tickets/view/\1/">#\1</a>', value)
register.filter('numberToTicketURL', numberToTicketURL)
