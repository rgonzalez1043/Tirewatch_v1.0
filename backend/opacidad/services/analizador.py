"""
Motor analitico de opacidad.

Con periodicidad semestral se dispone de ~2 puntos por ano. La regresion
recien es informativa desde el tercer punto; por eso la carga historica
no es opcional, es lo que hace util el modulo desde el primer dia.

Deliberadamente se usa regresion lineal simple: con 4-6 puntos no hay
estadistica que rescatar con modelos mas sofisticados.
"""
from datetime import timedelta

import numpy as np
from django.utils import timezone

from core.models import ConfiguracionSistema
from equipos.models import Equipo
from ..models import MedicionOpacidad, ProyeccionOpacidad

MIN_PUNTOS_REGRESION = 3
MESES_PERIODICIDAD = 6


class AnalizadorOpacidad:

    @staticmethod
    def _config():
        return ConfiguracionSistema.load()

    @classmethod
    def analizar_equipo(cls, equipo):
        """Recalcula y persiste la proyeccion de un equipo. Devuelve la instancia."""
        cfg = cls._config()
        umbral_alerta = getattr(cfg, "umbral_alerta_opacidad_pct", 0.70)
        umbral_critico = getattr(cfg, "umbral_critico_opacidad_pct", 0.85)
        meses = getattr(cfg, "meses_periodicidad_opacidad", MESES_PERIODICIDAD)

        mediciones = list(
            MedicionOpacidad.objects
            .filter(equipo=equipo, anulado=False)
            .order_by("fecha")
        )

        proy, _ = ProyeccionOpacidad.objects.get_or_create(equipo=equipo)

        if not mediciones:
            proy.n_mediciones = 0
            proy.estado = "OK"
            proy.motivo_estado = "Sin mediciones registradas"
            proy.k_actual = None
            proy.save()
            return proy

        actual = mediciones[-1]
        tipo_cod = equipo.tipo.codigo if equipo and equipo.tipo else ""
        limite_cfg = cfg.get_limite_opacidad(tipo_cod) if hasattr(cfg, "get_limite_opacidad") else (getattr(cfg, "limite_opacidad_k_default", 3.0) or 3.0)
        limite = limite_cfg if (not actual.k_limite or actual.k_limite < 2.0) else actual.k_limite

        proy.n_mediciones = len(mediciones)
        proy.k_actual = actual.k_medio
        proy.k_limite = limite
        proy.pct_limite = round(actual.k_medio / limite, 4)
        proy.ultima_medicion_fecha = actual.fecha
        proy.proximo_control = actual.fecha + timedelta(days=int(meses * 30.44))
        proy.control_vencido = proy.proximo_control < timezone.localdate()
        proy.delta_ultimo = (
            round(actual.k_medio - mediciones[-2].k_medio, 3) if len(mediciones) >= 2 else None
        )

        # --- Regresion temporal ---
        proy.tasa_k_anual = None
        proy.k_proyectado = None
        proy.semestres_a_limite = None

        if len(mediciones) >= MIN_PUNTOS_REGRESION:
            t0 = mediciones[0].fecha
            x = np.array([(m.fecha - t0).days / 365.25 for m in mediciones], dtype=float)
            y = np.array([m.k_medio for m in mediciones], dtype=float)
            if x.max() > 0:
                pend, inter = np.polyfit(x, y, 1)
                proy.tasa_k_anual = round(float(pend), 4)
                horizonte = float(x[-1]) + (meses / 12.0)
                proy.k_proyectado = round(float(pend * horizonte + inter), 3)
                if pend > 0.001:
                    restante = (limite - float(y[-1])) / (float(pend) * (meses / 12.0))
                    proy.semestres_a_limite = round(max(restante, 0), 1)

            # --- Normalizacion por horometro (mejor indicador que el calendario) ---
            con_hm = [m for m in mediciones if m.horometro_motor]
            if len(con_hm) >= MIN_PUNTOS_REGRESION:
                xh = np.array([m.horometro_motor / 1000.0 for m in con_hm], dtype=float)
                yh = np.array([m.k_medio for m in con_hm], dtype=float)
                if xh.max() - xh.min() > 0.1:
                    ph, _ = np.polyfit(xh, yh, 1)
                    proy.tasa_k_1000h = round(float(ph), 4)

        estado, motivo = cls._semaforo(proy, limite, actual, umbral_alerta, umbral_critico)
        proy.estado = estado
        proy.motivo_estado = motivo
        proy.save()
        return proy

    @staticmethod
    def _semaforo(proy, limite, actual, umbral_alerta, umbral_critico):
        """
        Reglas, en orden de prioridad. Se devuelve el primer disparo.
        Se mantienen los 3 estados del resto de TireWatch (OK/ATENCION/CRITICO)
        para que el dashboard consolidado no tenga que conocer un cuarto color.
        """
        if not actual.aprobado:
            return "CRITICO", f"Test REPROBADO: k={actual.k_medio} sobre limite {limite}"

        if proy.pct_limite >= umbral_critico:
            return "CRITICO", f"k al {proy.pct_limite:.0%} del limite normativo"

        if proy.k_proyectado and proy.k_proyectado > limite:
            return "CRITICO", (
                f"La tendencia proyecta k={proy.k_proyectado} en el proximo control, "
                f"sobre el limite {limite}"
            )

        if proy.control_vencido:
            return "ATENCION", f"Control vencido desde {proy.proximo_control}"

        if proy.pct_limite >= umbral_alerta:
            return "ATENCION", f"k al {proy.pct_limite:.0%} del limite normativo"

        if proy.tasa_k_anual and proy.tasa_k_anual > 0.30:
            return "ATENCION", f"Tendencia al alza: +{proy.tasa_k_anual} 1/m por ano"

        if proy.delta_ultimo and proy.delta_ultimo > 0.50:
            return "ATENCION", f"Salto de +{proy.delta_ultimo} 1/m respecto del control anterior"

        if not actual.calibracion_vigente:
            return "ATENCION", "Ultimo test realizado con opacimetro fuera de calibracion"

        return "OK", f"k={actual.k_medio} ({proy.pct_limite:.0%} del limite)"

    @classmethod
    def analizar_todos(cls):
        """Recalcula todos los equipos que tengan al menos una medicion."""
        cfg = cls._config()
        limite_cfg = getattr(cfg, "limite_opacidad_k_default", 3.0) or 3.0

        # Corregir mediciones donde se guardó 1.50 por calibración errónea en el opacímetro
        for m in MedicionOpacidad.objects.filter(anulado=False, k_limite__lt=2.0).select_related("equipo", "equipo__tipo"):
            tipo_cod = m.equipo.tipo.codigo if m.equipo and m.equipo.tipo else ""
            lim_corregido = cfg.get_limite_opacidad(tipo_cod) if hasattr(cfg, "get_limite_opacidad") else (getattr(cfg, "limite_opacidad_k_default", 3.0) or 3.0)
            m.k_limite = lim_corregido
            if m.k_medio is not None:
                m.aprobado = (m.k_medio <= lim_corregido)
            m.save(update_fields=["k_limite", "aprobado"])

        ids = (
            MedicionOpacidad.objects.filter(anulado=False)
            .values_list("equipo_id", flat=True).distinct()
        )
        n = 0
        for equipo in Equipo.objects.filter(id__in=list(ids)):
            cls.analizar_equipo(equipo)
            n += 1
        return n

    @classmethod
    def cobertura_campana(cls, periodo):
        """
        Para auditoria: que porcentaje de la flota tiene control en el periodo.
        Esta es la pregunta que hace el fiscalizador, no el certificado individual.
        """
        equipos = Equipo.objects.exclude(estado="fuera_servicio")
        total = equipos.count()
        medidos = set(
            MedicionOpacidad.objects
            .filter(periodo=periodo, anulado=False)
            .values_list("equipo_id", flat=True)
        )
        faltantes = [e for e in equipos if e.id not in medidos]
        sin_calibracion = MedicionOpacidad.objects.filter(
            periodo=periodo, anulado=False, calibracion_vigente=False
        ).count()
        reprobados = MedicionOpacidad.objects.filter(
            periodo=periodo, anulado=False, aprobado=False
        ).count()

        return {
            "periodo": periodo,
            "total_flota": total,
            "con_control": len(medidos),
            "sin_control": len(faltantes),
            "cobertura_pct": round(len(medidos) / total * 100, 1) if total else 0.0,
            "equipos_faltantes": [e.codigo_completo for e in faltantes],
            "tests_sin_calibracion_vigente": sin_calibracion,
            "tests_reprobados": reprobados,
        }
