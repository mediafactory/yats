# -*- coding: utf-8 -*-
from django.db.models import get_model
from django.conf import settings
from yats.shortcuts import get_ticket_model, modulePathToModuleName
from rpc4django import rpcmethod

"""
    http://code.google.com/p/tracker-for-trac/source/browse/trunk/%40source/trac_main.pas
    http://trac-hacks.org/browser/xmlrpcplugin#0.10/tracrpc
    http://www.hossainkhan.info/content/trac-xml-rpc-api-reference
"""

from xmlrpclib import Fault
APPLICATION_ERROR = -32500
FIELD_EXCLUDE_LIST = ['id', 'active_record', 'd_user', 'd_date', 'u_user', 'close_date', 'last_action_date', 'tickets_ptr']

def fieldNameToTracName(field):
    if field == 'c_date':
        return 'time created'
    if field == 'c_user':
        return 'reporter'
    if field == 'u_date':
        return 'time changed'
    if field == 'assigned':
        return 'owner'
    if field == 'caption':
        return 'summary'
    
    return field
    
@rpcmethod(name='system.getAPIVersion', signature=['array']) 
def getAPIVersion():
    return [1,2,3]

@rpcmethod(name='ticket.getTicketFields', signature=['array']) 
def getTicketFields(**kwargs):
    """
        returns an array of field items:
        [
            {
                'name': 'aaa',
                'type': 'text',
            },
            {
                'name': 'bbb',
                'type': 'textarea',
            },
            {
                'name': 'ccc',
                'type': 'select',
                'options': [
                    'a',
                    'b',
                    'c'
                ]
            },
            {
                'name': 'ddd',
                'type': 'radio',
            },            
        ]

    """
    request = kwargs['request']
    result = []
    exclude_list = FIELD_EXCLUDE_LIST
    if not request.user.is_staff:
        exclude_list = list(set(exclude_list + settings.TICKET_NON_PUBLIC_FIELDS))
        
    tickets = get_ticket_model()
    t = tickets()
    for field in t._meta.fields:
        if field.name in exclude_list:
            continue
        
        if type(field).__name__ == 'ForeignKey':
            typename = 'select'
            options = []
            opts = get_model(modulePathToModuleName(field.rel.to.__module__), field.rel.to.__name__).objects.all()
            for opt in opts:
                options.append(unicode(opt))
        else:
            # print field.__class__.__name__
            if field.__class__.__name__ == 'TextField':
                typename = 'textarea'
            else:
                typename = 'text'
                
            # TODO: bool and boolnull and choices
            options = None
        
        value = {
                'name': field.name,
                'label': fieldNameToTracName(field.name),
                'type': typename
               }
        if options:
            value['options'] = options
        result.append(value)

    return result

@rpcmethod(name='ticket.query', signature=['array'])
def query(**kwargs):
    return [1]


@rpcmethod(name='ticket.get', signature=['array', 'int'])
def get(id, **kwargs):
    exclude_list = FIELD_EXCLUDE_LIST
    request = kwargs['request']
    
    if not request.user.is_staff:
        exclude_list = list(set(exclude_list + settings.TICKET_NON_PUBLIC_FIELDS))

    ticket = get_ticket_model().objects.get(pk=id)

    attributes = {}
    for field in ticket._meta.fields:
        if field.name in exclude_list:
            continue
        attributes[field.name] = unicode(getattr(ticket, field.name))
        
    return [id, ticket.c_date, ticket.last_action_date, attributes]