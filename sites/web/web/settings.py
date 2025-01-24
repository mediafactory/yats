# -*- coding: utf-8 -*-
DEBUG = True
# DEBUG_PROPAGATE_EXCEPTIONS = DEBUG
XMLRPC_DEBUG = False
ALLOWED_HOSTS = ['*']
SECURE_PROXY_SSL_HEADER = ('HTTP_FRONT_END_HTTPS', 'On')

USE_TZ = True
SITE_ID = 1

TESTSYTEM = True

ADMINS = []
MANAGERS = ADMINS

EMAIL_SUBJECT_PREFIX = 'yats-dev'
EMAIL_HOST = 'localhost'
EMAIL_PORT = 25
SERVER_EMAIL = 'develope@mediafactory.de'
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''

JABBER_HOST_USER = ''
JABBER_HOST_PASSWORD = ''
JABBER_TEST_RECIPIENT = ''

SIGNAL_BIN = 'sudo /usr/local/bin/signal-cli'  # defaul
SIGNAL_CONFIG = ''  # default
SIGNAL_USERNAME = ''
SIGNAL_TEST_RECIPIENT = ''

# DATABASE_ROUTERS = ['web.routers.ModelRouter']
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': '/var/web/yats/db/yats2.sqlite',
        'USER': 'root',
        'PASSWORD': None,
        'HOST': 'localhost',
        'PORT': None,
        # 'ATOMIC_REQUESTS': config.get('database', 'ATOMIC_REQUESTS'),
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:11211',
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
FILE_UPLOAD_PATH = '/var/web/yats/files/'
FILE_UPLOAD_VIRUS_SCAN = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

STATIC_ROOT = '/var/web/yats/static/'

# Absolute path to the directory temp files should be saved to.
# used for reports
TEMP_ROOT = '/tmp/'

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

# Make this unique, and don't share it with anybody.
SECRET_KEY = ')ha6uuz1zqw3$r1-bqk1wv=wh%=*7aheo&6-cm(_z)v+bs%%!*'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'

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
    'djradicale',
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
                'filename': '/var/web/yats/logs/django_request.log',
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
        'djradicale': {
            'handlers': ['console'],
            'level': 'DEBUG',
            # 'level': 'ERROR',
            'propagate': True,
        },
    }
}

TICKET_CLASS = 'web.models.test'
TICKET_NEW_MAIL_RCPT = ''
TICKET_NEW_JABBER_RCPT = ''
TICKET_NEW_SIGNAL_RCPT = ''
TICKET_NON_PUBLIC_FIELDS = ['billing_needed', 'billing_reason', 'billing_done', 'fixed_in_version', 'solution', 'assigned', 'priority']
TICKET_SEARCH_FIELDS = ['caption', 'c_user', 'priority', 'type', 'customer', 'component', 'deadline', 'billing_needed', 'billing_done', 'closed', 'assigned', 'state', 'description', 'hasAttachments', 'hasComments']
TICKET_EDITABLE_FIELDS_AFTER_CLOSE = ['billing_done']

GITHUB_REPO = 'yats'
GITHUB_OWNER = 'mediafactory'
GITHUB_USER = None
GITHUB_PASS = None

LOGIN_URL = '/local_login'
SSO_PRIVATE_KEY = 'Your Private Key'
SSO_PUBLIC_KEY = 'Your Public Key'
SSO_SERVER = 'http://192.168.33.17:8080/server/'
API_KEY = 'geheim'

KEEP_IT_SIMPLE = True
KEEP_IT_SIMPLE_DEFAULT_TYPE = 1
KEEP_IT_SIMPLE_DEFAULT_PRIORITY = 2
KEEP_IT_SIMPLE_DEFAULT_CUSTOMER = -1  # auto from user
KEEP_IT_SIMPLE_DEFAULT_COMPONENT = 1

PROJECT_NAME = 'DEV'

DJRADICALE_CONFIG = {
    'server': {
        'base_prefix': '/tickets/dav/',
        'realm': 'YATS Tickets - Password Required',
    },
    'encoding': {
        'request': 'utf-8',
        'stock': 'utf-8',
    },
    'auth': {
        'type': 'custom',
        'custom_handler': 'djradicale.auth.django',
    },
    'rights': {
        'type': 'custom',
        'custom_handler': 'djradicale.rights.django',
    },
    'storage': {
        'type': 'custom',
        'custom_handler': 'yats.caldav.storage',
    },
    'well-known': {
        'caldav': '/tickets/dav/%(user)s/calendar.ics',
    },
}

DJRADICALE_RIGHTS = {
    'rw': {
        'user': '.+',
        'collection': '^%(login)s/[a-z0-9\.\-_]+\.(vcf|ics)$',
        'permission': 'rw',
    },
    'rw-root': {
        'user': '.+',
        'collection': '^%(login)s$',
        'permission': 'rw',
    },
}

# HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'xapian_backend.XapianEngine',
        'PATH': '/var/web/yats/index/xapian_index',
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
