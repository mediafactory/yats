# -*- coding: utf-8 -*- 
from django.contrib import admin
from models import ticket_component, ticket_system_version
from yats.admin import yatsAdmin

admin.site.register(ticket_component, yatsAdmin)
admin.site.register(ticket_system_version, yatsAdmin)
