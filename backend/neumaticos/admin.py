from django.contrib import admin
from .models import Neumatico, Medicion, TasaDesgaste, Proyeccion


@admin.register(Neumatico)
class NeumaticoAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "tipo", "posicion", "marca",
        "fecha_instalacion", "activo",
    ]
    list_filter = ["tipo", "marca", "activo"]
    search_fields = ["equipo__numero", "serie"]


@admin.register(Medicion)
class MedicionAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "fecha", "tipo", "marca_nombre", "origen",
        "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8",
        "d1", "d2",
    ]
    list_filter = ["tipo", "marca_nombre", "origen", "fecha"]
    search_fields = ["equipo__numero", "marca_nombre"]
    date_hierarchy = "fecha"
    readonly_fields = ["created_at", "updated_at"]


@admin.register(TasaDesgaste)
class TasaDesgasteAdmin(admin.ModelAdmin):
    list_display = [
        "marca_nombre", "tipo", "posicion",
        "tasa_mm_dia", "tasa_mm_hora", "tasa_mm_100h",
        "n_mediciones", "calculado_en",
    ]
    list_filter = ["tipo", "marca_nombre"]


@admin.register(Proyeccion)
class ProyeccionAdmin(admin.ModelAdmin):
    list_display = [
        "equipo", "tipo", "marca_nombre",
        "posicion_critica", "horas_restantes",
        "fecha_cambio_estimada", "estado",
    ]
    list_filter = ["tipo", "marca_nombre"]
    search_fields = ["equipo__numero"]

    def estado(self, obj):
        return obj.estado
    estado.short_description = "Estado"
