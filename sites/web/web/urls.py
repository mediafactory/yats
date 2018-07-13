# -*- coding: utf-8 -*-
from django.conf.urls import include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = [
    url(r'^', include('yats.check.urls')),
    url(r'^', include('yats.urls')),
    url(r'^admin/', include(admin.site.urls)),
]
