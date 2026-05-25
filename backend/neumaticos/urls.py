from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register("mediciones", views.MedicionViewSet, basename="medicion")
router.register("tasas", views.TasaDesgasteViewSet, basename="tasa-desgaste")
router.register("proyecciones", views.ProyeccionViewSet, basename="proyeccion")

urlpatterns = [
    path("", include(router.urls)),
    path("importar/", views.ImportarExcelView.as_view(), name="importar-excel"),
    path("analisis/ejecutar/", views.EjecutarAnalisisView.as_view(), name="ejecutar-analisis"),
    path("grafico/<int:equipo_numero>/", views.GraficoEquipoView.as_view(), name="grafico-equipo"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
