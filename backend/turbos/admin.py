from django.contrib import admin
from .models import MedicionTurbo, ProyeccionTurbo


@admin.register(MedicionTurbo)
class MedicionTurboAdmin(admin.ModelAdmin):
    list_display = ["equipo", "fecha", "horometro_motor", "juego_radial", "juego_axial", "estado_visual"]
    list_filter = ["estado_visual", "fecha"]
    search_fields = ["equipo__numero"]
    ordering = ["-fecha", "-horometro_motor"]
    readonly_fields = ["created_at"]


@admin.register(ProyeccionTurbo)
class ProyeccionTurboAdmin(admin.ModelAdmin):
    list_display = ["equipo", "estado", "horas_motor_restantes", "juego_radial_actual", "juego_axial_actual", "ultima_medicion_fecha"]
    list_filter = ["estado"]
    search_fields = ["equipo__numero"]
    ordering = ["estado", "horas_motor_restantes"]
    readonly_fields = ["updated_at"]
