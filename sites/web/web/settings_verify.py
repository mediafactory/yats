# -*- coding: utf-8 -*-
"""
Verification overlay settings for the Django 5.2 migration (Phase 1).

Imports the real project settings and neutralizes the heavy/optional backends
(Xapian, memcached, clamav, fixed filesystem paths) so that `check`, `migrate`
and `runserver` can run on a developer machine WITHOUT the full system stack.
The signal this produces is about Django 5.2 compatibility, not missing C libs.

Usage:
    DJANGO_SETTINGS_MODULE=web.settings_verify python manage.py check
"""
import os
import tempfile

from web.settings import *  # noqa: F401,F403

_TMP = tempfile.gettempdir()

# Search: drop the Xapian backend (no native deps to build).
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}

# Cache: no running memcached required.
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

# DB: writable temp sqlite instead of the hardcoded /var/web/... path.
DATABASES['default']['ENGINE'] = 'django.db.backends.sqlite3'  # noqa: F405
DATABASES['default']['NAME'] = os.path.join(_TMP, 'yats_verify.sqlite')  # noqa: F405

# No clamav daemon connection on uploads.
FILE_UPLOAD_VIRUS_SCAN = False

# Filesystem paths -> temp dirs.
STATIC_ROOT = os.path.join(_TMP, 'yats_verify_static')
FILE_UPLOAD_PATH = os.path.join(_TMP, 'yats_verify_files') + os.sep
TEMP_ROOT = _TMP + os.sep

# Logging: console only (the project's RotatingFileHandler points at /var/web/...).
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {'level': 'DEBUG', 'class': 'logging.StreamHandler'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
