from django.contrib import admin
from .models import Equipo, TipoEquipo, MarcaComponente


@admin.register(TipoEquipo)
class TipoEquipoAdmin(admin.ModelAdmin):
    list_display = ["nombre", "codigo"]
    search_fields = ["nombre", "codigo"]


@admin.register(MarcaComponente)
class MarcaComponenteAdmin(admin.ModelAdmin):
    list_display = ["nombre", "tipo", "profundidad_fabrica_mm", "vida_util_horas", "activo"]
    list_filter = ["tipo", "activo"]
    search_fields = ["nombre"]


@admin.register(Equipo)
class EquipoAdmin(admin.ModelAdmin):
    list_display = ["numero", "tipo", "estado", "horometro_actual", "horas_operacion_diaria"]
    list_filter = ["tipo", "estado"]
    search_fields = ["numero", "nombre"]
    list_editable = ["estado", "horometro_actual"]
