from django.contrib.auth.models import AbstractUser
from django.db import models


class Departamento(models.Model):
    """Departamentos de STI"""
    nombre = models.CharField(max_length=100, unique=True)
    codigo = models.CharField(max_length=20, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Departamento"
        verbose_name_plural = "Departamentos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    """Usuario extendido para TireWatch"""
    ROLES = [
        ("admin", "Administrador"),
        ("supervisor", "Supervisor"),
        ("tecnico", "Técnico"),
        ("operador", "Operador"),
        ("viewer", "Solo Lectura"),
    ]

    departamento = models.ForeignKey(
        Departamento,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="usuarios",
    )
    rol = models.CharField(max_length=20, choices=ROLES, default="tecnico")
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def __str__(self):
        return f"{self.get_full_name()} ({self.rol})"

    @property
    def puede_editar(self):
        return self.rol in ("admin", "supervisor", "tecnico")

    @property
    def puede_administrar(self):
        return self.rol in ("admin", "supervisor")


class ConfiguracionSistema(models.Model):
    """
    Modelo Singleton para almacenar configuraciones globales del sistema.
    Solo debería existir un registro en la base de datos.
    """
    # Módulo Neumáticos
    limite_cambio_neumatico_mm = models.FloatField(default=10.0, help_text="Límite mínimo en mm para alerta de cambio de neumático")
    filtro_pinchazo_neumatico_mm = models.FloatField(default=-10.0, help_text="Cualquier pérdida brusca mayor a este valor (negativo) se asume pinchazo y se filtra del desgaste normal")
    horas_diarias_operacion = models.FloatField(default=12.5, help_text="Promedio de horas diarias de operación por equipo")
    prof_fabrica_neumatico = models.FloatField(default=40.0, help_text="Profundidad de remanente en mm de un neumático nuevo")
    
    # Módulo Turbos
    limite_turbo_radial = models.FloatField(default=0.45, help_text="Límite máximo de juego radial permitido en mm")
    limite_turbo_axial = models.FloatField(default=0.15, help_text="Límite máximo de juego axial permitido en mm")
    umbral_alerta_turbo_pct = models.FloatField(default=0.80, help_text="Porcentaje de desgaste (0.0 a 1.0) desde el cual desencadenar alerta de ATENCIÓN")

    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuración del Sistema"

    def __str__(self):
        return "Configuración Global TireWatch"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj
