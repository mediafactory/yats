# -*- coding: utf-8 -*-
"""In-process CalDAV verification for the embedded Radicale 3.x (modules/dav)."""
import base64
import json
import os
import warnings

warnings.filterwarnings('ignore')

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth.models import User
from django.test import Client
from django.test.utils import setup_test_environment

setup_test_environment()

# Fresh schema + seed data.
call_command('migrate', run_syncdb=True, verbosity=0)
call_command('flush', interactive=False, verbosity=0)
call_command('loaddata', 'vagrant/init_db.json', verbosity=0)

from yats.models import tickets_reports

admin = User.objects.get(username='admin')
admin.set_password('test')
admin.is_staff = True
admin.save()
AUTH = 'Basic ' + base64.b64encode(b'admin:test').decode()

# Create a saved report (= a CalDAV collection) matching all tickets.
rep = tickets_reports(
    name='All Open', c_user=admin, u_user=admin,
    search=json.dumps({'condition': 'AND', 'rules': [], 'valid': True}),
)
rep.save(user=admin)
print('report slug:', rep.slug)

c = Client(enforce_csrf_checks=False)

def show(label, resp):
    body = resp.content.decode('utf-8', 'replace')
    print(f'\n### {label} -> HTTP {resp.status_code}')
    print(body[:600])

# 1) OPTIONS (no auth) — capability discovery
show('OPTIONS /tickets/dav/', c.options('/tickets/dav/'))

# 2) PROPFIND principal, depth 1 — should list the report collection
show('PROPFIND /tickets/dav/admin/ (depth 1)',
     c.generic('PROPFIND', '/tickets/dav/admin/', b'', 'application/xml',
               HTTP_AUTHORIZATION=AUTH, HTTP_DEPTH='1'))

# 3) PROPFIND the calendar collection, depth 1 — should list VTODO items (0 so far)
show('PROPFIND /tickets/dav/admin/all-open/ (depth 1)',
     c.generic('PROPFIND', '/tickets/dav/admin/all-open/', b'', 'application/xml',
               HTTP_AUTHORIZATION=AUTH, HTTP_DEPTH='1'))

# 4) GET the collection — serialized VCALENDAR
show('GET /tickets/dav/admin/all-open/',
     c.get('/tickets/dav/admin/all-open/', HTTP_AUTHORIZATION=AUTH))

# 5) PUT a new VTODO — should create a ticket
vtodo = (
    'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n'
    'BEGIN:VTODO\r\nUID:caldav-test-uid-1\r\nSUMMARY:Created via CalDAV\r\n'
    'DESCRIPTION:hello from caldav\r\nEND:VTODO\r\nEND:VCALENDAR\r\n'
)
before = tickets_reports.objects.model  # noqa (placeholder)
from yats.shortcuts import get_ticket_model
TM = get_ticket_model()
n_before = TM.objects.count()
show('PUT /tickets/dav/admin/all-open/caldav-test-uid-1.ics',
     c.generic('PUT', '/tickets/dav/admin/all-open/caldav-test-uid-1.ics',
               vtodo.encode(), 'text/calendar', HTTP_AUTHORIZATION=AUTH))
n_after = TM.objects.count()
print(f'\n>>> tickets before PUT: {n_before}, after PUT: {n_after}')
if n_after > n_before:
    t = TM.objects.get(uuid='caldav-test-uid-1')
    print(f'>>> CREATED ticket pk={t.pk} caption={t.caption!r} desc={t.description!r}')

# 6) Round-trip: GET the collection again — the new ticket must appear as VTODO.
rt = c.get('/tickets/dav/admin/all-open/', HTTP_AUTHORIZATION=AUTH)
body = rt.content.decode('utf-8', 'replace')
print('\n### Round-trip GET contains the new VTODO:',
      'caldav-test-uid-1' in body and 'Created via CalDAV' in body)

# 7) Close path: PUT the same VTODO with STATUS:COMPLETED — ticket must close.
vtodo_done = (
    'BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//test//EN\r\n'
    'BEGIN:VTODO\r\nUID:caldav-test-uid-1\r\nSUMMARY:Created via CalDAV\r\n'
    'STATUS:COMPLETED\r\nEND:VTODO\r\nEND:VCALENDAR\r\n'
)
r = c.generic('PUT', '/tickets/dav/admin/all-open/caldav-test-uid-1.ics',
              vtodo_done.encode(), 'text/calendar', HTTP_AUTHORIZATION=AUTH)
t.refresh_from_db()
print(f'### Close via CalDAV (STATUS:COMPLETED) -> HTTP {r.status_code}; ticket.closed={t.closed}')
