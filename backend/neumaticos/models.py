from django.db import models
from django.conf import settings


class Neumatico(models.Model):
    """Neumático instalado en un equipo"""
    TIPO_CHOICES = [
        ("traccion", "Traccional"),
        ("direccion", "Direccional"),
    ]

    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="neumaticos",
    )
    marca = models.ForeignKey(
        "equipos.MarcaComponente",
        on_delete=models.PROTECT,
        related_name="neumaticos",
        limit_choices_to={"tipo": "neumatico"},
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    posicion = models.CharField(
        max_length=10,
        help_text="Posición: H1-H8 para traccionales, D1-D2 para direccionales"
    )
    serie = models.CharField(max_length=50, blank=True, help_text="Número de serie")
    fecha_instalacion = models.DateField(null=True, blank=True)
    horometro_instalacion = models.FloatField(
        default=0,
        help_text="Horómetro al momento de instalar"
    )
    profundidad_inicial_mm = models.FloatField(
        null=True, blank=True,
        help_text="Profundidad al instalar (mm). Si vacío, usa valor de fábrica."
    )
    activo = models.BooleanField(default=True)
    fecha_retiro = models.DateField(null=True, blank=True)
    motivo_retiro = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Neumático"
        verbose_name_plural = "Neumáticos"
        ordering = ["equipo", "tipo", "posicion"]
        unique_together = ["equipo", "tipo", "posicion", "activo"]

    def __str__(self):
        return f"Eq.{self.equipo.numero} - {self.get_tipo_display()} {self.posicion}"

    @property
    def profundidad_fabrica(self):
        if self.profundidad_inicial_mm:
            return self.profundidad_inicial_mm
        if self.marca and self.marca.profundidad_fabrica_mm:
            return self.marca.profundidad_fabrica_mm
        tw = settings.TIREWATCH
        return tw["PROFUNDIDAD_FABRICA"].get(self.marca.nombre.upper(), 75)


class Medicion(models.Model):
    """Medición individual de profundidad"""
    ORIGEN_CHOICES = [
        ("terreno", "Registro en Terreno"),
        ("excel", "Importación Excel"),
        ("api", "API Externa"),
    ]

    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="mediciones_neumaticos",
    )
    fecha = models.DateField(help_text="Fecha de la medición")
    tipo = models.CharField(
        max_length=20,
        choices=Neumatico.TIPO_CHOICES,
    )
    marca_nombre = models.CharField(
        max_length=50,
        help_text="Nombre de marca al momento de medir"
    )

    # Valores por posición (nullable para flexibilidad)
    h1 = models.FloatField(null=True, blank=True, verbose_name="H1 (mm)")
    h2 = models.FloatField(null=True, blank=True, verbose_name="H2 (mm)")
    h3 = models.FloatField(null=True, blank=True, verbose_name="H3 (mm)")
    h4 = models.FloatField(null=True, blank=True, verbose_name="H4 (mm)")
    h5 = models.FloatField(null=True, blank=True, verbose_name="H5 (mm)")
    h6 = models.FloatField(null=True, blank=True, verbose_name="H6 (mm)")
    h7 = models.FloatField(null=True, blank=True, verbose_name="H7 (mm)")
    h8 = models.FloatField(null=True, blank=True, verbose_name="H8 (mm)")
    d1 = models.FloatField(null=True, blank=True, verbose_name="D1 (mm)")
    d2 = models.FloatField(null=True, blank=True, verbose_name="D2 (mm)")

    # Metadata
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default="terreno")
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="mediciones_registradas",
    )
    horometro = models.FloatField(null=True, blank=True, help_text="Horómetro al medir")
    observaciones = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Medición"
        verbose_name_plural = "Mediciones"
        ordering = ["equipo", "tipo", "fecha"]
        indexes = [
            models.Index(fields=["equipo", "tipo", "fecha"]),
            models.Index(fields=["fecha"]),
            models.Index(fields=["marca_nombre"]),
        ]

    def __str__(self):
        return f"Eq.{self.equipo.numero} - {self.fecha} ({self.get_tipo_display()})"

    @property
    def posiciones(self):
        """Retorna dict de posiciones con valor"""
        if self.tipo == "traccion":
            campos = {"H1": self.h1, "H2": self.h2, "H3": self.h3, "H4": self.h4,
                       "H5": self.h5, "H6": self.h6, "H7": self.h7, "H8": self.h8}
        else:
            campos = {"D1": self.d1, "D2": self.d2}
        return {k: v for k, v in campos.items() if v is not None}


class TasaDesgaste(models.Model):
    """Tasa de desgaste calculada (cache de análisis)"""
    marca_nombre = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=Neumatico.TIPO_CHOICES)
    posicion = models.CharField(max_length=5)
    tasa_mm_dia = models.FloatField(help_text="mm/día (valor absoluto)")
    tasa_mm_hora = models.FloatField(help_text="mm/hora")
    tasa_mm_100h = models.FloatField(help_text="mm/100 horas")
    total_mm_acum = models.FloatField(help_text="mm acumulados usados para cálculo")
    total_dias_acum = models.FloatField(help_text="Días acumulados usados para cálculo")
    n_mediciones = models.IntegerField(default=0)
    calculado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Tasa de Desgaste"
        verbose_name_plural = "Tasas de Desgaste"
        unique_together = ["marca_nombre", "tipo", "posicion"]
        ordering = ["tipo", "marca_nombre", "posicion"]

    def __str__(self):
        return f"{self.marca_nombre} - {self.posicion}: {self.tasa_mm_dia:.4f} mm/día"


class Proyeccion(models.Model):
    """Proyección de cambio por equipo"""
    equipo = models.ForeignKey(
        "equipos.Equipo",
        on_delete=models.CASCADE,
        related_name="proyecciones_neumaticos",
    )
    tipo = models.CharField(max_length=20, choices=Neumatico.TIPO_CHOICES)
    marca_nombre = models.CharField(max_length=50)
    posicion_critica = models.CharField(max_length=5, help_text="Posición que llega primero al límite")
    valor_actual_mm = models.FloatField()
    horas_restantes = models.FloatField()
    fecha_cambio_estimada = models.DateField()
    fecha_ultima_medicion = models.DateField()
    calculado_en = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proyección"
        verbose_name_plural = "Proyecciones"
        unique_together = ["equipo", "tipo"]
        ordering = ["horas_restantes"]

    def __str__(self):
        return f"Eq.{self.equipo.numero} - {self.horas_restantes:.0f} hrs restantes"

    @property
    def estado(self):
        if self.horas_restantes < 200:
            return "critico"
        elif self.horas_restantes < 500:
            return "atencion"
        return "ok"
