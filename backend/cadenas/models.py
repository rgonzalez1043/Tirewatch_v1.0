from django.db import models
from django.conf import settings


class MedicionCadena(models.Model):
    """
    Medición de elongación de cadena en spreader de grúa pórtico Taylor.
    La elongación se calcula comparando longitud medida vs longitud nominal.
    Límite industria (ISO/estándar): 3% de elongación máxima.
    Alerta temprana: 1.5% (recomendación para equipos de manejo de carga crítica).

    Instrucción de medición:
    - Medir bajo tensión sobre 10-12 eslabones consecutivos
    - Comparar con la longitud nominal del mismo tramo
    - Registrar longitud_nominal_mm y longitud_medida_mm
    """
    TIPO_CADENA_CHOICES = [
        ("spreader_principal", "Cadena Principal de Spreader"),
        ("spreader_secundaria", "Cadena Secundaria de Spreader"),
        ("elevacion", "Cadena de Elevación"),
        ("traslacion", "Cadena de Traslación"),
        ("otro", "Otro (ver observaciones)"),
    ]

    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="mediciones_cadena",
    )
    fecha = models.DateField(help_text="Fecha de la medición")
    horometro = models.FloatField(
        null=True, blank=True,
        help_text="Horómetro del equipo al momento de medir"
    )
    tipo_cadena = models.CharField(
        max_length=30,
        choices=TIPO_CADENA_CHOICES,
        default="spreader_principal",
        help_text="Tipo/ubicación de la cadena medida"
    )

    # Medidas de la cadena
    longitud_nominal_mm = models.FloatField(
        help_text="Longitud nominal (nueva) del tramo medido en mm"
    )
    longitud_medida_mm = models.FloatField(
        help_text="Longitud medida actual del mismo tramo en mm"
    )
    num_eslabones = models.IntegerField(
        default=12,
        help_text="Número de eslabones en el tramo medido (recomendado: 10-12)"
    )

    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="mediciones_cadena",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medición de Cadena"
        verbose_name_plural = "Mediciones de Cadenas"
        ordering = ["-fecha", "equipo"]
        indexes = [
            models.Index(fields=["equipo", "fecha"]),
        ]

    def __str__(self):
        return f"Cadena Eq.{self.equipo.numero} — {self.get_tipo_cadena_display()} ({self.fecha})"

    @property
    def elongacion_pct(self):
        """Elongación porcentual respecto a longitud nominal."""
        if self.longitud_nominal_mm and self.longitud_nominal_mm > 0:
            return ((self.longitud_medida_mm - self.longitud_nominal_mm) / self.longitud_nominal_mm) * 100
        return 0.0


class ProyeccionCadena(models.Model):
    """
    Proyección del estado de desgaste de cadena por equipo.
    Se actualiza cada vez que se registra una nueva medición.
    """
    ESTADO_CHOICES = [
        ("OK", "OK"),
        ("ATENCION", "Atención"),
        ("CRITICO", "Crítico"),
    ]

    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="proyecciones_cadena",
    )
    tipo_cadena = models.CharField(max_length=30, blank=True)

    # Valores actuales
    elongacion_actual_pct = models.FloatField(
        null=True, blank=True,
        help_text="Elongación actual de la cadena (%)"
    )
    longitud_nominal_mm = models.FloatField(
        null=True, blank=True,
        help_text="Longitud nominal de referencia (mm)"
    )
    longitud_actual_mm = models.FloatField(
        null=True, blank=True,
        help_text="Longitud medida en la última inspección (mm)"
    )

    # Tasa de desgaste y proyección
    tasa_elongacion_pct_1000h = models.FloatField(
        default=0.0,
        help_text="Incremento de elongación (%) por cada 1000 horas"
    )
    horas_restantes = models.FloatField(
        default=99999,
        help_text="Horas estimadas hasta alcanzar el límite de elongación"
    )
    fecha_reemplazo_estimada = models.DateField(
        null=True, blank=True,
        help_text="Fecha estimada de reemplazo de cadena"
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="OK")

    ultima_medicion_fecha = models.DateField(null=True, blank=True)
    ultima_medicion_horometro = models.FloatField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyección de Cadena"
        verbose_name_plural = "Proyecciones de Cadenas"
        unique_together = ["equipo", "tipo_cadena"]
        ordering = ["estado", "elongacion_actual_pct"]

    def __str__(self):
        return f"Cadena Eq.{self.equipo.numero} — {self.estado} ({self.elongacion_actual_pct:.2f}%)"
