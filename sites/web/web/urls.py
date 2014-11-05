# -*- coding: utf-8 -*- 
from django.conf.urls import patterns, url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.contrib import admin
admin.autodiscover()

from wiki.urls import get_pattern as get_wiki_pattern # for wiki
from django_nyt.urls import get_pattern as get_nyt_pattern # for wiki

urlpatterns = staticfiles_urlpatterns() + patterns('',
    (r'^', include('yats.check.urls')),
    url(r'^', include('yats.urls')),
    url(r'^admin/', include(admin.site.urls)),
    (r'^notifications/', get_nyt_pattern()), # for wiki
    (r'^wiki/', get_wiki_pattern()), # for wiki
)

