# -*- coding: utf-8 -*- 
from django.db import models
from django.utils.functional import lazy
from django.core.cache import cache
from django.conf import settings
from yats.models import tickets, organisation
from yats.models import base

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
        return set(reversed(sorted(tags)))
    
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
    return set(reversed(sorted(result)))

class test(tickets):
    component = models.ForeignKey(ticket_component)
    version = models.CharField(max_length=255, choices=lazy(getGibthubTags, set)())
    keywords = models.CharField(max_length=255, blank=True)
    reproduction = models.TextField(null=True)
    billing_needed = models.NullBooleanField(default=None)
    billing_reason = models.TextField(null=True, blank=True)
    billing_done = models.NullBooleanField(default=None)
    solution = models.TextField(null=True, blank=True)
    fixed_in_version = models.CharField(max_length=255, choices=lazy(getGibthubTags, set)(), blank=True)
    deadline = models.DateField(null=True, blank=True)