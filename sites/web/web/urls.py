# -*- coding: utf-8 -*-
from django.urls import include, re_path
from django.contrib import admin
from django.conf import settings
from dav.views import caldav_view, well_known_view

admin.autodiscover()

_CALDAV_PREFIX = getattr(settings, 'CALDAV_BASE_PREFIX', '/tickets/dav/').lstrip('/')

handler500 = 'yats.errors.server_error'

urlpatterns = [
    re_path(r'^', include('yats.check.urls')),
    re_path(r'^', include('yats.urls')),
    re_path(r'^admin/', admin.site.urls),

    # CalDAV: embedded Radicale 3.x WSGI app (modules/dav/).
    re_path(r'^' + _CALDAV_PREFIX + r'(?P<path>.*)$', caldav_view, name='caldav'),
    re_path(r'^\.well-known/(?P<type>(caldav|carddav))$', well_known_view, name='well-known'),
]
