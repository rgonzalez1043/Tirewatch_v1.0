from django.db import models


class MarcaComponente(models.Model):
    """Marcas de componentes (neumáticos, turbos, etc.)"""
    TIPO_CHOICES = [
        ("neumatico", "Neumático"),
        ("turbo", "Turbo"),
        ("freno", "Freno"),
        ("cadena", "Cadena"),
        ("otro", "Otro"),
    ]

    nombre = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    profundidad_fabrica_mm = models.FloatField(
        null=True, blank=True,
        help_text="Profundidad de fábrica en mm (para neumáticos)"
    )
    vida_util_horas = models.FloatField(
        null=True, blank=True,
        help_text="Vida útil estimada en horas (referencia)"
    )
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Marca de Componente"
        verbose_name_plural = "Marcas de Componentes"
        unique_together = ["nombre", "tipo"]
        ordering = ["tipo", "nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.get_tipo_display()})"


class TipoEquipo(models.Model):
    """Tipos de equipo: Portacontenedor, RTG, STS, etc."""
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Tipo de Equipo"
        verbose_name_plural = "Tipos de Equipos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Equipo(models.Model):
    """Equipo individual (portacontenedor, grúa, etc.)"""
    ESTADO_CHOICES = [
        ("operativo", "Operativo"),
        ("mantenimiento", "En Mantenimiento"),
        ("fuera_servicio", "Fuera de Servicio"),
    ]

    numero = models.IntegerField(unique=True, help_text="Número identificador del equipo")
    tipo = models.ForeignKey(TipoEquipo, on_delete=models.PROTECT, related_name="equipos")
    nombre = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="operativo")
    horometro_actual = models.FloatField(default=0, help_text="Horómetro actual en horas")
    horas_operacion_diaria = models.FloatField(
        default=12.5,
        help_text="Horas promedio de operación diaria"
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    notas = models.TextField(blank=True)

    class Meta:
        verbose_name = "Equipo"
        verbose_name_plural = "Equipos"
        ordering = ["numero"]

    def __str__(self):
        return f"Equipo {self.numero} ({self.tipo.codigo})"
