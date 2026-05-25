from django.db import models
from equipos.models import Equipo
from core.models import Usuario

class MedicionTurbo(models.Model):
    """
    Registro individual de medición de holgura radial y axial de un turbo en terreno
    """
    ESTADO_VISUAL_CHOICES = [
        ("OK", "Buen estado - Sin anomalías"),
        ("FUGA_ACEITE", "Fuga visible de aceite en caracola"),
        ("ROCE_ASPAS", "Roce metálico de álabes en carcasa"),
        ("OTRO", "Otro (Ver observaciones)")
    ]

    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE, related_name="mediciones_turbo")
    fecha = models.DateField()
    horometro_motor = models.PositiveIntegerField(help_text="Horas de funcionamiento del motor al momento de la medición")
    
    juego_radial = models.FloatField(help_text="Juego radial en milímetros (mm)")
    juego_axial = models.FloatField(help_text="Juego axial en milímetros (mm)")
    
    estado_visual = models.CharField(max_length=20, choices=ESTADO_VISUAL_CHOICES, default="OK")
    observaciones = models.TextField(blank=True, null=True)
    
    registrado_por = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-horometro_motor"]
        unique_together = ("equipo", "fecha", "horometro_motor")  # Evitar duplicados

    def __str__(self):
        return f"Turbo {self.equipo.numero} - {self.horometro_motor} hrs ({self.fecha})"


class ProyeccionTurbo(models.Model):
    """
    Almacena el último análisis predictivo de desgaste para un turbo.
    Se actualiza cada vez que se ingresa una medición nueva o se corre el motor analítico.
    """
    ESTADO_CHOICES = [
        ("OK", "Ok"),
        ("ATENCION", "Atención"),
        ("CRITICO", "Crítico"),
    ]

    equipo = models.OneToOneField(Equipo, on_delete=models.CASCADE, related_name="proyeccion_turbo")
    
    # Tasas de crecimiento de la holgura. Ej: 0.05 mm cada 1000 horas
    tasa_radial_1000h = models.FloatField(default=0.0, help_text="Crecimiento milimétrico proyectado cada 1000 hrs")
    tasa_axial_1000h = models.FloatField(default=0.0, help_text="Crecimiento milimétrico proyectado cada 1000 hrs")
    
    # Proyecciones finales
    horas_motor_restantes = models.FloatField(default=10000, help_text="Horas estimadas de motor restantes hasta límite de tolerancia")
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default="OK")
    
    ultima_medicion_fecha = models.DateField(null=True, blank=True)
    ultima_medicion_horometro = models.PositiveIntegerField(null=True, blank=True)
    
    # Guardamos el valor actual para graficar rápido sin query adicional
    juego_radial_actual = models.FloatField(null=True, blank=True)
    juego_axial_actual = models.FloatField(null=True, blank=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["estado", "horas_motor_restantes"]

    def __str__(self):
        return f"Proyección Turbo {self.equipo.numero} - Estado: {self.estado}"
