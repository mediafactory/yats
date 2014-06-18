# -*- coding: utf-8 -*- 
from django.conf.urls import patterns, url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
admin.autodiscover()

urlpatterns =staticfiles_urlpatterns() + patterns('',
    (r'^', include('yats.check.urls')),
    url(r'^', include('yats.urls')),
    url(r'^admin/', include(admin.site.urls)),
)
