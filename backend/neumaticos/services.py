"""
Motor de Análisis de Desgaste de Neumáticos
============================================
Migración de la lógica del notebook Proyección_Neumaticos.ipynb
a un servicio reutilizable en Django.

Flujo:
1. Toma mediciones de la BD
2. Calcula tasas de desgaste por marca y posición
3. Proyecta fechas de cambio por equipo
4. Guarda resultados en TasaDesgaste y Proyeccion
"""
from datetime import timedelta

from .models import Medicion, TasaDesgaste, Proyeccion
from equipos.models import Equipo
from core.models import ConfiguracionSistema


class MotorAnalisis:
    """Motor de cálculo de desgaste y proyecciones"""

    def __init__(self):
        # Fallback a valores por defecto si la tabla de config aún no existe (ej. primeras migraciones)
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

    # =========================================================================
    # POSICIONES POR TIPO
    # =========================================================================
    POSICIONES = {
        "traccion": ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"],
        "direccion": ["d1", "d2"],
    }

    def _get_posiciones(self, tipo):
        return self.POSICIONES.get(tipo, [])

    def _get_valor(self, medicion, pos):
        return getattr(medicion, pos, None)

    # =========================================================================
    # 1. CALCULAR TASAS DE DESGASTE
    # =========================================================================
    def calcular_tasas(self, tipo="traccion"):
        """
        Calcula tasas de desgaste por marca y posición.
        Retorna dict: {marca: {posicion: tasa_mm_dia}}
        """
        posiciones = self._get_posiciones(tipo)
        mediciones = (
            Medicion.objects
            .filter(tipo=tipo)
            .select_related("equipo")
            .order_by("equipo", "fecha")
        )

        # Agrupar por equipo
        por_equipo = {}
        for m in mediciones:
            eq_id = m.equipo_id
            if eq_id not in por_equipo:
                por_equipo[eq_id] = []
            por_equipo[eq_id].append(m)

        # Acumular desgaste por marca
        acum_marcas = {}  # {marca: {pos: {mm, dias, n}}}
        acum_global = {}  # {pos: {mm, dias}}

        for eq_id, historial in por_equipo.items():
            for i in range(1, len(historial)):
                m_act = historial[i]
                m_ant = historial[i - 1]
                dt = (m_act.fecha - m_ant.fecha).days

                if dt <= 0:
                    continue

                marca = m_act.marca_nombre.upper()

                if marca not in acum_marcas:
                    acum_marcas[marca] = {}

                for pos in posiciones:
                    val_act = self._get_valor(m_act, pos)
                    val_ant = self._get_valor(m_ant, pos)

                    if val_act is None or val_ant is None:
                        continue

                    desgaste = val_act - val_ant

                    # Filtrar: solo desgaste real (negativo) y no pinchazos
                    if desgaste < 0 and desgaste > self.filtro_pinchazo:
                        # Por marca
                        if pos not in acum_marcas[marca]:
                            acum_marcas[marca][pos] = {"mm": 0, "dias": 0, "n": 0}
                        acum_marcas[marca][pos]["mm"] += desgaste
                        acum_marcas[marca][pos]["dias"] += dt
                        acum_marcas[marca][pos]["n"] += 1

                        # Global
                        if pos not in acum_global:
                            acum_global[pos] = {"mm": 0, "dias": 0}
                        acum_global[pos]["mm"] += desgaste
                        acum_global[pos]["dias"] += dt

        # Calcular tasas
        tasa_global = {}
        for pos, data in acum_global.items():
            tasa_global[pos] = data["mm"] / data["dias"] if data["dias"] > 0 else 0

        tasas_marca = {}
        for marca, posiciones_data in acum_marcas.items():
            tasas_marca[marca] = {}
            for pos in posiciones:
                if pos in posiciones_data and posiciones_data[pos]["dias"] > 0:
                    tasas_marca[marca][pos] = posiciones_data[pos]["mm"] / posiciones_data[pos]["dias"]
                else:
                    tasas_marca[marca][pos] = tasa_global.get(pos, 0)

        return {
            "tasas_marca": tasas_marca,
            "tasa_global": tasa_global,
            "acum_marcas": acum_marcas,
            "acum_global": acum_global,
        }

    # =========================================================================
    # 2. PROYECTAR EQUIPO
    # =========================================================================
    def proyectar_equipo(self, equipo, tipo, tasas_marca, tasa_global):
        """
        Proyecta la fecha de cambio para un equipo específico.
        """
        posiciones = self._get_posiciones(tipo)

        historial = list(
            Medicion.objects
            .filter(equipo=equipo, tipo=tipo)
            .order_by("fecha")
        )

        if len(historial) == 0:
            return None

        ultimo = historial[-1]
        marca = ultimo.marca_nombre.upper()
        tasas = tasas_marca.get(marca, tasa_global)
        horas_dia = equipo.horas_operacion_diaria or self.horas_diarias

        mejor_pos = None
        min_horas = float("inf")

        for pos in posiciones:
            val = self._get_valor(ultimo, pos)
            if val is None:
                continue

            tasa_dia = tasas.get(pos, tasa_global.get(pos, 0))
            if tasa_dia >= 0:
                continue  # No hay desgaste

            tasa_hora = tasa_dia / horas_dia
            horas_restantes = (self.limite_cambio - val) / tasa_hora

            if horas_restantes < min_horas:
                min_horas = horas_restantes
                mejor_pos = pos.upper()

        if mejor_pos is None or min_horas == float("inf"):
            return None

        dias_restantes = min_horas / horas_dia
        fecha_cambio = ultimo.fecha + timedelta(days=dias_restantes)

        return {
            "equipo": equipo,
            "tipo": tipo,
            "marca": marca,
            "posicion_critica": mejor_pos,
            "valor_actual_mm": self._get_valor(ultimo, mejor_pos.lower()) or 0,
            "horas_restantes": abs(min_horas),
            "fecha_cambio": fecha_cambio,
            "fecha_ultima_medicion": ultimo.fecha,
            "historial": historial,
        }

    # =========================================================================
    # 3. GENERAR DATOS PARA GRÁFICO
    # =========================================================================
    def datos_grafico(self, equipo, tipo, tasas_marca, tasa_global):
        """Genera series de datos para gráficos (historial + proyección)"""
        posiciones = self._get_posiciones(tipo)

        historial = list(
            Medicion.objects
            .filter(equipo=equipo, tipo=tipo)
            .order_by("fecha")
        )

        if not historial:
            return []

        series = []

        # Datos reales
        for m in historial:
            valores = {}
            for pos in posiciones:
                val = self._get_valor(m, pos)
                if val is not None:
                    valores[pos.upper()] = val
            series.append({
                "fecha": m.fecha.isoformat(),
                "tipo": "real",
                "valores": valores,
            })

        # Proyección
        ultimo = historial[-1]
        marca = ultimo.marca_nombre.upper()
        tasas = tasas_marca.get(marca, tasa_global)

        for mes in range(1, 49):
            fecha_proy = ultimo.fecha + timedelta(days=30 * mes)
            valores = {}
            alguno_bajo = False

            for pos in posiciones:
                val = self._get_valor(ultimo, pos)
                if val is None:
                    continue
                tasa = tasas.get(pos, tasa_global.get(pos, 0))
                val_proy = val + tasa * 30 * mes
                valores[pos.upper()] = round(val_proy, 2)
                if val_proy <= self.limite_cambio:
                    alguno_bajo = True

            series.append({
                "fecha": fecha_proy.isoformat(),
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
        - Calcula tasas
        - Guarda en TasaDesgaste
        - Proyecta todos los equipos
        - Guarda en Proyeccion
        """
        resultado = self.calcular_tasas(tipo)
        tasas_marca = resultado["tasas_marca"]
        tasa_global = resultado["tasa_global"]
        acum_marcas = resultado["acum_marcas"]

        # Guardar tasas
        TasaDesgaste.objects.filter(tipo=tipo).delete()
        for marca, posiciones_data in tasas_marca.items():
            horas_dia = self.horas_diarias
            for pos, tasa_dia in posiciones_data.items():
                tasa_abs = abs(tasa_dia)
                tasa_hora = tasa_abs / horas_dia
                acum = acum_marcas.get(marca, {}).get(pos, {})

                TasaDesgaste.objects.create(
                    marca_nombre=marca,
                    tipo=tipo,
                    posicion=pos.upper(),
                    tasa_mm_dia=tasa_abs,
                    tasa_mm_hora=tasa_hora,
                    tasa_mm_100h=tasa_hora * 100,
                    total_mm_acum=abs(acum.get("mm", 0)),
                    total_dias_acum=acum.get("dias", 0),
                    n_mediciones=acum.get("n", 0),
                )

        # Proyectar equipos
        Proyeccion.objects.filter(tipo=tipo).delete()
        equipos = Equipo.objects.all()
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

        return {
            "tasas_calculadas": sum(len(v) for v in tasas_marca.values()),
            "equipos_analizados": len(equipos),
            "proyecciones_generadas": len(proyecciones),
        }
