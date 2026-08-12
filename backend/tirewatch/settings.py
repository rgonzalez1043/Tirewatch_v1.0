"""
TireWatch - Django Settings
Sistema de Control de Desgaste - STI / HGT
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Carga automática de variables desde .env (dev y producción)
load_dotenv(BASE_DIR / ".env", override=False)

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-CAMBIAR-EN-PRODUCCION-tirewatch-sti-2025"
)

DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() == "true"

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0").split(",")

# =============================================================================
# APPS
# =============================================================================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    # Local apps
    "core.apps.CoreConfig",
    "equipos.apps.EquiposConfig",
    "neumaticos.apps.NeumaticosConfig",
    "turbos.apps.TurbosConfig",
    "frenos.apps.FrenosConfig",
    "cadenas.apps.CadenasConfig",
    "web.apps.WebConfig",
]

# =============================================================================
# MIDDLEWARE
# =============================================================================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # archivos estáticos sin Nginx
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "tirewatch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "web.context_processors.drf_token",
            ],
        },
    },
]

WSGI_APPLICATION = "tirewatch.wsgi.application"

# =============================================================================
# DATABASE
# =============================================================================
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("DB_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("DB_NAME", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("DB_USER", ""),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", ""),
        "PORT": os.environ.get("DB_PORT", ""),
    }
}

# =============================================================================
# AUTH
# =============================================================================
AUTH_USER_MODEL = "core.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =============================================================================
# REST FRAMEWORK
# =============================================================================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S",
    "DATE_FORMAT": "%Y-%m-%d",
}

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
).split(",")

CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# API Externa — Horómetros de equipos
# =============================================================================
# Cambiar la URL base si la IP del servidor cambia
HOROMETROS_API_BASE_URL = os.environ.get(
    "HOROMETROS_API_BASE_URL",
    "http://192.168.38.14:8009/vehiculos"
)
# Timeout en segundos para llamadas a la API de horómetros
HOROMETROS_API_TIMEOUT = int(os.environ.get("HOROMETROS_API_TIMEOUT", "5"))

# =============================================================================
# i18n
# =============================================================================
LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC & MEDIA
# =============================================================================
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

# WhiteNoise: compresión y cache de estáticos en producción (sin requerir manifest estricto)
if not DEBUG:
    STORAGES = {
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
        },
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Frontend web
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"

# =============================================================================
# PRODUCCION — Red interna (HTTP, sin HTTPS)
# Silenciar advertencias de SSL que no aplican en intranet
# =============================================================================
if not DEBUG:
    SILENCED_SYSTEM_CHECKS = [
        "security.W004",   # HSTS — no aplica en HTTP intranet
        "security.W008",   # SSL redirect — no hay HTTPS en intranet
        "security.W012",   # SESSION_COOKIE_SECURE — HTTP only
        "security.W016",   # CSRF_COOKIE_SECURE — HTTP only
    ]

# =============================================================================
# TIREWATCH CONFIG
# =============================================================================
TIREWATCH = {
    "LIMITE_CAMBIO_MM": 10,
    "FILTRO_PINCHAZO_MM": -10,
    "HORAS_DIARIAS_OPERACION": 12.5,
    "PROFUNDIDAD_FABRICA": {
        "GOODYEAR": 90,
        "CONTINENTAL": 75,
        "BKT": 70,
    },
    "MESES_PROYECCION_MAX": 48,
}
