from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicionCadenaViewSet, ProyeccionCadenaViewSet

router = DefaultRouter()
router.register("mediciones", MedicionCadenaViewSet, basename="medicion-cadena")
router.register("proyecciones", ProyeccionCadenaViewSet, basename="proyeccion-cadena")

urlpatterns = [
    path("", include(router.urls)),
]
