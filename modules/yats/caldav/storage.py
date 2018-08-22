# Copyright (C) 2014 Okami, okami@fuzetsu.info

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

import json
import os
import logging
import vobject

from datetime import datetime

from contextlib import contextmanager
from radicale import ical

from yats.shortcuts import get_ticket_model, build_ticket_search
from yats.models import tickets_reports, UserProfile

from django.contrib.auth.models import AnonymousUser, User

from djradicale.models import DBCollection, DBItem, DBProperties

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
            ical.Header('PRODID:-//Radicale//NONSGML Radicale Server//EN'),
            ical.Header('VERSION:%s' % self.version))

    def delete(self):
        DBItem.objects.filter(collection__path=self.path).delete()
        DBCollection.objects.filter(path=self.path).delete()
        DBProperties.objects.filter(path=self.path).delete()

    def append(self, name, text):
        #import pydevd
        #pydevd.settrace('192.168.33.1', 5678)
        new_items = self._parse(text, ICAL_TYPES, name)
        timezones = list(filter(
            lambda x: x.tag == ical.Timezone.tag, new_items.values()))

        for new_item in new_items.values():
            if new_item.tag == ical.Timezone.tag:
                continue

            collection, ccreated = DBCollection.objects.get_or_create(
                path=self.path, parent_path=os.path.dirname(self.path))
            item, icreated = DBItem.objects.get_or_create(
                collection=collection, name=name)

            item.text = ical.serialize(
                self.tag, self.headers, [new_item] + timezones)
            item.save()

    def remove(self, name):
        DBItem.objects.filter(collection__path=self.path, name=name).delete()

    # def replace(self, name, text):
    #     raise NotImplementedError

    @property
    def text(self):
        return ical.serialize(self.tag, self.headers, self.items.values())

    @classmethod
    def children(cls, path):
        #import pydevd
        #pydevd.settrace('192.168.33.1', 5678)

        request = cls._getRequestFromUrl(path)

        children = list(tickets_reports.objects.filter(c_user=request.user).values_list('name', flat=True))
        children = ['admin/%s.ics' % itm for itm in children]
        return map(cls, children)

    @classmethod
    def is_node(cls, path):
        #import pydevd
        #pydevd.settrace('192.168.33.1', 5678)
        result = True
        if path == 'admin' or 'ics' in path:
            return result

        if path:
            result = (
                DBCollection.objects
                .filter(parent_path=path or '').exists())
        return result

    @classmethod
    def is_leaf(cls, path):
        #import pydevd
        #pydevd.settrace('192.168.33.1', 5678)
        result = False
        if path and len(path.split('/')) > 1:
            try:
                request = cls._getRequestFromUrl(path)
                rep = tickets_reports.objects.get(pk=cls._getReportFromUrl(path))
                tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
                search_params, tic = build_ticket_search(request, tic, {}, json.loads(rep.search))

                result = (tic.exists())

            except:
                import sys
                a = sys.exc_info()

        return result

    @property
    def last_modified(self):
        try:
            collection = DBCollection.objects.get(path=self.path)
        except DBCollection.DoesNotExist:
            pass
        else:
            if collection.last_modified:
                return datetime.strftime(
                    collection.last_modified, '%a, %d %b %Y %H:%M:%S %z')

    @property
    def tag(self):
        with self.props as props:
            if 'tag' not in props:
                if self.path.endswith(('.vcf', '/carddav')):
                    props['tag'] = 'VADDRESSBOOK'
                else:
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
        if old_properties != properties and DBCollection.objects.filter(path=self.path).exists():
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
            rep = tickets_reports.objects.get(pk=self._getReportFromUrl(self.path))
            tic = get_ticket_model().objects.select_related('type', 'state', 'assigned', 'priority', 'customer').all()
            search_params, tic = build_ticket_search(request, tic, {}, json.loads(rep.search))

            #import pydevd
            #pydevd.settrace('192.168.33.1', 5678)

            for item in tic:
                text = self._itemToICal(item)
                items.update(self._parse(text, ICAL_TYPES))

        except:
            import sys
            a = sys.exc_info()

        return items

    @classmethod
    def _getRequestFromUrl(cls, path):
        request = FakeRequest()
        request.user = User.objects.get(username='admin')
        request.organisation = UserProfile.objects.get(user=request.user).organisation
        return request

    @classmethod
    def _getReportFromUrl(cls, path):
        if '.ics' in path:
            file = path.split('/')[-1]
            file = file.replace('.ics', '')
            repid = tickets_reports.objects.get(name=file).pk
            return repid
        return 0

    @classmethod
    def _itemToICal(cls, item):
        cal = vobject.iCalendar()
        cal.add('vtodo')
        cal.vtodo.add('summary').value = item.caption
        cal.vtodo.add('uid').value = str(item.uuid)
        cal.vtodo.add('created').value = item.c_date
        if item.description:
            cal.vtodo.add('description').value = item.description
        if item.deadline:
            #cal.vtodo.add('dstart').value = item.deadline
            cal.vtodo.add('due').value = item.deadline
            cal.vtodo.add('valarm')
            cal.vtodo.valarm.add('uuid').value = '%s-%s' % (str(item.uuid), item.pk)
            cal.vtodo.valarm.add('x-wr-alarmuid').value = '%s-%s' % (str(item.uuid), item.pk)
            cal.vtodo.valarm.add('action').value = 'DISPLAY'
            cal.vtodo.valarm.add('x-apple-proximity').value = 'DEPART'
            cal.vtodo.valarm.add('description').value = 'Erinnerung an ein Ereignis'
            #cal.vtodo.valarm.add('trigger').value =
            #TRIGGER;VALUE=DATE-TIME:20180821T200000Z

        cal.vtodo.add('x-radicale-name').value = '%s.ics' % str(item.uuid)
        return cal.serialize()
