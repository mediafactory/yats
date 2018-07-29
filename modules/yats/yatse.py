# -*- coding: utf-8 -*-
from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.http.request import QueryDict
from yats.shortcuts import get_ticket_model, modulePathToModuleName, build_ticket_search, clean_search_values
from yats.models import UserProfile
from yats.forms import SearchForm
try:
    import json
except ImportError:
    from django.utils import simplejson as json

def api_login(request):
    if request.META.get('HTTP_API_KEY') == settings.API_KEY and request.META.get('HTTP_API_USER') <> '':
        try:
            user = User.objects.get(username=request.META.get('HTTP_API_USER'), is_active=True)
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

    tic = get_ticket_model().objects.select_related('type', 'state', 'assigned').all()
    data = json.loads(request.body)
    POST = QueryDict(mutable=True)
    POST.update(data)
    form = SearchForm(POST, include_list=settings.TICKET_SEARCH_FIELDS, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    form.is_valid()
    for err in form._errors:
        field = form.fields[err]
        b = type(field)
        if err in ['c_user']:
            try:
                form.cleaned_data[err] = field.choices.queryset.get(username=data[err]).pk
            except:
                form.cleaned_data[err] = -1
        else:
            try:
                form.cleaned_data[err] = field.choices.queryset.get(name=data[err]).pk
            except:
                form.cleaned_data[err] = -1

    search_params, base_query = build_ticket_search(request, tic, {}, clean_search_values(form.cleaned_data))
    return ValuesQuerySetToDict(base_query.values('id', 'caption', 'c_date', 'type__name', 'state__name', 'assigned__username', 'deadline', 'closed'))
