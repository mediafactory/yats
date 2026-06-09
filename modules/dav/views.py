# -*- coding: utf-8 -*-
"""
Embedded Radicale 3.x as a WSGI app behind a Django view.

Every CalDAV request first passes through Django (HTTP Basic auth against the
Django user store), then the environ is handed to a singleton Radicale
``Application`` configured with the YATS plugins (``dav.storage``,
``dav.radicale_auth``, ``dav.radicale_rights``). Radicale's own auth plugin
trusts the username Django already validated.
"""
import io
import base64
import logging
import threading

from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger('dav')

# Base prefix the view is mounted under (must match urls.py / CALDAV_BASE_PREFIX).
_BASE_PREFIX = getattr(settings, 'CALDAV_BASE_PREFIX', '/tickets/dav/')
_SCRIPT_NAME = '/' + _BASE_PREFIX.strip('/')

_radicale_app = None
_app_lock = threading.Lock()


def _get_radicale_app():
    """Build (once) and return the singleton Radicale WSGI application."""
    global _radicale_app
    if _radicale_app is None:
        with _app_lock:
            if _radicale_app is None:
                from radicale import Application
                from radicale import config as radicale_config
                cfg = radicale_config.load()
                cfg.update({
                    'auth': {'type': 'dav.radicale_auth'},
                    'rights': {'type': 'dav.radicale_rights'},
                    'storage': {'type': 'dav.storage'},
                }, 'yats')
                _radicale_app = Application(cfg)
    return _radicale_app


def _authenticate_basic(request):
    """Return the validated Django user from the Basic auth header, or None."""
    header = request.META.get('HTTP_AUTHORIZATION', '')
    parts = header.split()
    if len(parts) != 2 or parts[0].lower() != 'basic':
        return None
    try:
        raw = parts[1] + '=' * ((4 - len(parts[1]) % 4) % 4)
        username, password = base64.b64decode(raw).decode('utf-8').split(':', 1)
    except Exception:
        return None
    return authenticate(username=username, password=password)


def _build_environ(request):
    """Build a clean WSGI environ for Radicale from the Django request."""
    environ = dict(request.META)
    # Re-expose the (already consumed) request body as a fresh stream.
    body = request.body or b''
    environ['wsgi.input'] = io.BytesIO(body)
    environ['CONTENT_LENGTH'] = str(len(body))
    # Mount point: SCRIPT_NAME is the prefix, PATH_INFO the resource path.
    environ['SCRIPT_NAME'] = _SCRIPT_NAME
    environ['PATH_INFO'] = request.path[len(_SCRIPT_NAME):] or '/'
    return environ


def _run_wsgi(app, environ):
    captured = {}
    chunks = []

    def start_response(status, headers, exc_info=None):
        captured['status'] = status
        captured['headers'] = headers
        return chunks.append

    iterable = app(environ, start_response)
    try:
        for chunk in iterable:
            if chunk:
                chunks.append(chunk)
    finally:
        if hasattr(iterable, 'close'):
            iterable.close()

    body = b''.join(chunks)
    status_code = int(captured['status'].split(' ', 1)[0])
    return body, status_code, captured['headers']


@csrf_exempt
def caldav_view(request, path=''):
    # OPTIONS is used for capability discovery and must work without auth.
    if request.method != 'OPTIONS':
        user = _authenticate_basic(request)
        if user is None or not user.is_active:
            resp = HttpResponse('Unauthorized', status=401)
            resp['WWW-Authenticate'] = 'Basic realm="YATS Tickets - Password Required"'
            return resp

    environ = _build_environ(request)
    body, status, headers = _run_wsgi(_get_radicale_app(), environ)

    response = HttpResponse(body, status=status)
    for key, value in headers:
        if key.lower() == 'content-length':
            continue
        response[key] = value
    return response


@csrf_exempt
def well_known_view(request, type):
    """Redirect .well-known/{caldav,carddav} to the CalDAV mount point."""
    resp = HttpResponse(status=301)
    resp['Location'] = _BASE_PREFIX
    return resp
