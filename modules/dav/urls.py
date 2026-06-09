# -*- coding: utf-8 -*-
from django.urls import re_path

from dav.views import caldav_view

app_name = 'dav'

urlpatterns = [
    re_path(r'^(?P<path>.*)$', caldav_view, name='caldav'),
]
