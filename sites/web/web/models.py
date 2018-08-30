# -*- coding: utf-8 -*-
from django.db import models
from django.utils.functional import lazy
from django.core.cache import cache
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from yats.models import tickets
from yats.models import base

import datetime
import base64
import httplib2
try:
    import json
except ImportError:
    from django.utils import simplejson as json

class ticket_component(base):

    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

    class Meta:
        verbose_name = _('module')
        verbose_name_plural = _(u'modules')
        ordering = ['name']

def getGibthubTags():
    owner = settings.GITHUB_OWNER
    repo = settings.GITHUB_REPO
    user = settings.GITHUB_USER
    password = settings.GITHUB_PASS

    if not owner or not repo:
        return ()

    cache_name = 'yats.%s.%s.tags.github' % (owner, repo)
    tags = cache.get(cache_name)
    if tags:
        return tuple(reversed(sorted(tags)))

    # https://developer.github.com/v3/repos/#list-tags
    result = []
    headers = {
               'Accept': 'application/vnd.github.v3+json',
               'User-Agent': 'yats'
               }
    if user:
        headers['Authorization'] = 'Basic %s' % base64.b64encode('%s:%s' % (user, password))

    try:
        h = httplib2.Http()
        header, content = h.request('https://api.github.com/repos/%s/%s/tags' % (owner, repo), 'GET', headers=headers)
        if header['status'] != '200':
            print 'ERROR fetching data from GitHub: %s' % content
            return ()

    except:
        print 'ERROR fetching data from GitHub'
        return ()

    tags = json.loads(content)

    for tag in tags:
        result.append((tag['name'], tag['name'],))

    cache.set(cache_name, result, 60 * 10)
    return tuple(reversed(sorted(result)))


BILLING_TYPE_CHOICES = (
    ('service', 'service'),
    ('development', 'development'),
)

class test(tickets):
    component = models.ForeignKey(ticket_component, verbose_name=_('component'))
    version = models.CharField(_('version'), max_length=255, choices=lazy(getGibthubTags, tuple)())
    keywords = models.CharField(_('keywords'), max_length=255, blank=True)
    reproduction = models.TextField(_('reproduction'), null=True)
    billing_needed = models.NullBooleanField(_('billing needed'), default=True)
    billing_done = models.NullBooleanField(_('billing done'), default=None)
    billing_reason = models.TextField(_('billing reason'), null=True, blank=True)
    billing_estimated_time = models.FloatField(_('billing estimated time'), null=True, blank=True)
    billing_time_taken = models.FloatField(_('billing tike taken'), null=True, blank=True)
    billing_type = models.CharField(_('billing type'), max_length=255, choices=BILLING_TYPE_CHOICES, null=True, blank=True)
    solution = models.TextField(_('solution'), null=True, blank=True)
    fixed_in_version = models.CharField(_('fixed in version'), max_length=255, choices=lazy(getGibthubTags, tuple)(), blank=True)
    deadline = models.DateTimeField(_('deadline'), null=True, blank=True)

    def is_late(self):
        if self.deadline < datetime.date.today():
            return 2
        if self.deadline < datetime.date.today() + datetime.timedelta(days=7):
            return 1
        return 0
