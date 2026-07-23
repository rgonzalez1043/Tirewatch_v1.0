"""
Motor de Análisis de Desgaste de Neumáticos
============================================
Calcula tasas de desgaste y proyecta fechas/horas de cambio.

Jerarquía de precisión en el cálculo de tasa:
  1. Regresión lineal (horómetro, mm) por equipo — MÁS PRECISO
     Requiere ≥ 2 mediciones con horómetro para ese equipo.
  2. Tasa de flota por marca usando horómetros cuando disponibles
     Usa dh = h2 - h1 cuando ambas mediciones tienen horómetro.
  3. Tasa de flota por marca usando días × horas_diarias_promedio
     Fallback cuando no hay horómetros.
"""
import logging
from datetime import timedelta

from .models import Medicion, TasaDesgaste, Proyeccion
from equipos.models import Equipo
from core.models import ConfiguracionSistema

logger = logging.getLogger(__name__)


def _regresion_lineal(puntos):
    """
    Regresión lineal mínimos cuadrados sobre pares (x, y).
    Retorna la pendiente (dy/dx). Negativa = desgaste cuando y=mm y x=horas.
    Necesita ≥ 2 puntos.
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
    return (n * sum_xy - sum_x * sum_y) / denom


class MotorAnalisis:
    """Motor de cálculo de desgaste y proyecciones para neumáticos."""

    def __init__(self):
        try:
            config = ConfiguracionSistema.load()
            self.limite_cambio = config.limite_cambio_neumatico_mm
            self.filtro_pinchazo = config.filtro_pinchazo_neumatico_mm
            self.horas_diarias = config.horas_diarias_operacion
            self.prof_fabrica = config.prof_fabrica_neumatico
        except Exception:
            self.limite_cambio = 10.0
            self.filtro_pinchazo = -10.0
            self.horas_diarias = 12.5
            self.prof_fabrica = 40.0

    POSICIONES = {
        "traccion": ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"],
        "direccion": ["d1", "d2"],
    }

    def _get_posiciones(self, tipo):
        return self.POSICIONES.get(tipo, [])

    def _get_valor(self, medicion, pos):
        return getattr(medicion, pos, None)

    # =========================================================================
    # 1. CALCULAR TASAS DE DESGASTE DE FLOTA (mm/hora)
    # =========================================================================
    def calcular_tasas(self, tipo="traccion"):
        """
        Calcula tasas de desgaste por marca y posición en mm/hora.

        Usa horómetros reales cuando están disponibles en pares consecutivos.
        Cuando no hay horómetro, convierte días × horas_diarias_promedio.
        """
        posiciones = self._get_posiciones(tipo)
        mediciones = (
            Medicion.objects
            .filter(tipo=tipo)
            .select_related("equipo")
            .order_by("equipo", "fecha")
        )

        por_equipo = {}
        for m in mediciones:
            eq_id = m.equipo_id
            if eq_id not in por_equipo:
                por_equipo[eq_id] = {"equipo": m.equipo, "mediciones": []}
            por_equipo[eq_id]["mediciones"].append(m)

        acum_marcas = {}   # {marca: {pos: {mm, horas, n, n_horometro}}}
        acum_global = {}   # {pos: {mm, horas}}

        for eq_id, data in por_equipo.items():
            equipo = data["equipo"]
            historial = data["mediciones"]
            horas_dia = equipo.horas_operacion_diaria or self.horas_diarias

            for i in range(1, len(historial)):
                m_act = historial[i]
                m_ant = historial[i - 1]

                # Intervalo en horas: horómetro real si disponible, else días × horas/día
                usa_horometro = (
                    m_act.horometro is not None
                    and m_ant.horometro is not None
                    and m_act.horometro > m_ant.horometro
                )
                if usa_horometro:
                    dh = m_act.horometro - m_ant.horometro
                else:
                    dt = (m_act.fecha - m_ant.fecha).days
                    if dt <= 0:
                        continue
                    dh = dt * horas_dia

                if dh <= 0:
                    continue

                marca = m_act.marca_nombre.upper()
                if marca not in acum_marcas:
                    acum_marcas[marca] = {}

                # Umbral pinchazo en mm/h
                filtro_hora = self.filtro_pinchazo / (horas_dia or self.horas_diarias)

                for pos in posiciones:
                    val_act = self._get_valor(m_act, pos)
                    val_ant = self._get_valor(m_ant, pos)

                    if val_act is None or val_ant is None:
                        continue

                    desgaste = val_act - val_ant
                    tasa_hora = desgaste / dh  # negativa = desgaste

                    if desgaste < 0 and tasa_hora > filtro_hora:
                        if pos not in acum_marcas[marca]:
                            acum_marcas[marca][pos] = {"mm": 0, "horas": 0, "n": 0, "n_horometro": 0}
                        acum_marcas[marca][pos]["mm"] += desgaste
                        acum_marcas[marca][pos]["horas"] += dh
                        acum_marcas[marca][pos]["n"] += 1
                        if usa_horometro:
                            acum_marcas[marca][pos]["n_horometro"] += 1

                        if pos not in acum_global:
                            acum_global[pos] = {"mm": 0, "horas": 0}
                        acum_global[pos]["mm"] += desgaste
                        acum_global[pos]["horas"] += dh

        # Tasas en mm/hora (negativas = desgaste)
        tasa_global = {
            pos: d["mm"] / d["horas"]
            for pos, d in acum_global.items()
            if d["horas"] > 0
        }

        tasas_marca = {}
        for marca, pos_data in acum_marcas.items():
            tasas_marca[marca] = {}
            for pos in posiciones:
                if pos in pos_data and pos_data[pos]["horas"] > 0:
                    tasas_marca[marca][pos] = pos_data[pos]["mm"] / pos_data[pos]["horas"]
                else:
                    tasas_marca[marca][pos] = tasa_global.get(pos, 0)

        return {
            "tasas_marca": tasas_marca,    # mm/hora (negativo)
            "tasa_global": tasa_global,    # mm/hora (negativo)
            "acum_marcas": acum_marcas,
            "acum_global": acum_global,
        }

    # =========================================================================
    # 2. PROYECTAR EQUIPO (con regresión por equipo si hay horómetros)
    # =========================================================================
    def proyectar_equipo(self, equipo, tipo, tasas_marca, tasa_global):
        """
        Proyecta la fecha/horas de cambio para un equipo.

        Prioridad:
          1. Regresión lineal propia del equipo en (horómetro, mm)
             → más precisa, usa el historial real de ese equipo
          2. Tasa de flota por marca (calculada con horómetros cuando disponibles)
        """
        posiciones = self._get_posiciones(tipo)

        historial = list(
            Medicion.objects
            .filter(equipo=equipo, tipo=tipo)
            .order_by("fecha")
        )

        if not historial:
            return None

        ultimo = historial[-1]
        marca = ultimo.marca_nombre.upper()
        horas_dia = equipo.horas_operacion_diaria or self.horas_diarias

        mejor_pos = None
        min_horas = float("inf")

        for pos in posiciones:
            val_actual = self._get_valor(ultimo, pos)
            if val_actual is None:
                continue

            # Intentar regresión por equipo con horómetros
            puntos_h = [
                (m.horometro, self._get_valor(m, pos))
                for m in historial
                if m.horometro is not None and self._get_valor(m, pos) is not None
            ]
            tasa_hora = _regresion_lineal(puntos_h)  # mm/hora, negativo

            # Fallback a tasa de flota
            if tasa_hora is None or tasa_hora >= 0:
                tasas_flota = tasas_marca.get(marca, tasa_global)
                tasa_hora = tasas_flota.get(pos, tasa_global.get(pos, 0))

            if tasa_hora >= 0:
                continue  # Sin desgaste medible

            margen_mm = val_actual - self.limite_cambio
            if margen_mm <= 0:
                horas_restantes = 0.0
            else:
                horas_restantes = margen_mm / abs(tasa_hora)

            if horas_restantes < min_horas:
                min_horas = horas_restantes
                mejor_pos = pos.upper()

        if mejor_pos is None or min_horas == float("inf") or min_horas != min_horas:
            return None

        MAX_HORAS = 87600.0  # 10 años
        min_horas = min(min_horas, MAX_HORAS)

        dias_restantes = min_horas / horas_dia
        fecha_cambio = ultimo.fecha + timedelta(days=int(dias_restantes))

        return {
            "equipo": equipo,
            "tipo": tipo,
            "marca": marca,
            "posicion_critica": mejor_pos,
            "valor_actual_mm": self._get_valor(ultimo, mejor_pos.lower()) or 0,
            "horas_restantes": min_horas,
            "fecha_cambio": fecha_cambio,
            "fecha_ultima_medicion": ultimo.fecha,
            "ultimo_horometro": ultimo.horometro,
        }

    # =========================================================================
    # 3. DATOS PARA GRÁFICO (series históricas + proyección)
    # =========================================================================
    def datos_grafico(self, equipo, tipo, tasas_marca, tasa_global):
        """Genera series de datos para gráficos (historial real + proyección)."""
        posiciones = self._get_posiciones(tipo)

        historial = list(
            Medicion.objects
            .filter(equipo=equipo, tipo=tipo)
            .order_by("fecha")
        )

        if not historial:
            return []

        series = []

        for m in historial:
            valores = {}
            for pos in posiciones:
                val = self._get_valor(m, pos)
                if val is not None:
                    valores[pos.upper()] = val
            series.append({
                "fecha": m.fecha.isoformat(),
                "horometro": m.horometro,
                "tipo": "real",
                "valores": valores,
            })

        ultimo = historial[-1]
        marca = ultimo.marca_nombre.upper()
        tasas = tasas_marca.get(marca, tasa_global)
        horas_dia = equipo.horas_operacion_diaria or self.horas_diarias

        try:
            from django.conf import settings
            meses_max = getattr(settings, "TIREWATCH", {}).get("MESES_PROYECCION_MAX", 48)
        except Exception:
            meses_max = 48

        for mes in range(1, meses_max + 1):
            fecha_proy = ultimo.fecha + timedelta(days=30 * mes)
            valores = {}
            alguno_bajo = False

            for pos in posiciones:
                val = self._get_valor(ultimo, pos)
                if val is None:
                    continue
                tasa = tasas.get(pos, tasa_global.get(pos, 0))
                horas_transcurridas = mes * 30 * horas_dia
                val_proy = val + tasa * horas_transcurridas
                valores[pos.upper()] = round(val_proy, 2)
                if val_proy <= self.limite_cambio:
                    alguno_bajo = True

            series.append({
                "fecha": fecha_proy.isoformat(),
                "horometro": None,
                "tipo": "limite" if alguno_bajo else "proyeccion",
                "valores": valores,
            })

            if alguno_bajo:
                break

        return series

    # =========================================================================
    # 4. EJECUTAR ANÁLISIS COMPLETO Y GUARDAR
    # =========================================================================
    def ejecutar_analisis(self, tipo="traccion"):
        """
        Ejecuta el análisis completo:
        - Calcula tasas de flota en mm/hora (con horómetros reales cuando disponibles)
        - Guarda en TasaDesgaste
        - Proyecta todos los equipos (regresión propia o tasa de flota)
        - Guarda en Proyeccion
        """
        resultado = self.calcular_tasas(tipo)
        tasas_marca = resultado["tasas_marca"]
        tasa_global = resultado["tasa_global"]
        acum_marcas = resultado["acum_marcas"]
        horas_dia = self.horas_diarias

        # Guardar tasas de flota
        TasaDesgaste.objects.filter(tipo=tipo).delete()
        for marca, posiciones_data in tasas_marca.items():
            for pos, tasa_hora in posiciones_data.items():
                tasa_abs = abs(tasa_hora)
                acum = acum_marcas.get(marca, {}).get(pos, {})

                TasaDesgaste.objects.create(
                    marca_nombre=marca,
                    tipo=tipo,
                    posicion=pos.upper(),
                    tasa_mm_hora=tasa_abs,
                    tasa_mm_dia=tasa_abs * horas_dia,
                    tasa_mm_100h=tasa_abs * 100,
                    total_mm_acum=abs(acum.get("mm", 0)),
                    total_dias_acum=acum.get("horas", 0) / (horas_dia or 1),
                    n_mediciones=acum.get("n", 0),
                )

        # Proyectar equipos
        Proyeccion.objects.filter(tipo=tipo).delete()
        equipos = Equipo.objects.select_related("tipo").all()
        proyecciones = []

        for equipo in equipos:
            proy = self.proyectar_equipo(equipo, tipo, tasas_marca, tasa_global)
            if proy and proy["horas_restantes"] is not None:
                proyecciones.append(
                    Proyeccion(
                        equipo=equipo,
                        tipo=tipo,
                        marca_nombre=proy["marca"],
                        posicion_critica=proy["posicion_critica"],
                        valor_actual_mm=proy["valor_actual_mm"],
                        horas_restantes=proy["horas_restantes"],
                        fecha_cambio_estimada=proy["fecha_cambio"],
                        fecha_ultima_medicion=proy["fecha_ultima_medicion"],
                    )
                )

        Proyeccion.objects.bulk_create(proyecciones)

        n_horometro = sum(
            acum_marcas.get(m, {}).get(p, {}).get("n_horometro", 0)
            for m in acum_marcas for p in acum_marcas[m]
        )
        n_total = sum(
            acum_marcas.get(m, {}).get(p, {}).get("n", 0)
            for m in acum_marcas for p in acum_marcas[m]
        )

        return {
            "tasas_calculadas": sum(len(v) for v in tasas_marca.values()),
            "equipos_analizados": len(equipos),
            "proyecciones_generadas": len(proyecciones),
            "pares_con_horometro": n_horometro,
            "pares_total": n_total,
            "pct_horometro": round(n_horometro / n_total * 100, 1) if n_total else 0,
        }
