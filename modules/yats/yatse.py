# -*- coding: utf-8 -*-
from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth import User
from yats.shortcuts import get_ticket_model, modulePathToModuleName, build_ticket_search, clean_search_values
from yats.models import UserProfile
try:
    import json
except ImportError:
    from django.utils import simplejson as json

def api_login(request):
    if request.META.get('HTTP_API_KEY') == settings.API_KEY and request.META.get('HTTP_API_USER') <> '':
        try:
            user = User.object.get(username=request.META.get('HTTP_API_USER'), is_active=True)
            request.user = user
            request.organisation = UserProfile.objects.get(user=user).organisation
        except:
            raise PermissionDenied
    else:
        raise PermissionDenied

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

def YATSSearch(request):
    def ValuesQuerySetToDict(vqs):
        return [item for item in vqs]

    tic = get_ticket_model().objects.select_related('type').all()
    # todo content_type
    # evtl: request.body.decode('utf-8')
    data = json.loads(request.body)
    search_params, base_query = build_ticket_search(request, tic, {}, clean_search_values(data))
    return ValuesQuerySetToDict(base_query)
