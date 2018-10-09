# -*- coding: utf-8 -*-
import json
import logging
import vobject

from datetime import datetime

from contextlib import contextmanager
from radicale import ical

from yats.shortcuts import get_ticket_model, build_ticket_search_ext, touch_ticket, remember_changes, mail_ticket, jabber_ticket, check_references, add_history, mail_comment, jabber_comment
from yats.models import tickets_reports, UserProfile, get_flow_end, tickets_comments, ticket_resolution, get_default_resolution, convertPrio
from yats.forms import SimpleTickets

from django.contrib.auth.models import AnonymousUser, User
from django.http import QueryDict
from django.conf import settings
from django.utils import timezone
from django.utils.translation import ugettext as _

from djradicale.models import DBProperties

logger = logging.getLogger('djradicale')

ICAL_TYPES = (
    ical.Event,
    ical.Todo,
    ical.Journal,
    # ical.Card,
    ical.Timezone,
)

class FakeRequest:
    def __init__(self):
        self.GET = {}
        self.POST = {}
        self.session = {}
        self.user = AnonymousUser()

class Collection(ical.Collection):
    @property
    def headers(self):
        return (
            ical.Header('PRODID:-//YATS//NONSGML Radicale Server//EN'),
            ical.Header('VERSION:%s' % self.version))

    def delete(self):
        repid = self._getReportFromUrl(self.path)
        tickets_reports.objects.get(pk=repid).delete()

    def append(self, name, text):
        new_items = self._parse(text, ICAL_TYPES, name)
        timezones = list(filter(
            lambda x: x.tag == ical.Timezone.tag, new_items.values()))

        request = self._getRequestFromUrl(self.path)

        for new_item in new_items.values():
            if new_item.tag == ical.Timezone.tag:
                continue

            if new_item.name not in self.items:
                self.items[new_item.name] = new_item

            text = ical.serialize(self.tag, self.headers, [new_item] + timezones)
            cal = vobject.readOne(text)

            # close ticket
            if hasattr(cal.vtodo, 'status') and cal.vtodo.status.value == 'COMPLETED':
                ticket = get_ticket_model()
                try:
                    flow_end = get_flow_end()
                    resolution = get_default_resolution()
                    close_comment = _('closed via CalDAV')

                    tic = ticket.objects.get(uuid=cal.vtodo.uid.value)
                    tic.resolution = resolution
                    tic.closed = True
                    tic.close_date = timezone.now()
                    tic.state = flow_end
                    tic.save(user=request.user)

                    com = tickets_comments()
                    com.comment = _('ticket closed - resolution: %(resolution)s\n\n%(comment)s') % {'resolution': resolution.name, 'comment': close_comment}
                    com.ticket = tic
                    com.action = 1
                    com.save(user=request.user)

                    check_references(request, com)

                    touch_ticket(request.user, tic.id)

                    add_history(request, tic, 1, close_comment)

                    mail_comment(request, com.pk)
                    jabber_comment(request, com.pk)

                except:
                    pass

            # change or new
            else:
                params = {
                    'caption': cal.vtodo.summary.value,
                    'description': cal.vtodo.description.value if hasattr(cal.vtodo, 'description') else None,
                    'uuid': cal.vtodo.uid.value,
                    'deadline': cal.vtodo.due.value if hasattr(cal.vtodo, 'due') else None,
                    'priority': convertPrio(cal.vtodo.priority.value) if hasattr(cal.vtodo, 'priority') else None
                }
                fakePOST = QueryDict(mutable=True)
                fakePOST.update(params)

                form = SimpleTickets(fakePOST)
                if form.is_valid():
                    cd = form.cleaned_data
                    ticket = get_ticket_model()

                    # change ticket
                    try:
                        tic = ticket.objects.get(uuid=cal.vtodo.uid.value)
                        tic.caption = cd['caption']
                        tic.description = cd['description']
                        tic.priority = cd['priority']
                        # tic.assigned = cd['assigned']
                        tic.deadline = cd['deadline']
                        tic.save(user=request.user)

                    # new ticket
                    except ticket.DoesNotExist:
                        tic = ticket()
                        tic.caption = cd['caption']
                        tic.description = cd['description']
                        if 'priority' not in cd or not cd['priority']:
                            if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_PRIORITY') and settings.KEEP_IT_SIMPLE_DEFAULT_PRIORITY:
                                tic.priority_id = settings.KEEP_IT_SIMPLE_DEFAULT_PRIORITY
                        else:
                            tic.priority = cd['priority']
                        tic.assigned = request.user
                        if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER') and settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER:
                            if settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER == -1:
                                tic.customer = request.organisation
                            else:
                                tic.customer_id = settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOME
                        if hasattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT') and settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT:
                            tic.component_id = settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT
                        tic.deadline = cd['deadline']
                        tic.uuid = cal.vtodo.uid.value
                        tic.save(user=request.user)

                    if tic.assigned:
                        touch_ticket(tic.assigned, tic.pk)

                    for ele in form.changed_data:
                        form.initial[ele] = ''
                    remember_changes(request, form, tic)

                    touch_ticket(request.user, tic.pk)

                    mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT, is_api=True)
                    jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT, is_api=True)

                else:
                    raise Exception(form.errors)

    def remove(self, name):
        pass

    def replace(self, name, text):
        self.append(name, text)

    @property
    def text(self):
        return ical.serialize(self.tag, self.headers, self.items.values())

    @classmethod
    def children(cls, path):
        """Yield the children of the collection at local ``path``."""
        request = cls._getRequestFromUrl(path)
        children = list(tickets_reports.objects.filter(active_record=True, c_user=request.user).values_list('slug', flat=True))
        children = ['%s/%s.ics' % (request.user.username, itm) for itm in children]
        return map(cls, children)

    @classmethod
    def is_node(cls, path):
        """Return ``True`` if relative ``path`` is a node.

        A node is a WebDAV collection whose members are other collections.

        """
        request = cls._getRequestFromUrl(path)

        if path == request.user.username:
            return True
        else:
            return False

    @classmethod
    def is_leaf(cls, path):
        """Return ``True`` if relative ``path`` is a leaf.

        A leaf is a WebDAV collection whose members are not collections.

        """
        result = False
        if '.ics' in path:
            try:
                request = cls._getRequestFromUrl(path)
                rep = tickets_reports.objects.get(active_record=True, pk=cls._getReportFromUrl(path))
                tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
                search_params, tic = build_ticket_search_ext(request, tic, json.loads(rep.search))

                result = (tic.exists())

            except:
                import sys
                a = sys.exc_info()

        return result

    @property
    def last_modified(self):
        try:
            request = self._getRequestFromUrl(self.path)
            rep = tickets_reports.objects.get(active_record=True, pk=self._getReportFromUrl(self.path))
            tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
            search_params, tic = build_ticket_search_ext(request, tic, json.loads(rep.search))
            date = tic.latest('u_date')
            return datetime.strftime(
                date.last_action_date, '%a, %d %b %Y %H:%M:%S %z')

        except:
            import sys
            a = sys.exc_info()

    @property
    def tag(self):
        with self.props as props:
            if 'tag' not in props:
                props['tag'] = 'VCALENDAR'
            return props['tag']

    @property
    @contextmanager
    def props(self):
        # On enter
        properties = {}
        try:
            props = DBProperties.objects.get(path=self.path)
        except DBProperties.DoesNotExist:
            pass
        else:
            properties.update(json.loads(props.text))
        old_properties = properties.copy()
        yield properties
        # On exit
        if old_properties != properties:
            props, created = DBProperties.objects.get_or_create(path=self.path)
            props.text = json.dumps(properties)
            props.save()

    @property
    def items(self):
        items = {}
        try:
            request = self._getRequestFromUrl(self.path)
            if self.path == request.user.username:
                return items
            rep = tickets_reports.objects.get(active_record=True, pk=self._getReportFromUrl(self.path))
            tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
            search_params, tic = build_ticket_search_ext(request, tic, json.loads(rep.search))

            for item in tic:
                text = self._itemToICal(item)
                items.update(self._parse(text, ICAL_TYPES))

        except:
            import sys
            a = sys.exc_info()

        return items

    @classmethod
    def _getRequestFromUrl(cls, path):
        user = path.split('/')[0]
        request = FakeRequest()
        request.user = User.objects.get(username=user)
        request.organisation = UserProfile.objects.get(user=request.user).organisation
        return request

    @classmethod
    def _getReportFromUrl(cls, path):
        if '.ics' in path:
            file = path.split('/')[-1]
            file = file.replace('.ics', '')
            repid = tickets_reports.objects.get(active_record=True, slug=file).pk
            return repid
        return 0

    @classmethod
    def _itemToICal(cls, item):
        cal = vobject.iCalendar()
        cal.add('vtodo')
        cal.vtodo.add('summary').value = item.caption
        cal.vtodo.add('uid').value = str(item.uuid)
        cal.vtodo.add('created').value = item.c_date
        if item.closed:
            cal.vtodo.add('status').value = 'COMPLETED'
        if item.priority:
            cal.vtodo.add('priority').value = str(item.priority.caldav)
        else:
            cal.vtodo.add('priority').value = '0'
        if item.description:
            cal.vtodo.add('description').value = item.description
        if item.deadline:
            #cal.vtodo.add('dstart').value = item.deadline
            cal.vtodo.add('due').value = item.deadline
            cal.vtodo.add('valarm')
            cal.vtodo.valarm.add('uuid').value = '%s-%s' % (str(item.uuid), item.pk)
            cal.vtodo.valarm.add('x-wr-alarmuid').value = '%s-%s' % (str(item.uuid), item.pk)
            cal.vtodo.valarm.add('action').value = 'DISPLAY'
            #cal.vtodo.valarm.add('x-apple-proximity').value = 'DEPART'
            cal.vtodo.valarm.add('description').value = 'Erinnerung an ein Ereignis'
            #cal.vtodo.valarm.add('trigger').value =
            #TRIGGER;VALUE=DATE-TIME:20180821T200000Z

        cal.vtodo.add('x-radicale-name').value = '%s.ics' % str(item.uuid)
        return cal.serialize().decode('utf-8')
