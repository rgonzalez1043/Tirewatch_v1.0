from django.db import models
from django.utils import timezone

from equipos.models import Equipo
from core.models import Usuario


class Opacimetro(models.Model):
    """
    Instrumento con el que se realiza el test de opacidad.
    Se modela aparte porque la validez del certificado depende de que el
    control periodico del equipo este vigente A LA FECHA DEL TEST.
    """
    fabricante = models.CharField(max_length=60, help_text="Ej: TEXA SPA")
    modelo = models.CharField(max_length=60, help_text="Ej: OPABOX Autopower")
    numero_serie = models.CharField(max_length=40, unique=True)
    numero_homologacion = models.CharField(max_length=80, blank=True)
    vencimiento_control = models.DateField(
        help_text="Vencimiento del control periodico de la camara de analisis"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Opacimetro"
        verbose_name_plural = "Opacimetros"
        ordering = ["fabricante", "modelo"]

    def __str__(self):
        return f"{self.fabricante} {self.modelo} ({self.numero_serie})"

    def vigente_al(self, fecha):
        """True si el control periodico estaba vigente en la fecha indicada."""
        if not fecha:
            return False
        return fecha <= self.vencimiento_control

    @property
    def vigente_hoy(self):
        return self.vigente_al(timezone.localdate())


class MedicionOpacidad(models.Model):
    """
    Registro individual de un test de opacidad en aceleracion libre.
    Periodicidad esperada: semestral (flota TRACTO y PORTA).
    """

    class Origen(models.TextChoices):
        PDF = "PDF", "Informe PDF"
        MANUAL = "MANUAL", "Medicion en terreno"
        HISTORICO = "HISTORICO", "Carga historica"

    equipo = models.ForeignKey(
        Equipo, on_delete=models.CASCADE, related_name="mediciones_opacidad"
    )
    fecha = models.DateField(db_index=True)
    hora = models.TimeField(null=True, blank=True)
    periodo = models.CharField(
        max_length=7, db_index=True, blank=True,
        help_text="Semestre de la campana. Ej: 2026-S1. Se calcula solo al guardar."
    )
    horometro_motor = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Horometro del equipo al momento del test (permite normalizar la tendencia)"
    )

    # --- Resultado ---
    k_medio = models.FloatField(help_text="Coeficiente de absorcion medio en 1/m")
    k_limite = models.FloatField(
        default=3.0,
        help_text="Limite normativo declarado en el informe (1/m). NO se asume, se lee del PDF."
    )
    aprobado = models.BooleanField(default=True)

    # --- Condiciones del ensayo ---
    temp_aceite = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Grados C")
    rpm_ralenti = models.PositiveIntegerField(null=True, blank=True)
    rpm_maximo = models.PositiveIntegerField(null=True, blank=True)

    # --- Trazabilidad ---
    opacimetro = models.ForeignKey(
        Opacimetro, on_delete=models.PROTECT, null=True, blank=True,
        related_name="mediciones"
    )
    calibracion_vigente = models.BooleanField(
        default=True,
        help_text="Se evalua contra la FECHA DEL TEST, no contra hoy. Queda congelado."
    )
    origen = models.CharField(max_length=10, choices=Origen.choices, default=Origen.PDF)
    campos_manuales = models.JSONField(
        default=list, blank=True,
        help_text="Campos marcados con # en el informe (digitados, no medidos por el instrumento)"
    )
    advertencias = models.JSONField(default=list, blank=True)
    operador = models.CharField(max_length=80, blank=True)
    observaciones = models.TextField(blank=True)

    archivo = models.FileField(upload_to="opacidad/%Y/%m/", null=True, blank=True)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    texto_crudo = models.TextField(blank=True, help_text="Texto extraido del PDF, para auditoria")

    # --- Ciclo de vida (nunca se borra: se anula) ---
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.TextField(blank=True)
    anulado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="opacidades_anuladas"
    )
    anulado_at = models.DateTimeField(null=True, blank=True)

    registrado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="opacidades_registradas"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medicion de Opacidad"
        verbose_name_plural = "Mediciones de Opacidad"
        ordering = ["-fecha", "equipo"]
        unique_together = ("equipo", "fecha")
        indexes = [models.Index(fields=["equipo", "fecha"])]

    def __str__(self):
        return f"Opacidad {self.equipo.codigo_completo} - k={self.k_medio} ({self.fecha})"

    @staticmethod
    def calcular_periodo(fecha):
        return f"{fecha.year}-S{1 if fecha.month <= 6 else 2}"

    @property
    def pct_limite(self):
        if not self.k_limite:
            return None
        return self.k_medio / self.k_limite

    @property
    def margen(self):
        return self.k_limite - self.k_medio

    def save(self, *args, **kwargs):
        if self.fecha and not self.periodo:
            self.periodo = self.calcular_periodo(self.fecha)
        if self.k_limite:
            self.aprobado = self.k_medio <= self.k_limite
        if self.opacimetro_id and self.fecha:
            self.calibracion_vigente = self.opacimetro.vigente_al(self.fecha)
        super().save(*args, **kwargs)

    def anular(self, usuario, motivo):
        self.anulado = True
        self.motivo_anulacion = motivo
        self.anulado_por = usuario
        self.anulado_at = timezone.now()
        self.save(update_fields=[
            "anulado", "motivo_anulacion", "anulado_por", "anulado_at", "updated_at"
        ])


class AceleracionOpacidad(models.Model):
    """Cada una de las 3 aceleraciones libres que componen el test."""
    medicion = models.ForeignKey(
        MedicionOpacidad, on_delete=models.CASCADE, related_name="aceleraciones"
    )
    numero = models.PositiveSmallIntegerField()
    k = models.FloatField()
    rpm_ralenti = models.PositiveIntegerField(null=True, blank=True)
    rpm_maximo = models.PositiveIntegerField(null=True, blank=True)
    tiempo_s = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Aceleracion"
        verbose_name_plural = "Aceleraciones"
        ordering = ["medicion", "numero"]
        unique_together = ("medicion", "numero")

    def __str__(self):
        return f"Acel #{self.numero} k={self.k}"


class ProyeccionOpacidad(models.Model):
    """
    Ultimo analisis de tendencia por equipo. Se recalcula al ingresar una
    medicion nueva o al correr el motor analitico completo.
    """
    ESTADO_CHOICES = [
        ("OK", "Ok"),
        ("ATENCION", "Atencion"),
        ("CRITICO", "Critico"),
    ]

    equipo = models.OneToOneField(
        Equipo, on_delete=models.CASCADE, related_name="proyeccion_opacidad"
    )

    k_actual = models.FloatField(null=True, blank=True)
    k_limite = models.FloatField(null=True, blank=True)
    pct_limite = models.FloatField(null=True, blank=True, help_text="k_actual / k_limite")
    delta_ultimo = models.FloatField(
        null=True, blank=True, help_text="Variacion respecto del control anterior"
    )

    tasa_k_anual = models.FloatField(
        null=True, blank=True, help_text="Pendiente de la regresion, en 1/m por ano"
    )
    tasa_k_1000h = models.FloatField(
        null=True, blank=True, help_text="Pendiente normalizada por horometro, en 1/m cada 1000 h"
    )
    k_proyectado = models.FloatField(
        null=True, blank=True, help_text="k estimado para el proximo control semestral"
    )
    semestres_a_limite = models.FloatField(null=True, blank=True)

    n_mediciones = models.PositiveSmallIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="OK")
    motivo_estado = models.CharField(max_length=200, blank=True)

    ultima_medicion_fecha = models.DateField(null=True, blank=True)
    proximo_control = models.DateField(null=True, blank=True)
    control_vencido = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyeccion de Opacidad"
        verbose_name_plural = "Proyecciones de Opacidad"
        ordering = ["estado", "-pct_limite"]

    def __str__(self):
        return f"Proyeccion Opacidad {self.equipo.codigo_completo} - {self.estado}"


class ImportacionOpacidad(models.Model):
    """
    Buffer de importacion. El parser NUNCA escribe directo en MedicionOpacidad:
    deja aqui lo extraido, el usuario valida/corrige y recien ahi se confirma.
    Los rechazos tambien quedan registrados.
    """

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente de revision"
        CONFIRMADA = "CONFIRMADA", "Confirmada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    archivo = models.FileField(upload_to="opacidad/importaciones/%Y/%m/")
    sha256 = models.CharField(max_length=64, db_index=True)
    nombre_original = models.CharField(max_length=255, blank=True)

    datos_extraidos = models.JSONField(default=dict)
    advertencias = models.JSONField(default=list)
    equipo_sugerido = models.ForeignKey(
        Equipo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="importaciones_opacidad"
    )
    matricula_detectada = models.CharField(max_length=30, blank=True)

    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE)
    medicion = models.OneToOneField(
        MedicionOpacidad, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="importacion"
    )
    motivo_rechazo = models.TextField(blank=True)

    subido_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="importaciones_opacidad"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Importacion de Opacidad"
        verbose_name_plural = "Importaciones de Opacidad"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Importacion {self.nombre_original or self.sha256[:8]} [{self.estado}]"
