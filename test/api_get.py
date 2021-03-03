#!/usr/bin/python3
# -*- coding: utf-8 -*-
import base64
from xmlrpc import client as xmlrpclib

rpc_srv = xmlrpclib.ServerProxy('http://admin:admin@192.168.33.11/rpc/', allow_none=True, use_datetime=True)
info = rpc_srv.ticket.get(1)

print('ticket: #%s' % info)
