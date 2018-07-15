# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from simple_sso.sso_client.client import Client

admin.autodiscover()

test_client = Client(settings.SSO_SERVER, settings.SSO_PUBLIC_KEY, settings.SSO_PRIVATE_KEY)

urlpatterns = [
    url(r'^', include('yats.check.urls')),
    url(r'^', include('yats.urls')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^client/', include(test_client.get_urls())),
]
