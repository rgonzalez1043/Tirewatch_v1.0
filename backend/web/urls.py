from django.urls import path
from . import views

app_name = "web"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("", views.dashboard, name="dashboard"),
    path("turbos/", views.turbos_dashboard, name="turbos_dashboard"),
    path("configuracion/", views.configuracion_sistema, name="configuracion_sistema"),
    path("terreno/", views.terreno, name="terreno"),
    path("importar/", views.importar, name="importar"),
    path("equipos/<int:equipo_id>/", views.equipo_detalle, name="equipo_detalle"),
    path("modulos/", views.modulos, name="modulos"),
    path("ayuda/", views.ayuda, name="ayuda"),
    
    # Usuarios (Admin)
    path("usuarios/", views.usuarios_list, name="usuarios_list"),
    path("usuarios/nuevo/", views.usuario_crear, name="usuario_crear"),
    path("usuarios/<int:user_id>/editar/", views.usuario_editar, name="usuario_editar"),
]
