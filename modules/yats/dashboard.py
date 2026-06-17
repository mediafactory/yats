# -*- coding: utf-8 -*-
"""
Dashboard data layer.

Aggregations and per-widget querysets for the start-page dashboard.
Visibility follows the same rule as the ticket list (`table()` in tickets.py):
non-staff users only see tickets of their own organisation.

`deadline` lives only on the web `test` subclass of `tickets`, never on the base
model - the due/overdue widget degrades gracefully when the active ticket model
has no such field.
"""
from django.db.models import Count
from django.utils import timezone
from yats.shortcuts import get_ticket_model


# Widgets shipped out of the box. Order here is the default order; each user can
# reorder / hide them, persisted as JSON in UserProfile.dashboard_config.
DEFAULT_WIDGETS = ['metrics', 'my_open', 'due', 'chart_state', 'chart_priority', 'chart_assigned']


def get_default_config():
    return [{'id': wid, 'visible': True} for wid in DEFAULT_WIDGETS]


def normalize_config(config):
    """Merge a stored config with DEFAULT_WIDGETS so newly added widgets show up
    and removed/unknown ids are dropped. Returns a list of {'id', 'visible'}."""
    if not isinstance(config, list):
        return get_default_config()

    known = set(DEFAULT_WIDGETS)
    seen = set()
    result = []
    for entry in config:
        if not isinstance(entry, dict):
            continue
        wid = entry.get('id')
        if wid in known and wid not in seen:
            result.append({'id': wid, 'visible': bool(entry.get('visible', True))})
            seen.add(wid)
    # append any widget the stored config didn't know about yet
    for wid in DEFAULT_WIDGETS:
        if wid not in seen:
            result.append({'id': wid, 'visible': True})
    return result


def get_visible_tickets(request):
    """Base queryset honouring the org visibility rule used by table()."""
    tic = get_ticket_model().objects.all()
    if not request.user.is_staff:
        tic = tic.filter(customer=request.organisation)
    return tic


def _has_deadline():
    return any(f.name == 'deadline' for f in get_ticket_model()._meta.get_fields())


def widget_my_open(request):
    """My assigned, still-open tickets, highest priority first."""
    return get_visible_tickets(request) \
        .filter(assigned=request.user, closed=False) \
        .select_related('priority', 'state', 'type', 'customer') \
        .order_by('-priority', '-id')[:20]


def widget_due(request):
    """Open tickets with a deadline, soonest first (overdue float to the top).
    Empty when the active ticket model has no deadline field."""
    if not _has_deadline():
        return None
    return get_visible_tickets(request) \
        .filter(closed=False, deadline__isnull=False) \
        .select_related('priority', 'state', 'customer') \
        .order_by('deadline')[:20]


def widget_metrics(request):
    """Headline counters."""
    visible = get_visible_tickets(request)
    open_q = visible.filter(closed=False)

    # start of the current ISO week (Monday 00:00, local time)
    now = timezone.localtime()
    week_start = (now - timezone.timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)

    return {
        'open_total': open_q.count(),
        'my_open': open_q.filter(assigned=request.user).count(),
        'unassigned': open_q.filter(assigned__isnull=True).count(),
        'closed_this_week': visible.filter(closed=True, close_date__gte=week_start).count(),
    }


def _counts_by(request, field, label_field):
    """Open-ticket counts grouped by a related field, ready for Chart.js.
    Returns {'labels': [...], 'data': [...]}."""
    rows = get_visible_tickets(request) \
        .filter(closed=False) \
        .values(label_field) \
        .annotate(c=Count('id')) \
        .order_by('-c')
    labels, data = [], []
    for row in rows:
        labels.append(row[label_field] or '-')
        data.append(row['c'])
    return {'labels': labels, 'data': data}


def widget_chart_state(request):
    return _counts_by(request, 'state', 'state__name')


def widget_chart_priority(request):
    return _counts_by(request, 'priority', 'priority__name')


def widget_chart_assigned(request):
    return _counts_by(request, 'assigned', 'assigned__username')
