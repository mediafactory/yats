# -*- coding: utf-8 -*-
from django.urls import re_path
from . views import raiseerror, raise404, notfound

urlpatterns = [
    re_path(r'^check/raise/500/$',
        view=raiseerror,
        name='check_raise'),

    re_path(r'^check/raise/404/$',
        view=raise404,
        name='check_raise'),

    re_path(r'^check/404/$',
        view=notfound,
        name='check_raise'),
]
