from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("", views.dashboard, name="dashboard"),
    path("turbos/", views.turbos_dashboard, name="turbos_dashboard"),
    path("frenos/", views.frenos_dashboard, name="frenos_dashboard"),
    path("cadenas/", views.cadenas_dashboard, name="cadenas_dashboard"),
    path("opacidad/", views.opacidad_dashboard, name="opacidad_dashboard"),
    path("app-movil/", views.app_movil, name="app_movil"),
    # Configuración y Marcas
    path("configuracion/", views.configuracion_sistema, name="configuracion_sistema"),
    path("marcas/crear/", views.marca_crear, name="marca_crear"),
    path("marcas/<int:marca_id>/eliminar/", views.marca_eliminar, name="marca_eliminar"),
    path("terreno/", views.terreno, name="terreno"),
    path("importar/", views.importar, name="importar"),
    path("equipos/<int:equipo_id>/", views.equipo_detalle, name="equipo_detalle"),
    path("modulos/", views.modulos, name="modulos"),
    path("ayuda/", views.ayuda, name="ayuda"),

    # Reportes
    path("reportes/", views.reporte_proyecciones, name="reporte_proyecciones"),

    # Usuarios (Admin)
    path("usuarios/", views.usuarios_list, name="usuarios_list"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:user_id>/editar/", views.usuario_editar, name="usuario_editar"),
]
