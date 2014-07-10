# -*- coding: utf-8 -*- 
from django.conf.urls import patterns, url
from yats.views import root, info, board
from yats.tickets import new, action, table, search, reports, workflow

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

   # workflow
   url(r'^workflow/$',
        view=workflow,
        name='workflow'),

   # boards
   url(r'^board/(?P<name>[\w|\W]+)/$',
        view=board,
        name='board'),

   # info
   url(r'^info/$',
        view=info,
        name='info'),
   
)