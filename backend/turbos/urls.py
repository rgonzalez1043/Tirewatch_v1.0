from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MedicionTurboViewSet, ProyeccionTurboViewSet, EjecutarAnalisisTurbosView

app_name = "turbos"

router = DefaultRouter()
router.register(r"mediciones", MedicionTurboViewSet, basename="medicion_turbo")
router.register(r"proyecciones", ProyeccionTurboViewSet, basename="proyeccion_turbo")

urlpatterns = [
    path("", include(router.urls)),
    path("analizar/", EjecutarAnalisisTurbosView.as_view(), name="analizar_turbos"),
]
