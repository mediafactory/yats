# -*- coding: utf-8 -*-
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.settings")
os.environ.setdefault("PYTHONPATH", "/vagrant_modules/pysrc/")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# http://blog.dscpl.com.au/2008/12/using-modwsgi-when-developing-django.html
import web.monitor
#web.monitor.start(interval=1.0)
