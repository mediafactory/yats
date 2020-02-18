# -*- coding: utf-8 -*-
from django.conf.urls import url
from . views import raiseerror, raise404, notfound

urlpatterns = [
    url(r'^check/raise/500/$',
        view=raiseerror,
        name='check_raise'),

    url(r'^check/raise/404/$',
        view=raise404,
        name='check_raise'),

    url(r'^check/404/$',
        view=notfound,
        name='check_raise'),
]
