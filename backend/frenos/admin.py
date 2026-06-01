from django.contrib import admin
from .models import ComponenteFreno, MedicionFreno, ProyeccionFreno


class MedicionFrenoInline(admin.TabularInline):
    model = MedicionFreno
    extra = 0
    readonly_fields = ["registrado_por", "created_at"]
    ordering = ["-fecha"]


@admin.register(ComponenteFreno)
class ComponenteFrenoAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "get_posicion_display", "get_tipo_freno_display",
        "espesor_fabrica_mm", "fecha_instalacion", "activo",
        "fecha_retiro", "motivo_retiro", "registrado_por",
    ]
    list_filter = ["activo", "tipo_freno", "posicion", "equipo__tipo"]
    search_fields = ["equipo__numero", "notas"]
    ordering = ["equipo__numero", "posicion", "-activo"]
    readonly_fields = ["created_at"]
    inlines = [MedicionFrenoInline]

    fieldsets = [
        ("Identificación", {
            "fields": ["equipo", "posicion", "tipo_freno"]
        }),
        ("Instalación", {
            "fields": ["espesor_fabrica_mm", "fecha_instalacion", "horometro_instalacion"]
        }),
        ("Estado", {
            "fields": ["activo", "fecha_retiro", "motivo_retiro"]
        }),
        ("Notas", {
            "fields": ["notas", "registrado_por", "created_at"]
        }),
    ]


@admin.register(MedicionFreno)
class MedicionFrenoAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "componente", "fecha", "horometro",
        "espesor_mm", "registrado_por",
    ]
    list_filter = ["fecha", "equipo__tipo"]
    search_fields = ["equipo__numero"]
    ordering = ["-fecha"]


@admin.register(ProyeccionFreno)
class ProyeccionFrenoAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "componente", "estado",
        "espesor_actual_mm", "desgaste_pct",
        "horas_restantes", "fecha_cambio_estimada", "updated_at",
    ]
    list_filter = ["estado"]
    search_fields = ["equipo__numero"]
    ordering = ["estado", "horas_restantes"]
