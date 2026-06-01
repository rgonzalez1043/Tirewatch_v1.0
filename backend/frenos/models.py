from django.db import models
from django.conf import settings


class ComponenteFreno(models.Model):
    """
    Registro de un componente de freno instalado en un equipo, por posición.
    Sigue el mismo patrón que Neumatico: un registro por posición, con
    historial de reemplazos (activo=False cuando se retira).

    Tipos de freno presentes en la flota:
    - disco: Freno de disco (delanteros en Kalmar T2, Konecranes)
    - tambor: Freno de tambor (traseros en Kalmar T2, Terberg)
    - tambor_aire: Freno de tambor accionado por aire (chasis / ejes de remolque)
    """

    TIPO_FRENO_CHOICES = [
        ("disco", "Disco"),
        ("tambor", "Tambor"),
        ("tambor_aire", "Tambor de Aire"),
    ]

    POSICION_CHOICES = [
        # Eje delantero
        ("del_izq", "Delantero Izquierdo"),
        ("del_der", "Delantero Derecho"),
        # Eje trasero principal
        ("tras_izq", "Trasero Izquierdo"),
        ("tras_der", "Trasero Derecho"),
        # Eje trasero doble (rueda interior — para vehículos con eje tandem)
        ("tras_izq_int", "Trasero Izq. Interior"),
        ("tras_der_int", "Trasero Der. Interior"),
        # Eje de chasis / remolque
        ("chasis_izq", "Chasis Izquierdo"),
        ("chasis_der", "Chasis Derecho"),
        # Eje medio (para equipos con 3 ejes)
        ("medio_izq", "Medio Izquierdo"),
        ("medio_der", "Medio Derecho"),
    ]

    MOTIVO_RETIRO_CHOICES = [
        ("desgaste", "Desgaste — Límite alcanzado"),
        ("daño", "Daño físico / Fractura"),
        ("preventivo", "Mantenimiento Preventivo"),
        ("otro", "Otro (ver notas)"),
    ]

    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="frenos",
    )
    posicion = models.CharField(max_length=20, choices=POSICION_CHOICES)
    tipo_freno = models.CharField(max_length=20, choices=TIPO_FRENO_CHOICES, default="tambor")

    # Espesor al instalar (nuevo o al reemplazar)
    espesor_fabrica_mm = models.FloatField(
        help_text="Espesor de la pastilla/balata al instalar (mm). "
                  "Ref. Kalmar T2: ~20mm. Límite cambio: 6.35mm (0.25\")"
    )
    fecha_instalacion = models.DateField(null=True, blank=True)
    horometro_instalacion = models.FloatField(
        null=True, blank=True,
        help_text="Horómetro del equipo al instalar el componente"
    )

    # Estado del componente
    activo = models.BooleanField(
        default=True,
        help_text="True = en servicio. False = reemplazado (histórico)"
    )
    fecha_retiro = models.DateField(null=True, blank=True)
    motivo_retiro = models.CharField(
        max_length=20, choices=MOTIVO_RETIRO_CHOICES,
        blank=True,
        help_text="Razón por la que se retiró este freno"
    )

    notas = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="componentes_freno_registrados",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Componente de Freno"
        verbose_name_plural = "Componentes de Frenos"
        ordering = ["equipo", "posicion", "-activo"]
        indexes = [
            models.Index(fields=["equipo", "activo"]),
            models.Index(fields=["equipo", "posicion", "activo"]),
        ]

    def __str__(self):
        estado = "Activo" if self.activo else "Retirado"
        return f"Freno {self.get_posicion_display()} ({self.get_tipo_freno_display()}) — Eq.{self.equipo.numero} [{estado}]"

    @property
    def desgaste_pct(self):
        """Porcentaje de vida útil consumida según última proyección."""
        try:
            return self.proyeccion.desgaste_pct
        except Exception:
            return None


class MedicionFreno(models.Model):
    """
    Medición de espesor de un componente de freno específico.
    Un registro por componente por sesión de medición.
    El técnico mide el espesor en el punto más delgado (según fabricante).
    """
    componente = models.ForeignKey(
        ComponenteFreno,
        on_delete=models.CASCADE,
        related_name="mediciones",
    )
    # Denormalizado para queries sin JOIN
    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="mediciones_freno",
    )

    fecha = models.DateField(help_text="Fecha de la medición")
    horometro = models.FloatField(
        null=True, blank=True,
        help_text="Horómetro del equipo al momento de medir"
    )

    # Espesor medido en el punto más delgado (mm)
    espesor_mm = models.FloatField(
        help_text="Espesor medido en el punto más delgado (mm). "
                  "Para discos: espesor de la pastilla. "
                  "Para tambores: espesor de la balata."
    )

    observaciones = models.TextField(blank=True)
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="mediciones_freno_registradas",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Medición de Freno"
        verbose_name_plural = "Mediciones de Frenos"
        ordering = ["componente", "fecha"]
        indexes = [
            models.Index(fields=["componente", "fecha"]),
            models.Index(fields=["equipo", "fecha"]),
        ]

    def __str__(self):
        return (
            f"Freno {self.componente.get_posicion_display()} "
            f"Eq.{self.equipo.numero} — {self.fecha}: {self.espesor_mm} mm"
        )


class ProyeccionFreno(models.Model):
    """
    Proyección de vida útil por componente de freno.
    Se actualiza cada vez que se registra una nueva medición.
    Una proyección por componente ACTIVO.
    """
    ESTADO_CHOICES = [
        ("OK", "OK"),
        ("ATENCION", "Atención"),
        ("CRITICO", "Crítico"),
    ]

    componente = models.OneToOneField(
        ComponenteFreno,
        on_delete=models.CASCADE,
        related_name="proyeccion",
    )
    # Denormalizado para queries sin JOIN doble
    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="proyecciones_freno",
    )

    # Valores actuales (de la última medición)
    espesor_actual_mm = models.FloatField(
        null=True, blank=True,
        help_text="Espesor medido en la última inspección (mm)"
    )
    desgaste_pct = models.FloatField(
        null=True, blank=True,
        help_text="Porcentaje de vida útil consumida (0% = nuevo, 100% = límite alcanzado)"
    )

    # Tasa de desgaste y proyección
    tasa_desgaste_mm_1000h = models.FloatField(
        default=0.0,
        help_text="mm desgastados por cada 1000 horas de operación"
    )
    horas_restantes = models.FloatField(
        default=99999,
        help_text="Horas estimadas hasta alcanzar el límite de cambio"
    )
    fecha_cambio_estimada = models.DateField(
        null=True, blank=True,
        help_text="Fecha estimada de cambio según tasa de desgaste"
    )
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="OK")

    # Metadata de la última medición
    ultima_medicion_fecha = models.DateField(null=True, blank=True)
    ultima_medicion_horometro = models.FloatField(null=True, blank=True)
    n_mediciones = models.IntegerField(default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyección de Freno"
        verbose_name_plural = "Proyecciones de Frenos"
        ordering = ["estado", "horas_restantes"]

    def __str__(self):
        return (
            f"Freno {self.componente.get_posicion_display()} "
            f"Eq.{self.equipo.numero} — {self.estado}"
        )
