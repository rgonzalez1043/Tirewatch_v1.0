from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    OpacimetroViewSet, MedicionOpacidadViewSet, ProyeccionOpacidadViewSet,
    ImportacionOpacidadViewSet, ImportarPDFView,
    EjecutarAnalisisOpacidadView, CoberturaCampanaView,
)

app_name = "opacidad"

router = DefaultRouter()
router.register(r"mediciones", MedicionOpacidadViewSet, basename="medicion_opacidad")
router.register(r"proyecciones", ProyeccionOpacidadViewSet, basename="proyeccion_opacidad")
router.register(r"opacimetros", OpacimetroViewSet, basename="opacimetro")
router.register(r"importaciones", ImportacionOpacidadViewSet, basename="importacion_opacidad")

urlpatterns = [
    path("", include(router.urls)),
    path("importar/", ImportarPDFView.as_view(), name="importar_pdf"),
    path("analizar/", EjecutarAnalisisOpacidadView.as_view(), name="analizar_opacidad"),
    path("cobertura/", CoberturaCampanaView.as_view(), name="cobertura_campana"),
]
