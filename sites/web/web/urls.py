# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from simple_sso.sso_client.client import Client
from djradicale.views import DjRadicaleView, WellKnownView

admin.autodiscover()

handler500 = 'yats.errors.server_error'

test_client = Client(settings.SSO_SERVER, settings.SSO_PUBLIC_KEY, settings.SSO_PRIVATE_KEY)

urlpatterns = [
    url(r'^', include('yats.check.urls')),
    url(r'^', include('yats.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^client/', include(test_client.get_urls())),

    url(r'^' + settings.DJRADICALE_CONFIG['server']['base_prefix'].lstrip('/'),
        include('djradicale.urls', namespace='djradicale')),

    # .well-known external implementation
    url(r'^\.well-known/(?P<type>(caldav|carddav))$',
        WellKnownView.as_view(), name='djradicale_well-known'),

    # .well-known internal (radicale) implementation
    # url(r'^\.well-known/(?P<type>(caldav|carddav))$',
    #     DjRadicaleView.as_view(), name='djradicale_well-known'),
]
