# -*- coding: utf-8 -*-
from django import http
from django.template import Context, loader

import sys
import pprint
import datetime

class ErrorCaptureMiddleware(object):
    """
    Middleware to capture exceptins and create a ticket/bug for it.
    see: django.core.handlers.base
    """
    traceback = __import__('traceback')

    def process_response(self, request, response):
        sc = response.status_code
        if sc in [404]:
            from django.conf import settings
            from django.core.mail import mail_admins

            if not settings.DEBUG:
                subject = '%d error' % response.status_code
                try:
                    request_repr = repr(request)
                except:
                    request_repr = "Request repr() unavailable"

                try:
                    session_repr = pprint.pformat(request.session._session)
                except:
                    session_repr = "Session repr() unavailable"

                from socket import gethostname
                from yats import get_version, get_python_version
                from django import get_version as get_django_version
                yats_data = 'URL: %s\nRAW_POST: %s\nHOST_NAME: %s\nYATS_APP_VERSION: %s\nDJANGO_VERSION: %s\nPYTHON: %s' % (request.build_absolute_uri(), request.body, gethostname(), get_version(), get_django_version(), get_python_version())
                if hasattr(request, 'user') and request.user.is_authenticated():
                    yats_data += '\nUSER: %s' % request.user.email
                message = "%s\n\n%s" % (yats_data, '%s\n\n%s' % (session_repr, request_repr))
                mail_admins(subject, message, fail_silently=True)

        return response

    def process_exception(self, request, exception):
        # If this is a 404 ...
        #if isinstance(exception, http.Http404):
        #    raise exception

        from django.conf import settings
        from django.core.mail import mail_admins

        if settings.DEBUG_PROPAGATE_EXCEPTIONS:
            raise

        exc_info = sys.exc_info()
        from socket import gethostname
        from yats import get_version, get_python_version
        from django import get_version as get_django_version
        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"

        try:
            session_repr = pprint.pformat(request.session._session)
        except:
            session_repr = "Session repr() unavailable"

        if settings.DEBUG:
            from django.views import debug
            return debug.technical_500_response(request, *exc_info)

        # send an error message to the admins, if something fails... => and not a bot
        subject = 'BUGTRACK EXCEPTION: %s' % type(exception).__name__[:60]

        yats_data = 'TS: %s\nURL: %s\nRAW_POST: %s\nHOST_NAME: %s\nYATS_APP_VERSION: %s\nDJANGO_VERSION: %s\nPYTHON: %s' % (datetime.datetime.now(), request.build_absolute_uri(), request.body, gethostname(), get_version(), get_django_version(), get_python_version())
        if hasattr(request, 'organisation'):
            yats_data += '\nORGA: %s' % request.organisation.name
        else:
            if hasattr(request, 'user') and request.user.is_authenticated():
                yats_data += '\nUSER: %s' % request.user.email
        message = "%s\n\n%s\n\n%s" % (self._get_traceback(exc_info), yats_data, '%s\n\n%s' % (session_repr, request_repr))
        mail_admins(subject, message, fail_silently=False)

        return http.HttpResponseServerError(loader.get_template('500.html').render(Context()))

    def _get_traceback(self, exc_info=None):
        "Helper function to return the traceback as a string"
        import traceback
        return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
