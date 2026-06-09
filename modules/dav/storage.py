# -*- coding: utf-8 -*-
"""
Radicale 3.x storage plugin for YATS — a *virtual* backend.

Unlike a normal filesystem storage, nothing is persisted as ``.ics`` files.
Instead the CalDAV tree is computed live from YATS data:

    {user}                        -> principal collection
    {user}/{report-slug}          -> a VCALENDAR collection (one saved report)
    {user}/{report-slug}/{uuid}.ics -> one VTODO item (one ticket)

The VTODO list of a report collection is rendered on every request from the
report's stored search query. Writes (PUT of a VTODO) are mapped back onto
tickets: a ``STATUS:COMPLETED`` closes the ticket, anything else creates or
updates it. This ports the behaviour of the old Radicale-1.x
``yats.caldav.storage`` to the Radicale-3.x plugin API.
"""
import json
import logging
import contextlib
import threading
from datetime import datetime
from email.utils import formatdate

import vobject
from vobject.icalendar import utc as _VOBJECT_UTC

from radicale import pathutils
from radicale import item as radicale_item
from radicale.storage import BaseStorage, BaseCollection

from django.conf import settings
from django.contrib.auth.models import AnonymousUser, User
from django.http import QueryDict
from django.utils import timezone
from django.utils.translation import gettext as _

logger = logging.getLogger('dav')

# A single process-wide lock — the virtual storage holds no file handles, but
# Radicale still expects acquire_lock() to behave like a real lock.
_LOCK = threading.RLock()


class FakeRequest:
    """Minimal request stand-in for yats.shortcuts.build_ticket_search_ext."""
    def __init__(self):
        self.GET = {}
        self.POST = {}
        self.session = {}
        self.user = AnonymousUser()
        self.organisation = None


def _request_for(username):
    from yats.models import UserProfile
    request = FakeRequest()
    request.user = User.objects.get(username=username)
    request.organisation = UserProfile.objects.get(user=request.user).organisation
    return request


def _report_for(username, slug):
    from yats.models import tickets_reports
    return tickets_reports.objects.get(active_record=True, c_user__username=username, slug=slug)


def _tickets_for(request, report):
    from yats.shortcuts import build_ticket_search_ext, get_ticket_model
    tic = get_ticket_model().objects.select_related(
        'type', 'state', 'assigned', 'priority', 'customer').all()
    _params, tic = build_ticket_search_ext(request, tic, json.loads(report.search))
    return tic


def _ical_dt(value):
    """Make a datetime serializable by vobject.

    With ``USE_TZ=True`` YATS datetimes are timezone-aware with the stdlib UTC
    tzinfo, which vobject cannot map to a TZID. Re-anchor aware datetimes to
    vobject's own UTC so they serialize as a Zulu (``...Z``) timestamp.
    """
    if value is not None and getattr(value, 'tzinfo', None) is not None:
        return value.astimezone(_VOBJECT_UTC)
    return value


def _item_to_ical(item):
    """Render one ticket as a VTODO VCALENDAR string (ported 1:1)."""
    cal = vobject.iCalendar()
    cal.add('vtodo')
    cal.vtodo.add('summary').value = item.caption
    cal.vtodo.add('uid').value = str(item.uuid)
    cal.vtodo.add('created').value = _ical_dt(item.c_date)
    if item.closed:
        cal.vtodo.add('status').value = 'COMPLETED'
    if item.priority:
        cal.vtodo.add('priority').value = str(item.priority.caldav)
    else:
        cal.vtodo.add('priority').value = '0'
    if item.description:
        cal.vtodo.add('description').value = item.description
    if item.show_start:
        cal.vtodo.add('due').value = _ical_dt(item.show_start)
        cal.vtodo.add('valarm')
        cal.vtodo.valarm.add('uuid').value = '%s-%s' % (str(item.uuid), item.pk)
        cal.vtodo.valarm.add('x-wr-alarmuid').value = '%s-%s' % (str(item.uuid), item.pk)
        cal.vtodo.valarm.add('action').value = 'DISPLAY'
        cal.vtodo.valarm.add('description').value = 'Erinnerung an ein Ereignis'
    return cal.serialize()


class Collection(BaseCollection):

    def __init__(self, storage, path):
        self._storage = storage
        # Accept paths with or without surrounding slashes (sanitize is
        # idempotent; strip_path then yields the canonical slash-free form).
        self._path = pathutils.strip_path(pathutils.sanitize_path(path))
        self._attrs = self._path.split('/') if self._path else []

    # --- identity -------------------------------------------------------
    @property
    def path(self):
        return self._path

    @property
    def _is_calendar(self):
        return len(self._attrs) == 2

    @property
    def _is_principal(self):
        return len(self._attrs) == 1

    def _owner(self):
        return self._attrs[0] if self._attrs else ''

    def _slug(self):
        return self._attrs[1] if self._is_calendar else None

    # --- existence / children (used by Storage.discover) ----------------
    def _exists(self):
        try:
            if not self._attrs:
                return True
            if self._is_principal:
                return User.objects.filter(username=self._owner()).exists()
            if self._is_calendar:
                _report_for(self._owner(), self._slug())
                return True
        except Exception:
            return False
        return False

    def _children(self):
        """Yield child collections (for a principal) or items (for a calendar)."""
        if self._is_principal:
            from yats.models import tickets_reports
            slugs = tickets_reports.objects.filter(
                active_record=True, c_user__username=self._owner()
            ).values_list('slug', flat=True)
            for slug in slugs:
                yield Collection(self._storage, '%s/%s' % (self._owner(), slug))
        elif self._is_calendar:
            yield from self.get_all()

    # --- metadata -------------------------------------------------------
    def get_meta(self, key=None):
        meta = {}
        if self._is_calendar:
            meta['tag'] = 'VCALENDAR'
            meta['C:supported-calendar-component-set'] = 'VTODO'
            try:
                meta['D:displayname'] = _report_for(self._owner(), self._slug()).name
            except Exception:
                meta['D:displayname'] = self._slug() or ''
        if key is None:
            return meta
        return meta.get(key)

    def set_meta(self, props):
        # Report metadata is managed in the YATS UI; ignore client-side changes.
        return

    @property
    def last_modified(self):
        try:
            if self._is_calendar:
                request = _request_for(self._owner())
                report = _report_for(self._owner(), self._slug())
                tic = _tickets_for(request, report)
                latest = tic.latest('u_date')
                return formatdate(latest.u_date.timestamp(), usegmt=True)
        except Exception:
            pass
        return formatdate(usegmt=True)

    # --- items ----------------------------------------------------------
    def get_all(self):
        if not self._is_calendar:
            return
        try:
            request = _request_for(self._owner())
            report = _report_for(self._owner(), self._slug())
        except Exception:
            logger.exception('dav: cannot resolve report for %r', self._path)
            return
        for ticket in _tickets_for(request, report):
            try:
                vobject_item = vobject.readOne(_item_to_ical(ticket))
            except Exception:
                logger.exception('dav: failed to render ticket %s', ticket.pk)
                continue
            yield radicale_item.Item(
                collection=self,
                vobject_item=vobject_item,
                href='%s.ics' % ticket.uuid,
            )

    def get_multi(self, hrefs):
        hrefs = set(hrefs)
        found = {}
        for item in self.get_all():
            if item.href in hrefs:
                found[item.href] = item
        for href in hrefs:
            yield href, found.get(href)

    def _get(self, href):
        for item in self.get_all():
            if item.href == href:
                return item
        return None

    # --- writes ---------------------------------------------------------
    def upload(self, href, item):
        request = _request_for(self._owner())
        vobject_item = item.vobject_item
        vtodo = getattr(vobject_item, 'vtodo', None)
        if vtodo is None:
            return item, None

        if hasattr(vtodo, 'status') and vtodo.status.value == 'COMPLETED':
            self._close_ticket(request, vtodo)
        else:
            self._create_or_update_ticket(request, vtodo)
        return item, None

    def delete(self, href=None):
        # Deleting the whole collection deletes the underlying report.
        if href is None and self._is_calendar:
            try:
                _report_for(self._owner(), self._slug()).delete()
            except Exception:
                logger.exception('dav: failed to delete report %r', self._path)
        # Deleting a single VTODO is intentionally a no-op (matches legacy
        # behaviour — tickets are not removed via CalDAV).
        return

    # --- ticket sync (ported from yats.caldav.storage.append) -----------
    def _close_ticket(self, request, vtodo):
        from yats.shortcuts import (get_ticket_model, touch_ticket,
                                    check_references, add_ticket_history,
                                    mail_comment, jabber_comment)
        from yats.models import (get_flow_end, tickets_comments,
                                 get_default_resolution)
        try:
            flow_end = get_flow_end()
            resolution = get_default_resolution()
            close_comment = _('closed via CalDAV')

            tic = get_ticket_model().objects.get(uuid=vtodo.uid.value)
            tic.resolution = resolution
            tic.closed = True
            tic.close_date = timezone.now()
            tic.state = flow_end
            tic.save(user=request.user)

            com = tickets_comments()
            com.comment = _('ticket closed - resolution: %(resolution)s\n\n%(comment)s') % {
                'resolution': resolution.name, 'comment': close_comment}
            com.ticket = tic
            com.action = 1
            com.save(user=request.user)

            check_references(request, com)
            touch_ticket(request.user, tic.id)
            add_ticket_history(request, tic, 1, close_comment)
            mail_comment(request, com.pk)
            jabber_comment(request, com.pk)
        except Exception:
            logger.exception('dav: failed to close ticket via CalDAV')

    def _create_or_update_ticket(self, request, vtodo):
        from yats.shortcuts import (get_ticket_model, touch_ticket,
                                    remember_ticket_changes, mail_ticket,
                                    jabber_ticket)
        from yats.models import convertPrio
        from yats.forms import SimpleTickets

        params = {
            'caption': vtodo.summary.value,
            'description': vtodo.description.value if hasattr(vtodo, 'description') else None,
            'uuid': vtodo.uid.value,
            'show_start': vtodo.due.value if hasattr(vtodo, 'due') else None,
            'priority': convertPrio(vtodo.priority.value) if hasattr(vtodo, 'priority') else None,
        }
        fakePOST = QueryDict(mutable=True)
        fakePOST.update(params)

        form = SimpleTickets(fakePOST)
        if not form.is_valid():
            raise Exception(form.errors)

        cd = form.cleaned_data
        ticket = get_ticket_model()
        try:
            tic = ticket.objects.get(uuid=vtodo.uid.value)
            tic.caption = cd['caption']
            tic.description = cd['description']
            tic.priority = cd['priority']
            tic.show_start = cd['show_start']
            tic.save(user=request.user)
        except ticket.DoesNotExist:
            tic = ticket()
            tic.caption = cd['caption']
            tic.description = cd['description']
            if not cd.get('priority'):
                if getattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_PRIORITY', None):
                    tic.priority_id = settings.KEEP_IT_SIMPLE_DEFAULT_PRIORITY
            else:
                tic.priority = cd['priority']
            tic.assigned = request.user
            if getattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER', None):
                if settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER == -1:
                    tic.customer = request.organisation
                else:
                    tic.customer_id = settings.KEEP_IT_SIMPLE_DEFAULT_CUSTOMER
            if getattr(settings, 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT', None):
                tic.component_id = settings.KEEP_IT_SIMPLE_DEFAULT_COMPONENT
            tic.show_start = cd['show_start']
            tic.uuid = vtodo.uid.value
            tic.save(user=request.user)

        if tic.assigned:
            touch_ticket(tic.assigned, tic.pk)
        for ele in form.changed_data:
            form.initial[ele] = ''
        remember_ticket_changes(request, form, tic)
        touch_ticket(request.user, tic.pk)
        mail_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_MAIL_RCPT, is_api=True)
        jabber_ticket(request, tic.pk, form, rcpt=settings.TICKET_NEW_JABBER_RCPT, is_api=True)


class Storage(BaseStorage):

    _collision_free = False

    def discover(self, path, depth="0", child_context_manager=None,
                 user_groups=set()):
        sane_path = pathutils.strip_path(path)
        attributes = sane_path.split('/') if sane_path else []

        # Item request: last component is a .ics file.
        if attributes and attributes[-1].endswith('.ics'):
            href = attributes[-1]
            collection = Collection(self, '/'.join(attributes[:-1]))
            if collection._exists():
                item = collection._get(href)
                if item is not None:
                    yield item
            return

        collection = Collection(self, sane_path)
        if not collection._exists():
            return
        yield collection

        if depth == "0":
            return

        for child in collection._children():
            yield child

    def move(self, item, to_collection, to_href):
        raise NotImplementedError("CalDAV move is not supported by YATS storage")

    def create_collection(self, href, items=None, props=None):
        # Reports (collections) are created in the YATS UI, not over CalDAV.
        # Return a transient handle so MKCALENDAR-style probes don't crash.
        logger.info('dav: create_collection ignored for %r (managed in YATS UI)', href)
        return Collection(self, href)

    @contextlib.contextmanager
    def acquire_lock(self, mode, user="", *args, **kwargs):
        with _LOCK:
            yield

    def verify(self):
        return True
