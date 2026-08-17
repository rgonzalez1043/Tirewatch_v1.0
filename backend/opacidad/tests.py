from datetime import date, timedelta

from django.test import TestCase

from equipos.models import Equipo, TipoEquipo
from .models import Opacimetro, MedicionOpacidad, ProyeccionOpacidad
from .services.analizador import AnalizadorOpacidad
from .services import parser_texa

TEXTO_TRA_2178 = """Copia para el taller
Resultado Test de Emisiones Diesel
Fecha del Test 18/06/2026
Hora del test 13:04
Detalles del vehiculo
Matricula 2178
VIN TRACTO
Fabricante TERBERG
Modelo YT220
Limites min. max.
Temperatura motor 60
k (1/m) 3,00
Opa range < 2,5 (k) 0,50
Opa range >= 2,5 (k) 0,70
Preparacion Valor leido Unidad min. max. Resultado
Temperatura del aceite motor #70 C 60 SUPERADO
Aceleracion de referencia / Regimen en ralenti #700 rpm
Aceleracion de referencia / Regimen maximo #2200 rpm
1 1,91 700 2200 -
2 1,61 700 2200 -
3 1,66 700 2200 -
Opacidad/ Test MOT (1/m) 3,00 1,73 SUPERADO
Exito global SUPERADO
TEXA
SPA
OPABOX
Autopower GOBNT005323 OM00372EST001b/NET2 23/01/2026
La validez del control periodico de la camara de analisis ha caducado
Testado por Firma
"""


class ParserTexaTests(TestCase):

    def setUp(self):
        self.d, self.w = parser_texa.extraer(TEXTO_TRA_2178)

    def test_extrae_campos_principales(self):
        self.assertEqual(self.d["fecha"], date(2026, 6, 18))
        self.assertEqual(self.d["matricula"], "2178")
        self.assertEqual(self.d["k_medio"], 1.73)
        self.assertEqual(self.d["k_limite"], 3.0)
        self.assertTrue(self.d["aprobado"])

    def test_extrae_tres_aceleraciones(self):
        self.assertEqual(len(self.d["aceleraciones"]), 3)
        self.assertEqual([a["k"] for a in self.d["aceleraciones"]], [1.91, 1.61, 1.66])

    def test_detecta_campos_digitados_a_mano(self):
        self.assertIn("temp_aceite", self.d["campos_manuales"])
        self.assertIn("rpm_ralenti", self.d["campos_manuales"])
        self.assertIn("rpm_maximo", self.d["campos_manuales"])

    def test_detecta_calibracion_vencida(self):
        self.assertTrue(any("CALIBRACION VENCIDA" in a for a in self.w))

    def test_identifica_opacimetro(self):
        self.assertEqual(self.d["opacimetro"]["numero_serie"], "GOBNT005323")
        self.assertEqual(self.d["opacimetro"]["vencimiento_control"], date(2026, 1, 23))

    def test_dispersion_dentro_de_tolerancia(self):
        self.assertAlmostEqual(self.d["dispersion"], 0.30, places=2)
        self.assertFalse(any("Dispersion" in a for a in self.w))

    def test_vin_invalido_advertido(self):
        self.assertTrue(any("VIN" in a for a in self.w))


class AnalizadorOpacidadTests(TestCase):

    def setUp(self):
        self.tipo = TipoEquipo.objects.create(nombre="Tracto", codigo="TRACTO")
        self.equipo = Equipo.objects.create(numero=2178, tipo=self.tipo)
        self.opa = Opacimetro.objects.create(
            fabricante="TEXA SPA", modelo="OPABOX", numero_serie="GOBNT005323",
            vencimiento_control=date(2027, 1, 23),
        )

    def _medir(self, fecha, k, hm=None, limite=3.0):
        return MedicionOpacidad.objects.create(
            equipo=self.equipo, fecha=fecha, k_medio=k, k_limite=limite,
            horometro_motor=hm, opacimetro=self.opa,
        )

    def test_periodo_semestral_automatico(self):
        m1 = self._medir(date(2026, 3, 10), 1.2)
        m2 = self._medir(date(2026, 9, 10), 1.3)
        self.assertEqual(m1.periodo, "2026-S1")
        self.assertEqual(m2.periodo, "2026-S2")

    def test_reprobado_marca_critico(self):
        self._medir(date(2026, 6, 18), 3.4)
        proy = AnalizadorOpacidad.analizar_equipo(self.equipo)
        self.assertEqual(proy.estado, "CRITICO")
        self.assertIn("REPROBADO", proy.motivo_estado)

    def test_tendencia_ascendente_detectada(self):
        self._medir(date(2024, 6, 1), 1.20, 10000)
        self._medir(date(2024, 12, 1), 1.55, 12000)
        self._medir(date(2025, 6, 1), 1.95, 14000)
        proy = AnalizadorOpacidad.analizar_equipo(self.equipo)
        self.assertIsNotNone(proy.tasa_k_anual)
        self.assertGreater(proy.tasa_k_anual, 0.5)
        self.assertIsNotNone(proy.tasa_k_1000h)
        self.assertEqual(proy.n_mediciones, 3)
        self.assertIn(proy.estado, ("ATENCION", "CRITICO"))

    def test_equipo_estable_queda_ok(self):
        self._medir(date(2025, 1, 15), 1.10)
        self._medir(date(2025, 7, 15), 1.15)
        self._medir(date(2026, 1, 15), 1.12)
        proy = AnalizadorOpacidad.analizar_equipo(self.equipo)
        # control vencido genera ATENCION; se valida la parte analitica
        self.assertLess(abs(proy.tasa_k_anual), 0.15)
        self.assertLess(proy.pct_limite, 0.70)

    def test_calibracion_evaluada_contra_fecha_del_test(self):
        vencido = Opacimetro.objects.create(
            fabricante="TEXA", modelo="OPABOX", numero_serie="XX111111",
            vencimiento_control=date(2026, 1, 23),
        )
        m = MedicionOpacidad.objects.create(
            equipo=self.equipo, fecha=date(2026, 6, 18),
            k_medio=1.73, k_limite=3.0, opacimetro=vencido,
        )
        self.assertFalse(m.calibracion_vigente)

    def test_anular_excluye_del_analisis(self):
        self._medir(date(2026, 1, 10), 1.2)
        mala = self._medir(date(2026, 6, 18), 2.9)
        proy = AnalizadorOpacidad.analizar_equipo(self.equipo)
        self.assertEqual(proy.k_actual, 2.9)
        mala.anular(None, "Error de digitacion")
        proy = AnalizadorOpacidad.analizar_equipo(self.equipo)
        self.assertEqual(proy.k_actual, 1.2)

    def test_cobertura_campana(self):
        Equipo.objects.create(numero=2179, tipo=self.tipo)
        self._medir(date(2026, 3, 1), 1.5)
        rep = AnalizadorOpacidad.cobertura_campana("2026-S1")
        self.assertEqual(rep["total_flota"], 2)
        self.assertEqual(rep["con_control"], 1)
        self.assertEqual(rep["cobertura_pct"], 50.0)
        self.assertIn("TRACTO-2179", rep["equipos_faltantes"])
