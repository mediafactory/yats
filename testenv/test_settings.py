# Test-environment settings overrides.
# Imports the real project settings (driven by YATS_CONFIG=testenv/test.ini),
# then swaps out the two services the local box doesn't have:
#   - memcached  -> in-process LocMem cache
#   - Xapian     -> Haystack simple backend (DB-backed search, no native libs)
# Use with: DJANGO_SETTINGS_MODULE=test_settings  (test_settings on PYTHONPATH).
from web.settings import *  # noqa: F401,F403

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    }
}

# Dev server: accept any host.
ALLOWED_HOSTS = ['*']
