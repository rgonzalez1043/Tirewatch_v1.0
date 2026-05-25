from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("departamentos/", views.DepartamentoListView.as_view(), name="departamentos"),
]
