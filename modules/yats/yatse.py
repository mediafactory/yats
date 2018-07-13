# -*- coding: utf-8 -*-
from django.apps import apps
from yats.shortcuts import get_ticket_model, modulePathToModuleName

def buildYATSFields(exclude_list):
    TracFields = []
    TicketFields = {}
    tickets = get_ticket_model()
    t = tickets()
    for field in t._meta.fields:
        if field.name in exclude_list:
            continue

        if type(field).__name__ == 'ForeignKey':
            typename = 'select'
            options = []
            opts = apps.get_model(modulePathToModuleName(field.rel.to.__module__), field.rel.to.__name__).objects.all()
            for opt in opts:
                options.append(unicode(opt))

            TicketFields[field.name] = (modulePathToModuleName(field.rel.to.__module__), field.rel.to.__name__)

        else:
            typename = field.__class__.__name__

            # TODO: bool and boolnull and choices
            options = None

            TicketFields[field.name] = None

        value = {
                'name': field.name,
                'label': field.name,
                'type': typename
               }
        if options:
            value['options'] = options
        TracFields.append(value)
    return (TracFields, TicketFields)
