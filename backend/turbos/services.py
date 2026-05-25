"""
Motor de Análisis Predictivo de Turbocompresores
=================================================
Usa regresión lineal sobre TODO el historial de mediciones para calcular
la tasa de desgaste, en lugar de un simple delta entre las 2 últimas.
Esto da proyecciones más precisas y robustas ante mediciones ruidosas.

Flujo:
  1. Carga todas las mediciones del equipo ordenadas por horómetro.
  2. Ajusta una recta (np.polyfit) a (horómetro, juego_radial) y a
     (horómetro, juego_axial) por separado.
  3. La pendiente de la recta = tasa de crecimiento en mm/hora.
  4. Proyecta cuántas horas faltan para cruzar el límite del fabricante.
  5. Guarda el resultado en ProyeccionTurbo.
"""
import numpy as np

from .models import MedicionTurbo, ProyeccionTurbo
from equipos.models import Equipo
from core.models import ConfiguracionSistema


class AnalizadorTurbos:
    """Motor de análisis predictivo para desgaste de Turbocompresores."""

    # -------------------------------------------------------------------------
    # Config dinámica
    # -------------------------------------------------------------------------
    @classmethod
    def _get_config(cls):
        try:
            return ConfiguracionSistema.load()
        except Exception:
            # Fallback en caso de que la tabla aún no exista durante migraciones
            class DummyConfig:
                limite_turbo_radial = 0.45
                limite_turbo_axial = 0.15
                umbral_alerta_turbo_pct = 0.80
            return DummyConfig()

    # -------------------------------------------------------------------------
    # Análisis de un equipo
    # -------------------------------------------------------------------------
    @classmethod
    def analizar_equipo(cls, equipo: Equipo):
        """
        Calcula la proyección para un equipo usando regresión lineal.
        Retorna la instancia ProyeccionTurbo actualizada, o None si no hay datos.
        """
        mediciones = list(
            MedicionTurbo.objects
            .filter(equipo=equipo)
            .order_by("horometro_motor")
        )

        if not mediciones:
            return None

        ultima = mediciones[-1]
        proy, _ = ProyeccionTurbo.objects.get_or_create(equipo=equipo)

        # Actualizar valores de la última medición
        proy.ultima_medicion_fecha = ultima.fecha
        proy.ultima_medicion_horometro = ultima.horometro_motor
        proy.juego_radial_actual = ultima.juego_radial
        proy.juego_axial_actual = ultima.juego_axial

        # Estado visual crítico tiene prioridad sobre cualquier proyección numérica
        if ultima.estado_visual in ("FUGA_ACEITE", "ROCE_ASPAS"):
            proy.estado = "CRITICO"
            proy.horas_motor_restantes = 0
            proy.tasa_radial_1000h = 0.0
            proy.tasa_axial_1000h = 0.0
            proy.save()
            return proy

        config = cls._get_config()

        # Con una sola medición no se puede calcular tasa; solo evaluar estado actual
        if len(mediciones) == 1:
            proy.tasa_radial_1000h = 0.0
            proy.tasa_axial_1000h = 0.0
            proy.horas_motor_restantes = 10_000  # valor indicativo "sin tasa aún"
            proy.estado = cls._determinar_estado(
                ultima.juego_radial, ultima.juego_axial,
                proy.horas_motor_restantes, config,
            )
            proy.save()
            return proy

        # ---------------------------------------------------------------------
        # Regresión lineal sobre todo el historial
        # ---------------------------------------------------------------------
        horas = np.array([m.horometro_motor for m in mediciones], dtype=float)
        radiales = np.array([m.juego_radial for m in mediciones], dtype=float)
        axiales = np.array([m.juego_axial for m in mediciones], dtype=float)

        # polyfit devuelve [pendiente, intercepto]; pendiente = mm/hora
        slope_rad, intercept_rad = np.polyfit(horas, radiales, 1)
        slope_ax, intercept_ax = np.polyfit(horas, axiales, 1)

        # Solo consideramos pendientes positivas (crecimiento real del juego)
        tasa_rad_h = max(0.0, slope_rad)   # mm/hora
        tasa_ax_h = max(0.0, slope_ax)     # mm/hora

        # Convertir a mm cada 1 000 horas para el modelo
        proy.tasa_radial_1000h = round(tasa_rad_h * 1000, 6)
        proy.tasa_axial_1000h = round(tasa_ax_h * 1000, 6)

        # Valor actual proyectado desde la recta (más estable que la última medición cruda)
        val_rad_actual = float(np.polyval([slope_rad, intercept_rad], ultima.horometro_motor))
        val_ax_actual = float(np.polyval([slope_ax, intercept_ax], ultima.horometro_motor))

        # Horas hasta cruzar el límite del fabricante
        horas_rad = cls._horas_hasta_limite(
            val_rad_actual, tasa_rad_h, config.limite_turbo_radial
        )
        horas_ax = cls._horas_hasta_limite(
            val_ax_actual, tasa_ax_h, config.limite_turbo_axial
        )

        proy.horas_motor_restantes = max(0.0, min(horas_rad, horas_ax))
        proy.estado = cls._determinar_estado(
            ultima.juego_radial, ultima.juego_axial,
            proy.horas_motor_restantes, config,
        )

        proy.save()
        return proy

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    @staticmethod
    def _horas_hasta_limite(valor_actual: float, tasa_h: float, limite: float) -> float:
        """Horas hasta que el valor lineal alcanza el límite. Retorna ∞ si la tasa es 0."""
        if tasa_h <= 0:
            return 100_000.0
        mm_restantes = limite - valor_actual
        if mm_restantes <= 0:
            return 0.0
        return mm_restantes / tasa_h

    @classmethod
    def _determinar_estado(cls, radial: float, axial: float, horas_restantes: float, config) -> str:
        limite_rad = config.limite_turbo_radial
        limite_ax = config.limite_turbo_axial
        umbral_pct = config.umbral_alerta_turbo_pct

        if radial >= limite_rad or axial >= limite_ax or horas_restantes <= 0:
            return "CRITICO"

        if (
            radial >= limite_rad * umbral_pct
            or axial >= limite_ax * umbral_pct
            or horas_restantes <= 500
        ):
            return "ATENCION"

        return "OK"

    # -------------------------------------------------------------------------
    # Análisis global
    # -------------------------------------------------------------------------
    @classmethod
    def analizar_todos(cls):
        """Recalcula la proyección de todos los equipos."""
        for equipo in Equipo.objects.all():
            cls.analizar_equipo(equipo)
