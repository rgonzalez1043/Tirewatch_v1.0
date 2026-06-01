from django.contrib import admin
from .models import MedicionCadena, ProyeccionCadena


@admin.register(MedicionCadena)
class MedicionCadenaAdmin(admin.ModelAdmin):
    list_display = ["equipo", "fecha", "tipo_cadena", "longitud_nominal_mm",
                    "longitud_medida_mm", "registrado_por"]
    list_filter = ["fecha", "tipo_cadena", "equipo__tipo"]
    search_fields = ["equipo__numero"]
    ordering = ["-fecha"]


@admin.register(ProyeccionCadena)
class ProyeccionCadenaAdmin(admin.ModelAdmin):
    list_display = ["equipo", "estado", "elongacion_actual_pct",
                    "horas_restantes", "fecha_reemplazo_estimada", "updated_at"]
    list_filter = ["estado"]
    search_fields = ["equipo__numero"]
    ordering = ["estado", "elongacion_actual_pct"]
