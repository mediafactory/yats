# -*- coding: utf-8 -*-
from django.urls import include, re_path
from django.contrib import admin
from django.conf import settings
from djradicale.views import DjRadicaleView, WellKnownView

admin.autodiscover()

handler500 = 'yats.errors.server_error'

urlpatterns = [
    re_path(r'^', include('yats.check.urls')),
    re_path(r'^', include('yats.urls')),
    re_path(r'^admin/', admin.site.urls),

    re_path(r'^' + settings.DJRADICALE_CONFIG['server']['base_prefix'].lstrip('/'), include(('djradicale.urls', 'djradicale'))),

    # .well-known external implementation
    re_path(r'^\.well-known/(?P<type>(caldav|carddav))$',
        WellKnownView.as_view(), name='djradicale_well-known'),

    # .well-known internal (radicale) implementation
    re_path(r'^\.well-known/(?P<type>(caldav|carddav))$',
         DjRadicaleView.as_view(), name='djradicale_well-known'),
]
