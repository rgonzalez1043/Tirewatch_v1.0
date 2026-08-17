from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Opacimetro, MedicionOpacidad, AceleracionOpacidad,
    ProyeccionOpacidad, ImportacionOpacidad,
)


@admin.register(Opacimetro)
class OpacimetroAdmin(admin.ModelAdmin):
    list_display = ["fabricante", "modelo", "numero_serie", "vencimiento_control",
                    "estado_calibracion", "activo"]
    list_filter = ["activo", "fabricante"]
    search_fields = ["numero_serie", "numero_homologacion"]

    @admin.display(description="Calibracion")
    def estado_calibracion(self, obj):
        color, txt = ("#2e7d32", "Vigente") if obj.vigente_hoy else ("#c62828", "VENCIDA")
        return format_html('<b style="color:{}">{}</b>', color, txt)


class AceleracionInline(admin.TabularInline):
    model = AceleracionOpacidad
    extra = 0


@admin.register(MedicionOpacidad)
class MedicionOpacidadAdmin(admin.ModelAdmin):
    list_display = ["equipo", "fecha", "periodo", "k_medio", "k_limite",
                    "semaforo", "calibracion_vigente", "origen", "anulado"]
    list_filter = ["periodo", "aprobado", "calibracion_vigente", "origen",
                   "anulado", "equipo__tipo"]
    search_fields = ["equipo__numero", "operador", "observaciones"]
    date_hierarchy = "fecha"
    inlines = [AceleracionInline]
    readonly_fields = ["periodo", "aprobado", "calibracion_vigente", "sha256",
                       "texto_crudo", "advertencias", "campos_manuales",
                       "created_at", "updated_at"]
    fieldsets = (
        ("Equipo y fecha", {"fields": ("equipo", "fecha", "hora", "periodo", "horometro_motor")}),
        ("Resultado", {"fields": ("k_medio", "k_limite", "aprobado")}),
        ("Condiciones del ensayo", {"fields": ("temp_aceite", "rpm_ralenti", "rpm_maximo",
                                               "campos_manuales")}),
        ("Trazabilidad", {"fields": ("opacimetro", "calibracion_vigente", "origen",
                                     "advertencias", "operador", "archivo", "sha256")}),
        ("Anulacion", {"fields": ("anulado", "motivo_anulacion", "anulado_por", "anulado_at"),
                       "classes": ("collapse",)}),
        ("Auditoria", {"fields": ("observaciones", "registrado_por", "texto_crudo",
                                  "created_at", "updated_at"),
                       "classes": ("collapse",)}),
    )

    @admin.display(description="Resultado")
    def semaforo(self, obj):
        if not obj.aprobado:
            return format_html('<b style="color:#c62828">REPROBADO</b>')
        pct = obj.pct_limite or 0
        color = "#2e7d32" if pct < 0.70 else ("#ef6c00" if pct < 0.85 else "#c62828")
        return format_html('<b style="color:{}">{:.0%} del limite</b>', color, pct)

    def has_delete_permission(self, request, obj=None):
        return False  # nunca se borra: se anula


@admin.register(ProyeccionOpacidad)
class ProyeccionOpacidadAdmin(admin.ModelAdmin):
    list_display = ["equipo", "estado", "k_actual", "pct_limite", "tasa_k_anual",
                    "k_proyectado", "n_mediciones", "proximo_control", "control_vencido"]
    list_filter = ["estado", "control_vencido", "equipo__tipo"]
    search_fields = ["equipo__numero"]
    readonly_fields = [f.name for f in ProyeccionOpacidad._meta.fields]


@admin.register(ImportacionOpacidad)
class ImportacionOpacidadAdmin(admin.ModelAdmin):
    list_display = ["nombre_original", "matricula_detectada", "equipo_sugerido",
                    "estado", "n_advertencias", "created_at"]
    list_filter = ["estado"]
    readonly_fields = ["sha256", "datos_extraidos", "advertencias", "created_at"]

    @admin.display(description="Advertencias")
    def n_advertencias(self, obj):
        n = len(obj.advertencias or [])
        color = "#2e7d32" if n == 0 else ("#ef6c00" if n < 3 else "#c62828")
        return format_html('<b style="color:{}">{}</b>', color, n)
