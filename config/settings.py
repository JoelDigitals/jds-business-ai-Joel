"""
JDS Business AI - Django Settings
Vollständige Konfiguration für Entwicklung und Produktion
"""

from pathlib import Path
from decouple import config
from datetime import timedelta
import environ
import os

env = environ.Env()
BASE_DIR = Path(__file__).resolve().parent.parent
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))


# ============================================================
# SECURITY
# ============================================================
SECRET_KEY = config('SECRET_KEY', default='dev-only-secret-key-change-in-production-now!')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# ============================================================
# APPS
# ============================================================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'drf_spectacular',
    'django_filters',

    # JDS Apps
    'apps.core',
    'apps.ai_engine',
    'apps.api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.core.middleware.GDPRMiddleware',
    'apps.core.middleware.RateLimitMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.core.context_processors.subscription_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# ============================================================
# DATABASE
# ============================================================
DATABASES = {
    'default': env.db(),  # Liest die DATABASE_URL aus der .env Datei
}

# SQLite Fallback für schnelle lokale Entwicklung ohne Docker
if config('USE_SQLITE', default=False, cast=bool):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# ============================================================
# CACHE & REDIS
# ============================================================
REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
# Sessions in DB — kein Redis nötig, CSRF-Token bleibt erhalten
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

# ============================================================
# AUTH
# ============================================================
AUTH_USER_MODEL = 'core.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ============================================================
# REST FRAMEWORK
# ============================================================
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'apps.api.authentication.APIKeyAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'apps.api.throttling.PlanBasedThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'free': '10/day',
        'pro': '200/day',
        'business': '10000/day',
        'api_pro': '500/hour',
        'api_business': '10000/hour',
    },
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'EXCEPTION_HANDLER': 'apps.core.exceptions.custom_exception_handler',
}

# ============================================================
# JWT
# ============================================================
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ============================================================
# CORS
# ============================================================
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:8000'
).split(',')
CORS_ALLOW_CREDENTIALS = True

# ============================================================
# AI ENGINE SETTINGS
# ============================================================
# ============================================================
# LLM API Keys
# Groq: Kostenlos registrieren auf https://console.groq.com/keys
# In .env eintragen: GROQ_API_KEY=gsk_xxx...
# ============================================================
GROQ_API_KEY = config('GROQ_API_KEY')

AI_CONFIG = {
    'MODEL_NAME': config('AI_MODEL_NAME', default='microsoft/DialoGPT-medium'),
    'MAX_NEW_TOKENS': config('AI_MAX_NEW_TOKENS', default=512, cast=int),
    'TEMPERATURE': config('AI_TEMPERATURE', default=0.7, cast=float),
    'TOP_P': config('AI_TOP_P', default=0.9, cast=float),
    'DEVICE': config('AI_DEVICE', default='cpu'),
    'MODEL_CACHE_DIR': BASE_DIR / 'model_cache',
}

# Plan Limits
PLAN_LIMITS = {
    'free': {
        'messages_per_day': config('FREE_MAX_MESSAGES_PER_DAY', default=10, cast=int),
        'chars_per_message': config('FREE_MAX_CHARS_PER_MESSAGE', default=500, cast=int),
        'image_uploads_per_day': config('FREE_MAX_IMAGE_UPLOADS_PER_DAY', default=2, cast=int),
        'api_access': False,
        'conversation_history': 5,
        'business_tools': ['basic_planning'],
    },
    'pro': {
        'messages_per_day': config('PRO_MAX_MESSAGES_PER_DAY', default=200, cast=int),
        'chars_per_message': config('PRO_MAX_CHARS_PER_MESSAGE', default=5000, cast=int),
        'image_uploads_per_day': config('PRO_MAX_IMAGE_UPLOADS_PER_DAY', default=20, cast=int),
        'api_access': True,
        'conversation_history': 50,
        'business_tools': ['basic_planning', 'legal_basic', 'financial_analysis', 'market_research'],
    },
    'business': {
        'messages_per_day': config('BUSINESS_MAX_MESSAGES_PER_DAY', default=10000, cast=int),
        'chars_per_message': config('BUSINESS_MAX_CHARS_PER_MESSAGE', default=50000, cast=int),
        'image_uploads_per_day': config('BUSINESS_MAX_IMAGE_UPLOADS_PER_DAY', default=500, cast=int),
        'api_access': True,
        'conversation_history': 1000,
        'business_tools': ['basic_planning', 'legal_advanced', 'financial_analysis',
                           'market_research', 'competitor_analysis', 'pitch_deck',
                           'tax_consulting', 'contract_review'],
    },
}

# ============================================================
# API Documentation (OpenAPI)
# ============================================================
SPECTACULAR_SETTINGS = {
    'TITLE': 'JDS Business AI API',
    'DESCRIPTION': '''
## JDS Business AI - Die KI für Ihr Business

JDS Business AI hilft Unternehmern bei:
- **Gründungsplanung**: Schritt-für-Schritt Anleitung zur Unternehmensgründung
- **Businessplanung**: Professionelle Businesspläne erstellen
- **Rechtliche Unterstützung**: Grundlegende Rechtsberatung für Unternehmen
- **Finanzplanung**: Budgets, Cashflow, Investitionen
- **Marktanalyse**: Wettbewerber und Marktpotenzial verstehen

### Authentifizierung
Verwende `Bearer <JWT-Token>` oder `X-API-Key <Ihr-API-Key>` im Header.

### Rate Limits
- Free: 10 Nachrichten/Tag
- Pro: 200 Nachrichten/Tag + API-Zugang (500/Stunde)
- Business: Nahezu unbegrenzt + voller API-Zugang
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
}

# ============================================================
# STATIC & MEDIA
# ============================================================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media'))

# Max file upload size: 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Request-Timeout für lange KI-Generierungen (in Sekunden)
# Gunicorn: starte mit --timeout 300
# Development-Server hat keinen Timeout-Limit
REQUEST_TIMEOUT = 300

# ============================================================
# INTERNATIONALIZATION
# ============================================================
LANGUAGE_CODE = 'de-de'
TIME_ZONE = 'Europe/Berlin'
USE_I18N = True
USE_TZ = True

# ============================================================
# DATENSCHUTZ / DSGVO
# ============================================================
GDPR_SETTINGS = {
    'DATA_RETENTION_DAYS': config('GDPR_RETENTION_DAYS', default=365, cast=int),
    'ANONYMIZE_LOGS': config('ANONYMIZE_LOGS', default=True, cast=bool),
    'COOKIE_CONSENT_REQUIRED': True,
    'DATA_EXPORT_ENABLED': True,  # Recht auf Datenauszug
    'DATA_DELETION_ENABLED': True,  # Recht auf Löschung
    'LEGAL_BASIS': 'DSGVO Art. 6 Abs. 1 lit. b (Vertragserfüllung)',
    'DATA_CONTROLLER': 'JDS Business AI GmbH',
    'DATA_CONTROLLER_EMAIL': 'datenschutz@jds-ai.de',
    'DPA_CONTACT': 'datenschutzbeauftragter@jds-ai.de',
}

# ============================================================
# LOGGING
# ============================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'jds.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {'handlers': ['console'], 'level': 'INFO'},
        'apps': {'handlers': ['console', 'file'], 'level': 'DEBUG', 'propagate': True},
        'ai_engine': {'handlers': ['console'], 'level': 'INFO'},
    },
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/chat/'
LOGOUT_REDIRECT_URL = '/'
