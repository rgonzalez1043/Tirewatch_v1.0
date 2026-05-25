from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Departamento


@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo", "activo"]
    search_fields = ["nombre", "codigo"]


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ["username", "get_full_name", "rol", "departamento", "is_active"]
    list_filter = ["rol", "departamento", "is_active"]
    search_fields = ["username", "first_name", "last_name", "email"]

    fieldsets = UserAdmin.fieldsets + (
        ("TireWatch", {
            "fields": ("rol", "departamento", "cargo", "telefono"),
        }),
    )
