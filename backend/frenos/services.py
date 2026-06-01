"""
Servicio de análisis predictivo para el módulo de Frenos.
Calcula tasa de desgaste por componente (regresión lineal) y proyecta
la fecha estimada de cambio en función del límite configurado.
"""
import datetime
import logging
from django.utils import timezone
from core.models import ConfiguracionSistema
from .models import ComponenteFreno, MedicionFreno, ProyeccionFreno

logger = logging.getLogger(__name__)


def _regresion_lineal(puntos):
    """
    Regresión lineal entre (horómetro, espesor_mm).
    Retorna la pendiente (mm/hora), negativa = desgaste.
    Necesita al menos 2 puntos.
    """
    n = len(puntos)
    if n < 2:
        return None
    sum_x = sum(p[0] for p in puntos)
    sum_y = sum(p[1] for p in puntos)
    sum_xy = sum(p[0] * p[1] for p in puntos)
    sum_x2 = sum(p[0] ** 2 for p in puntos)
    denom = n * sum_x2 - sum_x ** 2
    if abs(denom) < 1e-9:
        return None
    return (n * sum_xy - sum_x * sum_y) / denom  # mm/hora


def analizar_componente(componente: ComponenteFreno) -> ProyeccionFreno | None:
    """
    Analiza el historial de mediciones de UN componente de freno y
    actualiza (o crea) su ProyeccionFreno.

    Lógica:
    - Con 1 medición: estado basado solo en espesor actual vs límite.
    - Con ≥2 mediciones Y horómetros: se calcula tasa de desgaste.
    - Estado:
        CRITICO  → espesor ≤ límite o horas_restantes < 100
        ATENCION → desgaste_pct ≥ umbral_alerta (ej: 75%)
        OK       → en el resto de los casos
    """
    config = ConfiguracionSistema.load()
    limite_mm = config.limite_freno_pastilla_mm
    prof_fabrica = componente.espesor_fabrica_mm
    umbral_pct = config.umbral_alerta_freno_pct  # 0.0 a 1.0

    mediciones = list(
        MedicionFreno.objects
        .filter(componente=componente)
        .order_by("fecha", "horometro")
    )

    if not mediciones:
        # Sin mediciones: proyección básica en OK
        proy, _ = ProyeccionFreno.objects.update_or_create(
            componente=componente,
            defaults={
                "equipo": componente.equipo,
                "espesor_actual_mm": None,
                "desgaste_pct": 0.0,
                "tasa_desgaste_mm_1000h": 0.0,
                "horas_restantes": 99999,
                "fecha_cambio_estimada": None,
                "estado": "OK",
                "ultima_medicion_fecha": None,
                "ultima_medicion_horometro": None,
                "n_mediciones": 0,
            }
        )
        return proy

    ultima = mediciones[-1]
    espesor_actual = ultima.espesor_mm
    n_mediciones = len(mediciones)

    # Calcular tasa de desgaste si hay horómetros
    puntos_h = [(m.horometro, m.espesor_mm) for m in mediciones if m.horometro is not None]
    tasa_mm_hora = _regresion_lineal(puntos_h)  # negativa = desgaste
    tasa_1000h = abs(tasa_mm_hora) * 1000 if tasa_mm_hora is not None else 0.0

    # Proyección de horas restantes
    horas_restantes = 99999.0
    fecha_cambio = None
    margen_mm = espesor_actual - limite_mm

    if margen_mm <= 0:
        horas_restantes = 0.0
    elif tasa_1000h > 0:
        horas_restantes = (margen_mm / tasa_1000h) * 1000
        horas_diarias = config.horas_diarias_operacion or 12.5
        dias = horas_restantes / horas_diarias
        fecha_cambio = timezone.now().date() + datetime.timedelta(days=int(dias))

    # Porcentaje de vida consumida (0% = nuevo, 100% = en límite)
    rango_util = prof_fabrica - limite_mm
    if rango_util > 0:
        desgaste_pct = ((prof_fabrica - espesor_actual) / rango_util) * 100
        desgaste_pct = max(0.0, min(desgaste_pct, 100.0))
    else:
        desgaste_pct = 0.0

    # Determinar estado
    desgaste_ratio = desgaste_pct / 100.0  # 0.0 a 1.0
    if espesor_actual <= limite_mm or horas_restantes < 100:
        estado = "CRITICO"
    elif desgaste_ratio >= umbral_pct:
        estado = "ATENCION"
    else:
        estado = "OK"

    proy, _ = ProyeccionFreno.objects.update_or_create(
        componente=componente,
        defaults={
            "equipo": componente.equipo,
            "espesor_actual_mm": espesor_actual,
            "desgaste_pct": desgaste_pct,
            "tasa_desgaste_mm_1000h": tasa_1000h,
            "horas_restantes": horas_restantes,
            "fecha_cambio_estimada": fecha_cambio,
            "estado": estado,
            "ultima_medicion_fecha": ultima.fecha,
            "ultima_medicion_horometro": ultima.horometro,
            "n_mediciones": n_mediciones,
        }
    )
    return proy


def analizar_frenos_equipo(equipo):
    """
    Analiza todos los componentes ACTIVOS de freno de un equipo.
    Retorna lista de ProyeccionFreno actualizadas.
    """
    componentes = ComponenteFreno.objects.filter(equipo=equipo, activo=True)
    resultados = []
    for comp in componentes:
        try:
            proy = analizar_componente(comp)
            if proy:
                resultados.append(proy)
        except Exception as e:
            logger.error(f"Error analizando componente freno {comp.id}: {e}")
    return resultados


def analizar_todos_los_frenos():
    """Ejecuta el análisis para todos los componentes activos de frenos."""
    componentes = ComponenteFreno.objects.filter(activo=True).select_related("equipo")
    resultados = []
    for comp in componentes:
        try:
            proy = analizar_componente(comp)
            if proy:
                resultados.append(proy)
        except Exception as e:
            logger.error(f"Error analizando freno {comp.id}: {e}")
    return resultados


def registrar_reemplazo(componente: ComponenteFreno, fecha_retiro, motivo_retiro,
                        nuevo_espesor_fabrica_mm, fecha_instalacion, horometro_instalacion,
                        notas="", registrado_por=None) -> ComponenteFreno:
    """
    Flujo completo de reemplazo de un componente de freno:
    1. Marca el componente actual como retirado
    2. Elimina su proyección
    3. Crea un nuevo componente en la misma posición
    4. Crea proyección inicial para el nuevo componente
    """
    # Retirar componente antiguo
    componente.activo = False
    componente.fecha_retiro = fecha_retiro
    componente.motivo_retiro = motivo_retiro
    componente.save()

    # Eliminar proyección del componente retirado (ya no está activo)
    ProyeccionFreno.objects.filter(componente=componente).delete()

    # Crear nuevo componente en la misma posición
    nuevo = ComponenteFreno.objects.create(
        equipo=componente.equipo,
        posicion=componente.posicion,
        tipo_freno=componente.tipo_freno,
        espesor_fabrica_mm=nuevo_espesor_fabrica_mm,
        fecha_instalacion=fecha_instalacion,
        horometro_instalacion=horometro_instalacion,
        notas=notas,
        registrado_por=registrado_por,
        activo=True,
    )

    # Crear proyección inicial (sin mediciones aún = OK)
    analizar_componente(nuevo)

    return nuevo
