# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _
from django.apps import apps
from django.conf import settings
from django.http import QueryDict
from yats.shortcuts import get_ticket_model, modulePathToModuleName, touch_ticket, remember_changes, mail_ticket, jabber_ticket, check_references
from rpc4django import rpcmethod
from xmlrpclib import Fault
import datetime

"""
    http://code.google.com/p/tracker-for-trac/source/browse/trunk/%40source/trac_main.pas
    http://trac-hacks.org/browser/xmlrpcplugin#0.10/tracrpc
    http://www.hossainkhan.info/content/trac-xml-rpc-api-reference
"""

APPLICATION_ERROR = -32500
FIELD_EXCLUDE_LIST = ['id', 'active_record', 'd_user', 'd_date', 'u_user', 'close_date', 'last_action_date', 'tickets_ptr', 'closed']

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
    if field == 'state':
        return 'status'

    return field

def buildFields(exclude_list):
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
            if field.__class__.__name__ == 'TextField':
                typename = 'textarea'
            else:
                typename = 'text'

            # TODO: bool and boolnull and choices
            options = None

            TicketFields[field.name] = None

        value = {
                'name': field.name,
                'label': fieldNameToTracName(field.name),
                'type': typename
               }
        if options:
            value['options'] = options
        TracFields.append(value)
    return (TracFields, TicketFields)

def TracNameTofieldName(field):
    if field == 'time created':
        return 'c_date'
    if field == 'reporter':
        return 'c_user'
    if field == 'time changed':
        return 'u_date'
    if field == 'owner':
        return 'assigned'
    if field == 'summary':
        return 'caption'
    if field == 'status':
        return 'state'
    return field

def add_search_terms(field_defs, parts, compare, results):
    if field_defs[parts[0]] == None:
        results['%s%s' % (parts[0], compare)] = parts[1]
    else:
        results[parts[0]] = apps.get_model(field_defs[parts[0]][0], field_defs[parts[0]][1]).objects.get(name=parts[1]).pk

def search_terms(q):
    """
    Break apart a search query into its various search terms.  Terms are
    grouped implicitly by word boundary, or explicitly by (single or double)
    quotes.
    """
    results = {}
    fields = buildFields([])[1]
    elements = q.split('&')
    for element in elements:
        if '<=' in element:
            parts = element.split('<=')
            add_search_terms(fields, parts, '__lte', results)
        elif '=>' in element:
            parts = element.split('=>')
            add_search_terms(fields, parts, '__gte', results)
        elif '$=' in element:
            parts = element.split('$=')
            add_search_terms(fields, parts, '__iendswith', results)
        elif '^=' in element:
            parts = element.split('^=')
            add_search_terms(fields, parts, '__istartswith', results)
        elif '~=' in element:
            parts = element.split('~=')
            add_search_terms(fields, parts, '__icontains', results)
        elif '>' in element:
            parts = element.split('>')
            add_search_terms(fields, parts, '__gt', results)
        elif '<' in element:
            parts = element.split('<')
            add_search_terms(fields, parts, '__lt', results)
        elif '=' in element:
            parts = element.split('=')
            add_search_terms(fields, parts, '__iexact', results)

    return results

@rpcmethod(name='system.getAPIVersion', signature=['array'], login_required=True)
def getAPIVersion():
    return [-1,0,1]

@rpcmethod(name='ticket.getTicketFields', signature=['array'], login_required=True)
def getTicketFields(**kwargs):
    """
        array ticket.getTicketFields()
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

        cache ticket structur:
        {
            'caption': None,
            'state': (modPath, modName, ),
            ...
        }

    """
    request = kwargs['request']

    exclude_list = FIELD_EXCLUDE_LIST
    if not request.user.is_staff:
        exclude_list = list(set(exclude_list + settings.TICKET_NON_PUBLIC_FIELDS))

    return buildFields(exclude_list)[0]

@rpcmethod(name='ticket.query', signature=['array'], login_required=True)
def query(*args, **kwargs):
    """
    array ticket.query(string qstr="status!=closed")
    """
    request = kwargs['request']

    tickets = get_ticket_model().objects.all()
    if len(args) > 0:
        tickets =  tickets.filter(**search_terms(args[0]))

    ids = tickets.values_list('id', flat=True)
    return list(ids)

@rpcmethod(name='ticket.get', signature=['array', 'int'], login_required=True)
def get(id, **kwargs):
    """
    array ticket.get(int id)
    """
    exclude_list = FIELD_EXCLUDE_LIST
    #exclude_list.pop(exclude_list.index('id'))

    request = kwargs['request']

    if not request.user.is_staff:
        exclude_list = list(set(exclude_list + settings.TICKET_NON_PUBLIC_FIELDS))

    ticket = get_ticket_model().objects.get(pk=id)

    attributes = {}
    for field in ticket._meta.fields:
        if field.name in exclude_list:
            continue
        if type(field).__name__ in ['DateTimeField', 'BooleanField', 'NullBooleanField']:
            attributes[fieldNameToTracName(field.name)] = getattr(ticket, field.name)
        elif type(field).__name__ == 'DateField':
            if not getattr(ticket, field.name) == None:
                attributes[fieldNameToTracName(field.name)] = datetime.datetime.combine(getattr(ticket, field.name), datetime.datetime.min.time())
            else:
                attributes[fieldNameToTracName(field.name)] = None

        else:
            attributes[fieldNameToTracName(field.name)] = unicode(getattr(ticket, field.name))
    return [id, ticket.c_date, ticket.last_action_date, attributes]

@rpcmethod(name='ticket.update', signature=['array', 'int', 'string', 'struct', 'bool'], login_required=True)
def update(id, comment, attributes={}, notify=False, **kwargs):
    """
    array ticket.update(int id, string comment, struct attributes={}, boolean notify=False)
    Update a ticket, returning the new ticket in the same form as getTicket(). Requires a valid 'action' in attributes to support workflow.
    """
    from yats.forms import TicketsForm

    request = kwargs['request']
    params = {}
    for key, value in attributes.iteritems():
        params[TracNameTofieldName(key)] = value

    ticket = get_ticket_model().objects.get(pk=id)
    if ticket.closed:
        return Fault(_('ticket already closed'))

    fakePOST = QueryDict('', mutable=True)
    fakePOST.update(params)

    form = TicketsForm(fakePOST, instance=ticket, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    form.cleaned_data = params
    form._changed_data = [name for name in params]

    for key, value in params.iteritems():
        setattr(ticket, key, value)
        if key == 'assigned':
            touch_ticket(value, ticket.pk)
    ticket.save(user=request.user)

    remember_changes(request, form, ticket)

    touch_ticket(request.user, ticket.pk)

    if comment:
        from yats.models import tickets_comments

        com = tickets_comments()
        com.comment = _('ticket changed by %(user)s\n\n%(comment)s') % {'user': request.user, 'comment': comment}
        com.ticket = ticket
        com.action = 4
        com.save(user=request.user)

        check_references(request, com)

    if notify:
        mail_ticket(request, ticket.pk, form, is_api=True)
        jabber_ticket(request, ticket.pk, form, is_api=True)

    return get(id, **kwargs)

@rpcmethod(name='ticket.create', signature=['array', 'struct', 'bool'], login_required=True)
def create(attributes={}, notify=True, **kwargs):
    """
    array ticket.create(struct attributes={}, boolean notify=False)
    create a ticket, returning the new ticket in the same form as getTicket(). Requires a valid 'action' in attributes to support workflow.
    """
    from yats.forms import TicketsForm

    excludes = ['resolution']

    request = kwargs['request']
    params = {}
    for key, value in attributes.iteritems():
        params[TracNameTofieldName(key)] = value

    fakePOST = QueryDict(mutable=True)
    fakePOST.update(params)

    form = TicketsForm(fakePOST, exclude_list=excludes, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    if form.is_valid():
        tic = form.save()
        if tic.keep_it_simple:
            tic.keep_it_simple = False
            tic.save(user=request.user)

        assigned = form.cleaned_data.get('assigned')
        if assigned:
            touch_ticket(assigned, tic.pk)

        for ele in form.changed_data:
            form.initial[ele] = ''
        remember_changes(request, form, tic)

        touch_ticket(request.user, tic.pk)

        if notify:
            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT)

        return get(tic.id, **kwargs)

    else:
        raise Exception('missing attributes')

@rpcmethod(name='ticket.createSimple', signature=['array', 'struct', 'bool'], login_required=True)
def createSimple(attributes={}, notify=True, **kwargs):
    from yats.forms import SimpleTickets

    request = kwargs['request']
    params = {}
    for key, value in attributes.iteritems():
        params[TracNameTofieldName(key)] = value

    fakePOST = QueryDict(mutable=True)
    fakePOST.update(params)

    form = SimpleTickets(fakePOST)
    if form.is_valid():
        cd = form.cleaned_data
        ticket = get_ticket_model()
        tic = ticket()
        tic.caption = cd['caption']
        tic.description = cd['description']
        if 'priority' not in cd or not cd['priority']:
            if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_PRIORITY') and settings.KEEP_IT_SIMPLE_DEFAULT_PRIORITY:
                tic.priority_id = settings.KEEP_IT_SIMPLE_DEFAULT_PRIORITY
        else:
            tic.priority = cd['priority']
        tic.assigned = cd['assigned']
        if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER') and settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER:
            if settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER == -1:
                tic.customer = request.organisation
            else:
                tic.customer_id = settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOME
        if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT') and settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT:
            tic.component_id = settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT
        tic.deadline = cd['deadline']
        tic.save(user=request.user)

        if tic.assigned:
            touch_ticket(tic.assigned, tic.pk)

        for ele in form.changed_data:
            form.initial[ele] = ''
        remember_changes(request, form, tic)

        touch_ticket(request.user, tic.pk)

        if notify:
            mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT)
            jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT)

        return get(tic.id, **kwargs)

    else:
        raise Exception('missing attributes')
