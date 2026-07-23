from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Departamento, ConfiguracionSistema


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


@admin.register(ConfiguracionSistema)
class ConfiguracionSistemaAdmin(admin.ModelAdmin):
    """Admin singleton — no permite crear más de un registro."""

    def has_add_permission(self, request):
        # Solo permitir agregar si no existe ningún registro
        return not ConfiguracionSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
