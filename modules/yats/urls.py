# -*- coding: utf-8 -*- 
from django.conf.urls import patterns, url
from yats.views import root, info
from yats.tickets import new, action, table, search, reports

urlpatterns = patterns('',
    (r'^RPC2/$', 'rpc4django.views.serve_rpc_request'),
   url(r'^$',
        view=root,
        name='view_root'),
   
   # tickets
   url(r'^tickets/new/$',
        view=new,
        name='new'),

   url(r'^tickets/list/$',
        view=table,
        name='table'),

   url(r'^tickets/search/$',
        view=search,
        name='search'),

   url(r'^tickets/(?P<mode>\w+)/(?P<ticket>\d+)/$',
        view=action,
        name='action'),

   # reports
   url(r'^reports/$',
        view=reports,
        name='reports'),

   # info
   url(r'^info/$',
        view=info,
        name='info'),
   
)