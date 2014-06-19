# -*- coding: utf-8 -*- 
from django.contrib import admin
from models import ticket_component
from yats.admin import yatsAdmin

admin.site.register(ticket_component, yatsAdmin)
