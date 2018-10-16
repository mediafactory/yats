# -*- coding: utf-8 -*-
from django.conf.urls import  url, include
from yats.views import root, info, show_board, board_by_id, yatse_api, login, logout, kanban, xptest, robots, autocomplete
from yats.tickets import new, action, table, search, search_ex, search_simple, reports, workflow, simple, create, log
from yats.docs import docs_action, docs_new
from rpc4django.views import serve_rpc_request
from markdownx import urls as markdownx

handler500 = 'yats.errors.server_error'

urlpatterns = [
    url(r'^rpc/$',
        view=serve_rpc_request,
        name='tx.tickets.callback'),

   url(r'^$',
        view=root,
        name='view_root'),

   # tickets
   url(r'^tickets/create/$',
        view=create,
        name='create'),

   url(r'^tickets/new/$',
        view=new,
        name='new'),

   url(r'^tickets/simple/$',
        view=simple,
        name='simple'),

   url(r'^tickets/list/$',
        view=table,
        name='table'),

   url(r'^tickets/search/$',
        view=search,
        name='search'),

   url(r'^tickets/search/simple/$',
        view=search_simple,
        name='search_simple'),

   url(r'^tickets/search/extended/$',
        view=search_ex,
        name='search_ex'),

   url(r'^tickets/(?P<mode>\w+)/(?P<ticket>\d+)/$',
        view=action,
        name='action'),

   # search
   url(r'^search/', include('haystack.urls')),

   # search
   url(r'^search/auto/',
        view=autocomplete,
        name='autocomplete'),

   # reports
   url(r'^reports/$',
        view=reports,
        name='reports'),

   # workflow
   url(r'^workflow/$',
        view=workflow,
        name='workflow'),

   # boards
   url(r'^board/(?P<id>\d+)/$',
        view=board_by_id,
        name='board_by_id'),

   url(r'^board/(?P<name>[\w|\W]+)/$',
        view=show_board,
        name='board'),

   # kanban
   url(r'^kanban/$',
        view=kanban,
        name='kanban'),

   # info
   url(r'^info/$',
        view=info,
        name='info'),

   # local login
   url(r'^local_login/$',
        view=login,
        name='login'),

   url(r'^local_logout/$',
        view=logout,
        name='logout'),

   # docs
   url(r'^docs/(?P<mode>\w+)/(?P<docid>\d+)/$',
        view=docs_action,
        name='docs_action'),

   url(r'^docs/new/$',
        view=docs_new,
        name='docs_new'),

   # log
   url(r'^log/$',
        view=log,
        name='log'),

   # yatse
   url(r'^yatse/$',
        view=yatse_api,
        name='yatse_api'),

   # xptest
   url(r'^xptest/(?P<test>[\w|\W]+)/$',
        view=xptest,
        name='xptest'),

   # robots
   url(r'^robots\.txt',
        view=robots,
        name='robots'),

    url(r'^markdownx/', include(markdownx)),
]
