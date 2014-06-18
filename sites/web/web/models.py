# -*- coding: utf-8 -*- 
from django.db import models
from yats.models import tickets, organisation
from yats.models import base

class ticket_component(base):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

class ticket_system_version(base):
    name = models.CharField(max_length=255)

    def __unicode__(self):
        return self.name

class test(tickets):
    component = models.ForeignKey(ticket_component)
    version = models.ForeignKey(ticket_system_version)
    keywords = models.CharField(max_length=255, blank=True)
    reproduction = models.TextField(null=True)
    billing_needed = models.BooleanField(default=False, )
    billing_reason = models.TextField(null=True, blank=True)
    billing_done = models.BooleanField(default=False)
    solution = models.TextField(null=True, blank=True)
    fixed_in_version = models.ForeignKey(ticket_system_version, related_name='+', null=True, blank=True)
    deadline = models.DateField(null=True, blank=True)
    
    form_excludes = ['billing_needed', 'billing_reason', 'billing_done', 'fixed_in_version', 'solution', 'assigned', 'priority']