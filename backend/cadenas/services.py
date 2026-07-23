"""
Lógica de análisis predictivo para el módulo de Cadenas.
Calcula tasa de elongación y proyecta fecha de reemplazo.
"""
import datetime
import logging
from django.utils import timezone
from core.models import ConfiguracionSistema
from .models import MedicionCadena, ProyeccionCadena

logger = logging.getLogger(__name__)


def _calcular_tasa_elongacion(mediciones):
    """
    Regresión lineal entre horómetro y elongación_pct.
    Retorna tasa en %/1000h.
    """
    puntos = []
    for m in mediciones:
        if m.horometro is not None:
            puntos.append((m.horometro, m.elongacion_pct))

    if len(puntos) < 2:
        return None

    puntos.sort(key=lambda x: x[0])
    n = len(puntos)
    sum_x = sum(p[0] for p in puntos)
    sum_y = sum(p[1] for p in puntos)
    sum_xy = sum(p[0] * p[1] for p in puntos)
    sum_x2 = sum(p[0] ** 2 for p in puntos)

    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-9:
        return None

    slope = (n * sum_xy - sum_x * sum_y) / denom  # %/hora
    return max(slope * 1000, 0.0)  # %/1000h (no negativo)


def analizar_cadenas_equipo(equipo):
    """
    Analiza el historial de mediciones de cadenas para un equipo
    y actualiza (o crea) su ProyeccionCadena.
    Agrupa por tipo_cadena y toma el más crítico.
    """
    config = ConfiguracionSistema.load()
    limite_pct = config.limite_elongacion_cadena_pct
    umbral_pct = config.umbral_alerta_cadena_pct

    mediciones = list(
        MedicionCadena.objects.filter(equipo=equipo).order_by("fecha")
    )

    if not mediciones:
        return None

    ultima = mediciones[-1]
    elongacion_actual = ultima.elongacion_pct
    tipo_cadena = ultima.get_tipo_cadena_display()

    # Calcular tasa de elongación global
    tasa_1000h = _calcular_tasa_elongacion(mediciones) or 0.0

    horas_restantes = 99999.0
    fecha_reemplazo = None

    if tasa_1000h > 0:
        margen_pct = limite_pct - elongacion_actual
        if margen_pct <= 0:
            horas_restantes = 0.0
        else:
            horas_restantes = (margen_pct / tasa_1000h) * 1000

        horas_diarias = config.horas_diarias_operacion or 12.5
        dias = horas_restantes / horas_diarias
        fecha_reemplazo = timezone.now().date() + datetime.timedelta(days=int(dias))

    # Determinar estado basado en elongación actual
    if elongacion_actual >= limite_pct or horas_restantes < 100:
        estado = "CRITICO"
    elif elongacion_actual >= umbral_pct:
        estado = "ATENCION"
    else:
        estado = "OK"

    proy, _ = ProyeccionCadena.objects.update_or_create(
        equipo=equipo,
        tipo_cadena=ultima.tipo_cadena,
        defaults={
            "elongacion_actual_pct": elongacion_actual,
            "longitud_nominal_mm": ultima.longitud_nominal_mm,
            "longitud_actual_mm": ultima.longitud_medida_mm,
            "tasa_elongacion_pct_1000h": tasa_1000h,
            "horas_restantes": horas_restantes,
            "fecha_reemplazo_estimada": fecha_reemplazo,
            "estado": estado,
            "ultima_medicion_fecha": ultima.fecha,
            "ultima_medicion_horometro": ultima.horometro,
        },
    )
    return proy


def analizar_todas_las_cadenas():
    """Ejecuta el análisis para todos los equipos con mediciones de cadena."""
    from equipos.models import Equipo
    equipos_con_datos = (
        MedicionCadena.objects.values_list("equipo_id", flat=True).distinct()
    )
    resultados = []
    for eq_id in equipos_con_datos:
        try:
            equipo = Equipo.objects.get(pk=eq_id)
            proy = analizar_cadenas_equipo(equipo)
            if proy:
                resultados.append(proy)
        except Exception as e:
            logger.error(f"Error analizando cadenas equipo {eq_id}: {e}")
    return resultados
