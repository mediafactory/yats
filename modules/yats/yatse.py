# -*- coding: utf-8 -*-
from django.apps import apps
from django.conf import settings
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.models import User
from django.http.request import QueryDict
from django.utils import timezone
from yats.shortcuts import get_ticket_model, modulePathToModuleName, build_ticket_search, clean_search_values
from yats.models import UserProfile, tickets_participants
from yats.forms import SearchForm
try:
    import json
except ImportError:
    from django.utils import simplejson as json
import datetime

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

    tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
    data = json.loads(request.body)

    if 'extra_filter' in data:
        extra_filter = data['extra_filter']
        del data['extra_filter']
    else:
        extra_filter = None
    if 'days' in data:
        days = data['days']
        del data['days']
    else:
        days = None
    if 'exclude_own' in data:
        exclude_own = data['exclude_own']
        del data['exclude_own']
    else:
        exclude_own = False

    POST = QueryDict(mutable=True)
    POST.update(data)
    form = SearchForm(POST, include_list=settings.TICKET_SEARCH_FIELDS, is_stuff=request.user.is_staff, user=request.user, customer=request.organisation.id)
    form.is_valid()
    for err in form._errors:
        field = form.fields[err]
        # b = type(field)
        if err in ['c_user', 'assigned']:
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
    if extra_filter:
        if extra_filter == '1':  # days since closed
            base_query = base_query.filter(close_date__gte=datetime.date.today() - datetime.timedelta(days=days)).exclude(close_date=None)
        if extra_filter == '2':  # days since created
            base_query = base_query.filter(c_date__gte=datetime.date.today() - datetime.timedelta(days=days))
        if extra_filter == '3':  # days since last changed
            base_query = base_query.filter(u_date__gte=datetime.date.today() - datetime.timedelta(days=days))
        if extra_filter == '4':  # days since last action
            base_query = base_query.filter(last_action_date__gte=datetime.date.today() - datetime.timedelta(days=days))
        if extra_filter == '5':  # days since falling due
            base_query = base_query.filter(deadline__lte=timezone.now() - datetime.timedelta(days=days)).filter(deadline__isnull=False)

    if exclude_own:
        base_query = base_query.exclude(assigned=request.user)

    seen = tickets_participants.objects.filter(user=request.user, ticket__in=base_query.values_list('id', flat=True)).values_list('ticket_id', 'seen')
    seen_elements = {}
    for see in seen:
        seen_elements[see[0]] = see[1]

    neededColumns = ['id', 'caption', 'c_date', 'type__name', 'state__name', 'assigned__username', 'deadline', 'closed', 'priority__color', 'customer__name', 'customer__hourly_rate', 'billing_estimated_time', 'close_date', 'last_action_date']
    """
    availableColumns = []
    tickets = get_ticket_model()
    t = tickets()
    for field in t._meta.fields:
        if field.name in neededColumns:
            availableColumns.append(field.name)
    """
    result = ValuesQuerySetToDict(base_query.values(*neededColumns))

    for ele in result:
        ele['seen'] = 0
        if ele['id'] in seen_elements:
            if seen_elements[ele['id']]:
                ele['seen'] = 2
            else:
                ele['seen'] = 1

    return result
