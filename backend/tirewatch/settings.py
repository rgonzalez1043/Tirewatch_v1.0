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

# Producción por defecto. Para desarrollo local, define DJANGO_DEBUG=True en .env
DEBUG = os.environ.get("DJANGO_DEBUG", "False").lower() == "true"

ALLOWED_HOSTS = os.environ.get(
    "DJANGO_ALLOWED_HOSTS", "192.168.38.14,localhost,127.0.0.1"
).split(",")

# Orígenes de confianza para CSRF (necesario para el login web con DEBUG=False)
CSRF_TRUSTED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CSRF_TRUSTED_ORIGINS", "http://192.168.38.14:8011"
    ).split(",") if o.strip()
]

# =============================================================================
# APPS
# =============================================================================
INSTALLED_APPS = [
    # Tema moderno del panel /admin/ (debe ir ANTES de django.contrib.admin)
    "jazzmin",
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
    "opacidad.apps.OpacidadConfig",
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

# =============================================================================
# JAZZMIN — Tema moderno del panel /admin/
# =============================================================================
JAZZMIN_SETTINGS = {
    "site_title": "TireWatch Admin",
    "site_header": "TireWatch",
    "site_brand": "TireWatch",
    "site_logo": "img/sti.png",
    "login_logo": "img/sti.png",
    "site_logo_classes": "",
    "site_icon": "img/sti.png",
    "welcome_sign": "Panel de Administración — TireWatch",
    "copyright": "STI / Hanseatic Global Terminals",
    "search_model": ["equipos.Equipo", "neumaticos.Neumatico", "core.Usuario"],

    # Enlaces del menú superior
    "topmenu_links": [
        {"name": "Volver al sitio", "url": "/", "new_window": False},
        {"name": "Dashboard", "url": "/", "new_window": False},
    ],

    # Formularios modernos con pestañas
    "changeform_format": "horizontal_tabs",
    "related_modal_active": True,

    # Orden de aplicaciones en la barra lateral
    "order_with_respect_to": [
        "equipos", "neumaticos", "turbos", "frenos", "cadenas", "opacidad",
        "core", "auth", "authtoken",
    ],

    # Íconos (FontAwesome, incluidos con Jazzmin)
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.Group": "fas fa-users",
        "authtoken.tokenproxy": "fas fa-key",
        "core.usuario": "fas fa-user",
        "core.departamento": "fas fa-building",
        "core.configuracionsistema": "fas fa-sliders-h",
        "equipos.equipo": "fas fa-truck-monster",
        "equipos.marcacomponente": "fas fa-tag",
        "equipos.tipoequipo": "fas fa-layer-group",
        "neumaticos.neumatico": "fas fa-life-ring",
        "neumaticos.medicion": "fas fa-ruler-combined",
        "neumaticos.proyeccion": "fas fa-chart-line",
        "neumaticos.tasadesgaste": "fas fa-percent",
        "turbos.turbo": "fas fa-fan",
        "turbos.medicionturbo": "fas fa-ruler-combined",
        "turbos.proyeccionturbo": "fas fa-chart-line",
        "frenos.componentefreno": "fas fa-compact-disc",
        "frenos.medicionfreno": "fas fa-ruler-combined",
        "frenos.proyeccionfreno": "fas fa-chart-line",
        "cadenas.medicioncadena": "fas fa-link",
        "cadenas.proyeccioncadena": "fas fa-chart-line",
        "opacidad.opacimetro": "fas fa-tachometer-alt",
        "opacidad.medicionopacidad": "fas fa-smog",
        "opacidad.proyeccionopacidad": "fas fa-chart-line",
        "opacidad.importacionopacidad": "fas fa-file-import",
    },
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",

    "show_ui_builder": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": "navbar-success",
    "accent": "accent-success",
    "navbar": "navbar-white navbar-light",
    "no_navbar_border": False,
    "navbar_fixed": True,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-light-success",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": False,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "flatly",
    "default_theme_mode": "light",
    "button_classes": {
        "primary": "btn-success",
        "secondary": "btn-outline-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}
