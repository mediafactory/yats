from django.template import Library

register = Library()

def contains(value, search):
    if not value or not search:
        return False
    return search in value
register.filter('contains', contains)