# -*- coding: utf-8 -*-
"""
Verification overlay for the Docker project settings (django_project.settings).

Same idea as web.settings_verify: load the real Docker settings and neutralize
heavy/optional backends so `check` can validate the Docker app wiring
(ROOT_URLCONF=django_project.urls, INSTALLED_APPS incl. 'dav', 'web') on a dev
machine without building the container or the system stack.

    DJANGO_SETTINGS_MODULE=django_project.settings_verify python -m django check
"""
import os
import tempfile

from django_project.settings import *  # noqa: F401,F403

_TMP = tempfile.gettempdir()

HAYSTACK_CONNECTIONS = {
    'default': {'ENGINE': 'haystack.backends.simple_backend.SimpleEngine'},
}
CACHES = {
    'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'},
}
DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'  # noqa: F405
DATABASES['default']['NAME'] = os.path.join(_TMP, 'yats_docker_verify.sqlite')  # noqa: F405
FILE_UPLOAD_VIRUS_SCAN = False
STATIC_ROOT = os.path.join(_TMP, 'yats_docker_verify_static')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
