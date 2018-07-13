'''
Creates a template tag that can handle `restructured text`_ (reST)

.. _restructured text: http://docutils.sourceforge.net/rst.html

'''

import logging
from django import template
from django.utils.safestring import mark_safe
from django.conf import settings

logger = logging.getLogger('rpc4django')

RESTRICT_REST = getattr(settings, 'RPC4DJANGO_RESTRICT_REST', False)

# all custom tag libraries must have this
register = template.Library()


def resttext(text):
    '''
    Returns *text* in reST format or plain text if resttext fails
    to import docutils or fails for any other reason

    If :envvar:`RPC4DJANGO_RESTRICT_REST` is ``True``, just return *text*
    '''

    overrides = {
        'inital_header_level': 3,
        'report_level': 5,   # 0 reports everything, 5 reports nothing
    }

    if RESTRICT_REST:
        return text

    try:
        from docutils.core import publish_parts
        parts = publish_parts(source=text, writer_name='html',
                              settings_overrides=overrides)
        return mark_safe(parts['fragment'])
    except ImportError:
        return text
    except Exception as ex1:
        # see Django Bug #6681
        logger.fatal(repr(ex1))
        return text


resttext.is_safe = True
register.filter('resttext', resttext)
