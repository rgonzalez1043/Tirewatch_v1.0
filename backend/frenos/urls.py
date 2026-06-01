from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ComponenteFrenoViewSet, MedicionFrenoViewSet, ProyeccionFrenoViewSet

router = DefaultRouter()
router.register("componentes", ComponenteFrenoViewSet, basename="componente-freno")
router.register("mediciones", MedicionFrenoViewSet, basename="medicion-freno")
router.register("proyecciones", ProyeccionFrenoViewSet, basename="proyeccion-freno")

urlpatterns = [
    path("", include(router.urls)),
]
