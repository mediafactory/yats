# -*- coding: utf-8 -*-
#
# Per-web parameterization
# ------------------------
# A single settings module serves all webs (mf / bagarino / schiwago ...).
# Per-web values are read from an INI file whose path comes from the env var
# YATS_CONFIG (default /etc/yats/web.ini). Each gunicorn / process_tasks
# systemd unit sets its own YATS_CONFIG=/etc/yats/<site>.ini.
#
# When no INI is present (dev / local verification), every lookup falls back to
# the historical hardcoded default, so the dev and verify setups keep working
# unchanged.
import os
import configparser

# interpolation=None: INI values are taken literally — SECRET_KEY / passwords
# legitimately contain '%' and must not be treated as ConfigParser interpolation.
_cfg = configparser.ConfigParser(interpolation=None)
_cfg.optionxform = str  # keep key case
YATS_CONFIG = os.environ.get('YATS_CONFIG', '/etc/yats/web.ini')
_cfg.read(YATS_CONFIG)  # silently does nothing if the file is absent


def _get(section, key, default=None):
    try:
        val = _cfg.get(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError):
        return default
    return val if val != '' else default


def _getbool(section, key, default=False):
    try:
        return _cfg.getboolean(section, key)
    except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
        return default


def _getint(section, key, default):
    val = _get(section, key)
    return int(val) if val is not None else default


def _getlist(section, key, default):
    """Comma-separated INI value -> list of stripped strings."""
    val = _get(section, key)
    if val is None:
        return default
    return [x.strip() for x in val.split(',') if x.strip()]


DEBUG = _getbool('debug', 'DEBUG', True)
# DEBUG_PROPAGATE_EXCEPTIONS = DEBUG
XMLRPC_DEBUG = False
_domain = _get('site', 'DOMAIN')
ALLOWED_HOSTS = [_domain] if _domain else ['*']
CSRF_TRUSTED_ORIGINS = ['https://%s' % _domain] if _domain else []
# mf-router / OpenResty terminates TLS and forwards X-Forwarded-Proto.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

USE_TZ = True
SITE_ID = 1

TESTSYTEM = _getbool('debug', 'TESTSYTEM', True)

# Recipients of Django error mails (per web, from INI). Comma-separated;
# entries may be a bare address or "Name <addr>".
def _parse_admin(entry):
    if '<' in entry and '>' in entry:
        name, addr = entry.split('<', 1)
        return (name.strip() or 'admin', addr.rstrip('>').strip())
    return ('admin', entry)


ADMINS = [_parse_admin(a) for a in _getlist('site', 'ADMINS', [])]
MANAGERS = ADMINS

EMAIL_SUBJECT_PREFIX = _get('mail', 'EMAIL_SUBJECT_PREFIX', 'yats-dev')
EMAIL_HOST = _get('mail', 'EMAIL_HOST', 'localhost')
EMAIL_PORT = int(_get('mail', 'EMAIL_PORT', '25'))
SERVER_EMAIL = _get('mail', 'SERVER_EMAIL', 'develope@mediafactory.de')
EMAIL_HOST_USER = _get('mail', 'EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = _get('mail', 'EMAIL_HOST_PASSWORD', '')

JABBER_HOST_USER = _get('jabber', 'JABBER_HOST_USER', '')
JABBER_HOST_PASSWORD = _get('jabber', 'JABBER_HOST_PASSWORD', '')
JABBER_TEST_RECIPIENT = _get('jabber', 'JABBER_TEST_RECIPIENT', '')

SIGNAL_BIN = _get('signal', 'SIGNAL_BIN', 'sudo /usr/local/bin/signal-cli')
SIGNAL_CONFIG = _get('signal', 'SIGNAL_CONFIG', '')
SIGNAL_USERNAME = _get('signal', 'SIGNAL_USERNAME', '')
SIGNAL_TEST_RECIPIENT = _get('signal', 'SIGNAL_TEST_RECIPIENT', '')

# DATABASE_ROUTERS = ['web.routers.ModelRouter']
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
_db_engine = _get('database', 'DATABASE_ENGINE', 'django.db.backends.sqlite3')
DATABASES = {
    'default': {
        'ENGINE': _db_engine,
        'NAME': _get('database', 'DATABASE_NAME', '/var/web/yats/db/yats2.sqlite'),
        'USER': _get('database', 'DATABASE_USER', 'root'),
        'PASSWORD': _get('database', 'DATABASE_PASSWORD'),
        'HOST': _get('database', 'DATABASE_HOST', 'localhost'),
        'PORT': _get('database', 'DATABASE_PORT'),
    }
}
if _db_engine.endswith('sqlite3'):
    # sqlite needs a busy timeout; network engines (PostgreSQL) do not.
    DATABASES['default']['OPTIONS'] = {'timeout': 20}
elif _getbool('database', 'ATOMIC_REQUESTS', False):
    DATABASES['default']['ATOMIC_REQUESTS'] = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.PyMemcacheCache',
        'LOCATION': _get('cache', 'LOCATION', '127.0.0.1:11211'),
        # Distinct prefix per web so the shared memcached has no key collisions.
        'KEY_PREFIX': _get('site', 'CACHE_KEY_PREFIX', ''),
    }
}

AUTH_PROFILE_MODULE = 'yats.UserProfile'

TIME_ZONE = 'Europe/Berlin'
LANGUAGE_CODE = 'de'

gettext = lambda s: s
LANGUAGES = (
    ('de', gettext('German')),
    ('en', gettext('English')),
)
USE_I18N = True
USE_L10N = True

FILE_UPLOAD_MAX_MEMORY_SIZE = 2621440 * 1024
FILE_UPLOAD_PATH = _get('folder', 'FILE_UPLOAD_PATH', '/var/web/yats/files/')
FILE_UPLOAD_VIRUS_SCAN = _getbool('folder', 'FILE_UPLOAD_VIRUS_SCAN', True)

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = _get('folder', 'STATIC_ROOT', '/var/web/yats/static/')

# Absolute path to the directory temp files should be saved to.
# used for reports
TEMP_ROOT = _get('folder', 'TEMP_ROOT', '/tmp/')

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'
MF_UI_URL = STATIC_URL

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody. Set a real per-web key in
# the INI ([site] SECRET_KEY); the literal below is only a dev fallback.
SECRET_KEY = _get('site', 'SECRET_KEY', ')ha6uuz1zqw3$r1-bqk1wv=wh%=*7aheo&6-cm(_z)v+bs%%!*')
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'OPTIONS': {
            'context_processors': [
                'django.contrib.messages.context_processors.messages',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.tz',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.static',
            ],
            'loaders': [
                'django.template.loaders.app_directories.Loader',
            ]
        },
    },
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # Serve STATIC_ROOT directly from gunicorn (mf-router/OpenResty proxies on a
    # separate host and cannot read this server's filesystem). Harmless where a
    # web server already serves /static (Vagrant/Apache, Docker/Caddy).
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'yats.middleware.header.ResponseInjectHeader',
    'yats.middleware.auth.TryBasicAuthMiddleware',
    # 'yats.middleware.auth.BasicAuthMiddleware',
    'yats.middleware.auth.OrgaAdditionMiddleware',
    #'yats.middleware.error.ErrorCaptureMiddleware',
]

ROOT_URLCONF = 'web.urls'

WSGI_APPLICATION = 'web.wsgi.application'

DEVSERVER_TRUNCATE_SQL = False
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'rpc4django',
    'bootstrap_toolkit',
    'yats',
    'web',
    'dav',  # CalDAV: embedded Radicale 3.x (replaces dead djradicale + Radicale 1.x)
    'markdownx',
    'haystack',
    'background_task',
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'include_html': True,
        },
        'request_handler': {
                'level': 'DEBUG',
                'class': 'logging.handlers.RotatingFileHandler',
                'filename': _get('folder', 'LOGGING_PATH', '/var/web/yats/logs/django_request.log'),
                'maxBytes': 1024 * 1024 * 5,  # 5 MB
                'backupCount': 5,
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['request_handler', 'mail_admins'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'rpc4django': {
            'handlers': ['request_handler'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'dav': {
            'handlers': ['console'],
            'level': 'DEBUG',
            # 'level': 'ERROR',
            'propagate': True,
        },
    }
}

TICKET_CLASS = 'web.models.test'
TICKET_NEW_MAIL_RCPT = _get('notify', 'TICKET_NEW_MAIL_RCPT', '')
TICKET_NEW_JABBER_RCPT = _get('notify', 'TICKET_NEW_JABBER_RCPT', '')
TICKET_NEW_SIGNAL_RCPT = _get('notify', 'TICKET_NEW_SIGNAL_RCPT', '')
TICKET_NON_PUBLIC_FIELDS = _getlist('tickets', 'TICKET_NON_PUBLIC_FIELDS', ['billing_needed', 'billing_reason', 'billing_done', 'fixed_in_version', 'solution', 'assigned', 'priority'])
TICKET_SEARCH_FIELDS = ['caption', 'c_user', 'priority', 'type', 'customer', 'component', 'deadline', 'billing_needed', 'billing_done', 'closed', 'assigned', 'state', 'description', 'hasAttachments', 'hasComments']
TICKET_EDITABLE_FIELDS_AFTER_CLOSE = ['billing_done']

# Used by yats.yatse (YATSE integration); empty disables it. Per-web.
API_KEY = _get('api', 'API_KEY', '')

GITHUB_REPO = _get('github', 'GITHUB_REPO', 'yats')
GITHUB_OWNER = _get('github', 'GITHUB_OWNER', 'mediafactory')
GITHUB_USER = _get('github', 'GITHUB_USER')
GITHUB_PASS = _get('github', 'GITHUB_PASS')

LOGIN_URL = _get('site', 'LOGIN_URL', '/local_login')

KEEP_IT_SIMPLE = True
KEEP_IT_SIMPLE_DEFAULT_TYPE = _getint('tickets', 'KEEP_IT_SIMPLE_DEFAULT_TYPE', 1)
KEEP_IT_SIMPLE_DEFAULT_PRIORITY = _getint('tickets', 'KEEP_IT_SIMPLE_DEFAULT_PRIORITY', 2)
KEEP_IT_SIMPLE_DEFAULT_CUSTOMER = _getint('tickets', 'KEEP_IT_SIMPLE_DEFAULT_CUSTOMER', -1)  # -1 = auto from user
KEEP_IT_SIMPLE_DEFAULT_COMPONENT = _getint('tickets', 'KEEP_IT_SIMPLE_DEFAULT_COMPONENT', 1)

REASSIGN_ALWAYS_TO_INCOMING_QUEUE = True

PROJECT_NAME = _get('site', 'PROJECT_NAME', 'DEV')

# CalDAV is served by an embedded Radicale 3.x WSGI app (modules/dav/).
# The mount point; the dav app + urls read this. Auth/rights are enforced by
# dav.radicale_auth (trusts Django) and dav.radicale_rights (own-principal only).
CALDAV_BASE_PREFIX = '/tickets/dav/'

# HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'xapian_backend.XapianEngine',
        'PATH': _get('folder', 'INDEX_PATH', '/var/web/yats/index/xapian_index'),
        'HAYSTACK_XAPIAN_LANGUAGE': 'de',
        'HAYSTACK_XAPIAN_STEMMING_STRATEGY': 'STEM_SOME',
        'INCLUDE_SPELLING': True,
    },
}

MARKDOWNX_MARKDOWN_EXTENSIONS = [
    'markdown.extensions.extra',
    'markdown.extensions.codehilite',
    'markdown.extensions.admonition',
    'markdown.extensions.nl2br',
]

MARKDOWNX_MARKDOWN_EXTENSION_CONFIGS = {
    'codehilite': {
        'linenums': False
    }
}
