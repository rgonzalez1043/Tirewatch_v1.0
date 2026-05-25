from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("lista", views.EquipoViewSet, basename="equipo")
router.register("tipos", views.TipoEquipoViewSet, basename="tipo-equipo")
router.register("marcas", views.MarcaComponenteViewSet, basename="marca-componente")

urlpatterns = [
    path("", include(router.urls)),
]
