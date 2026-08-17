"""TireWatch URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("api/auth/", include("core.urls")),
    path("api/equipos/", include("equipos.urls")),
    path("api/neumaticos/", include("neumaticos.urls")),
    path("api/turbos/", include("turbos.urls")),
    path("api/frenos/", include("frenos.urls")),
    path("api/cadenas/", include("cadenas.urls")),
    path("api/opacidad/", include("opacidad.urls")),
    # Frontend web
    path("", include("web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = "TireWatch - STI"
admin.site.site_title = "TireWatch Admin"
admin.site.index_title = "Panel de Administración"
