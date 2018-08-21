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

from datetime import datetime

from contextlib import contextmanager
from radicale import ical

from djradicale.models import DBCollection, DBItem, DBProperties

logger = logging.getLogger('djradicale')

ICAL_TYPES = (
    ical.Event,
    ical.Todo,
    ical.Journal,
    #ical.Card,
    ical.Timezone,
)


class Collection(ical.Collection):
    @property
    def headers(self):
        return (
            ical.Header('PRODID:-//YATS//NONSGML Radicale Server//EN'),
            ical.Header('VERSION:%s' % self.version))

    def delete(self):
        raise NotImplementedError("does not make sense")

    def append(self, name, text):
        raise NotImplementedError("TODO")

    def remove(self, name):
        raise NotImplementedError("does not make sense")

    # def replace(self, name, text):
    #     raise NotImplementedError

    @property
    def text(self):
        return ical.serialize(self.tag, self.headers, self.items.values())

    @classmethod
    def children(cls, path):
        children = list(
            DBCollection.objects
            .filter(parent_path=path or '')
            .values_list('path', flat=True))
        return map(cls, children)

    @classmethod
    def is_node(cls, path):
        result = True
        if path:
            result = (
                DBCollection.objects
                .filter(parent_path=path or '').exists())
        return result

    @classmethod
    def is_leaf(cls, path):
        result = False
        if path:
            result = (
                DBItem.objects
                .filter(collection__path=path or '').exists())
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
        for item in DBItem.objects.filter(collection__path=self.path):
            items.update(self._parse(item.text, ICAL_TYPES))
        return items