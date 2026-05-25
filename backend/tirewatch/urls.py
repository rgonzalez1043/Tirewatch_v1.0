"""TireWatch URL Configuration"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from web.views import login_view
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    # API
    path("api/auth/", include("core.urls")),
    path("api/equipos/", include("equipos.urls")),
    path("api/neumaticos/", include("neumaticos.urls")),
    path("api/turbos/", include("turbos.urls")),
    # Frontend web
    path("login/", login_view, name="login"),
    path("", include("web.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Admin site customization
admin.site.site_header = "TireWatch - STI"
admin.site.site_title = "TireWatch Admin"
admin.site.index_title = "Panel de Administración"
