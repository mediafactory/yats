# -*- coding: utf-8 -*-
from django.urls import include, re_path
from yats.views import root, info, show_board, board_by_id, yatse_api, login, logout, kanban, xptest, robots, autocomplete
from yats.tickets import new, action, table, search, search_ex, search_simple, reports, workflow, simple, create, log
from yats.docs import docs_action, docs_new, docs_search, docs_wiki
from yats.forms import yatsSearchView
from rpc4django.views import serve_rpc_request
from markdownx import urls as markdownx

handler500 = 'yats.errors.server_error'

urlpatterns = [
   re_path(r'^rpc/$',
       view=serve_rpc_request,
       name='rpc'),

   re_path(r'^$',
       view=root,
       name='view_root'),

   # tickets
   re_path(r'^tickets/create/$',
       view=create,
       name='create'),

   re_path(r'^tickets/new/$',
       view=new,
       name='new'),

   re_path(r'^tickets/simple/$',
       view=simple,
       name='simple'),

   re_path(r'^tickets/list/$',
       view=table,
       name='table'),

   re_path(r'^tickets/search/$',
       view=search,
       name='search'),

   re_path(r'^tickets/search/simple/$',
       view=search_simple,
       name='search_simple'),

   re_path(r'^tickets/search/extended/$',
       view=search_ex,
       name='search_ex'),

   re_path(r'^tickets/(?P<mode>\w+)/(?P<ticket>\d+)/$',
       view=action,
       name='action'),

   # search
   re_path(r'^search/?$', yatsSearchView.as_view(), name='search_view'),

   # search
   re_path(r'^search/auto/',
       view=autocomplete,
       name='autocomplete'),

   # reports
   re_path(r'^reports/$',
       view=reports,
       name='reports'),

   # workflow
   re_path(r'^workflow/$',
       view=workflow,
       name='workflow'),

   # boards
   re_path(r'^board/(?P<id>\d+)/$',
       view=board_by_id,
       name='board_by_id'),

   re_path(r'^board/(?P<name>[\w|\W]+)/$',
       view=show_board,
       name='board'),

   # kanban
   re_path(r'^kanban/$',
       view=kanban,
       name='kanban'),

   # info
   re_path(r'^info/$',
       view=info,
       name='info'),

   # local login
   re_path(r'^local_login/$',
       view=login,
       name='login'),

   re_path(r'^local_logout/$',
       view=logout,
       name='logout'),

   # docs
   re_path(r'^docs/(?P<mode>\w+)/(?P<docid>\d+)/$',
       view=docs_action,
       name='docs_action'),

   re_path(r'^docs/view/wikis/(?P<wiki>\w+)/$',
       view=docs_wiki,
       name='docs_wiki'),

   re_path(r'^docs/new/$',
       view=docs_new,
       name='docs_new'),

   re_path(r'^docs/search/$',
       view=docs_search,
       name='docs_search'),

   # log
   re_path(r'^log/$',
       view=log,
       name='log'),

   # yatse
   re_path(r'^yatse/$',
       view=yatse_api,
       name='yatse_api'),

   # xptest
   re_path(r'^xptest/(?P<test>[\w|\W]+)/$',
       view=xptest,
       name='xptest'),

   # robots
   re_path(r'^robots\.txt',
       view=robots,
       name='robots'),

   re_path(r'^markdownx/', include(markdownx)),
]
