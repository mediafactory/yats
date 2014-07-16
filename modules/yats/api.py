# -*- coding: utf-8 -*-
from django.db.models import get_model
from yats.shortcuts import get_ticket_model, modulePathToModuleName
from rpc4django import rpcmethod

from xmlrpclib import Fault
APPLICATION_ERROR = -32500

def getModelValue(mod_path, cls_name, value):
    mod_path = mod_path.split('.').pop(0)
    try:
        return unicode(get_model(mod_path, cls_name).objects.get(pk=value))
    except:
        return u''

@rpcmethod(name='tickets.getTicketFields', signature=['array']) 
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
    # request = kwargs['request']
    result = []    
        
    tickets = get_ticket_model()
    t = tickets()
    for field in t._meta.fields:
        # TODO: remove fields
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
            options = None
        
        value = {
                'label': field.name,
                'type': typename
               }
        if options:
            value['options'] = options
        result.append(value)

    return result