from django.template import Library

register = Library()

def comment_color(value):
    result = {
      0: lambda : 'info',
      1: lambda : 'danger',
      2: lambda : 'success',
      3: lambda : 'inverse',
    }[value]()
    return result

register.filter('comment_color', comment_color)
