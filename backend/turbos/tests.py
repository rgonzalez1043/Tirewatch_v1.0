"""
Tests unitarios — Módulo Turbos
=================================
Cubre AnalizadorTurbos: regresión lineal, estados y proyecciones.
Ejecutar: python manage.py test turbos
"""
from datetime import date

from django.test import TestCase

from equipos.models import Equipo, TipoEquipo
from turbos.models import MedicionTurbo, ProyeccionTurbo
from turbos.services import AnalizadorTurbos


# ─────────────────────────────────────────────────────────────
# Fixtures compartidas
# ─────────────────────────────────────────────────────────────
def crear_equipo(numero=201):
    tipo, _ = TipoEquipo.objects.get_or_create(codigo="PC", defaults={"nombre": "Portacontenedor"})
    return Equipo.objects.get_or_create(numero=numero, defaults={"tipo": tipo})[0]


def crear_mediciones_turbo(equipo, progresion_radial=0.05, progresion_axial=0.015):
    """
    Crea 3 mediciones con desgaste lineal controlado.
    progresion_radial: mm que crece el juego radial cada 2 000 horas.
    """
    datos = [
        (date(2024, 1, 1), 1000, 0.10,                          0.04),
        (date(2024, 7, 1), 3000, 0.10 + progresion_radial,      0.04 + progresion_axial),
        (date(2025, 1, 1), 5000, 0.10 + progresion_radial * 2,  0.04 + progresion_axial * 2),
    ]
    for fecha, horometro, radial, axial in datos:
        MedicionTurbo.objects.create(
            equipo=equipo,
            fecha=fecha,
            horometro_motor=horometro,
            juego_radial=radial,
            juego_axial=axial,
        )


# ─────────────────────────────────────────────────────────────
# Tests de analizar_equipo
# ─────────────────────────────────────────────────────────────
class TestAnalizadorTurbosAnalizar(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(201)
        crear_mediciones_turbo(self.equipo)

    def test_genera_proyeccion(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertIsNotNone(proy)
        self.assertIsInstance(proy, ProyeccionTurbo)

    def test_tasa_radial_positiva(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertGreater(proy.tasa_radial_1000h, 0)

    def test_tasa_axial_positiva(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertGreater(proy.tasa_axial_1000h, 0)

    def test_horas_restantes_positivas(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertGreater(proy.horas_motor_restantes, 0)

    def test_valores_actuales_guardados(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertIsNotNone(proy.juego_radial_actual)
        self.assertIsNotNone(proy.juego_axial_actual)

    def test_ultima_medicion_guardada(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertEqual(proy.ultima_medicion_horometro, 5000)
        self.assertEqual(proy.ultima_medicion_fecha, date(2025, 1, 1))

    def test_estado_en_valores_validos(self):
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertIn(proy.estado, ["OK", "ATENCION", "CRITICO"])

    def test_equipo_sin_mediciones_retorna_none(self):
        equipo_vacio = crear_equipo(999)
        proy = AnalizadorTurbos.analizar_equipo(equipo_vacio)
        self.assertIsNone(proy)

    def test_una_sola_medicion_no_genera_tasa(self):
        """Con una sola medición no hay delta — las tasas deben ser 0."""
        equipo = crear_equipo(202)
        MedicionTurbo.objects.create(
            equipo=equipo, fecha=date(2025, 1, 1),
            horometro_motor=1000, juego_radial=0.10, juego_axial=0.04,
        )
        proy = AnalizadorTurbos.analizar_equipo(equipo)
        self.assertEqual(proy.tasa_radial_1000h, 0.0)
        self.assertEqual(proy.tasa_axial_1000h, 0.0)


# ─────────────────────────────────────────────────────────────
# Tests de estado crítico por valores
# ─────────────────────────────────────────────────────────────
class TestAnalizadorTurbosEstados(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(203)
        # Medición base
        MedicionTurbo.objects.create(
            equipo=self.equipo, fecha=date(2024, 1, 1),
            horometro_motor=1000, juego_radial=0.10, juego_axial=0.04,
        )

    def test_estado_critico_por_fuga_aceite(self):
        MedicionTurbo.objects.create(
            equipo=self.equipo, fecha=date(2025, 6, 1),
            horometro_motor=5000, juego_radial=0.10, juego_axial=0.04,
            estado_visual="FUGA_ACEITE",
        )
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertEqual(proy.estado, "CRITICO")
        self.assertEqual(proy.horas_motor_restantes, 0)

    def test_estado_critico_por_roce_aspas(self):
        MedicionTurbo.objects.create(
            equipo=self.equipo, fecha=date(2025, 6, 1),
            horometro_motor=5000, juego_radial=0.10, juego_axial=0.04,
            estado_visual="ROCE_ASPAS",
        )
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertEqual(proy.estado, "CRITICO")

    def test_estado_critico_cuando_supera_limite_radial(self):
        MedicionTurbo.objects.create(
            equipo=self.equipo, fecha=date(2025, 6, 1),
            horometro_motor=5000, juego_radial=0.50, juego_axial=0.04,  # 0.50 > 0.45 límite
        )
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertEqual(proy.estado, "CRITICO")

    def test_estado_critico_cuando_supera_limite_axial(self):
        MedicionTurbo.objects.create(
            equipo=self.equipo, fecha=date(2025, 6, 1),
            horometro_motor=5000, juego_radial=0.10, juego_axial=0.20,  # 0.20 > 0.15 límite
        )
        proy = AnalizadorTurbos.analizar_equipo(self.equipo)
        self.assertEqual(proy.estado, "CRITICO")


# ─────────────────────────────────────────────────────────────
# Tests de _determinar_estado
# ─────────────────────────────────────────────────────────────
class TestDeterminarEstado(TestCase):

    def _config(self):
        from core.models import ConfiguracionSistema
        return ConfiguracionSistema.load()

    def test_ok_con_valores_normales(self):
        config = self._config()
        estado = AnalizadorTurbos._determinar_estado(0.10, 0.05, 5000, config)
        self.assertEqual(estado, "OK")

    def test_atencion_por_porcentaje_radial(self):
        """Radial al 85% del límite (0.45 * 0.85 = 0.3825)."""
        config = self._config()
        estado = AnalizadorTurbos._determinar_estado(0.39, 0.05, 5000, config)
        self.assertEqual(estado, "ATENCION")

    def test_atencion_por_horas_bajas(self):
        """Menos de 500 horas restantes → ATENCIÓN."""
        config = self._config()
        estado = AnalizadorTurbos._determinar_estado(0.10, 0.05, 400, config)
        self.assertEqual(estado, "ATENCION")

    def test_critico_por_radial_sobre_limite(self):
        config = self._config()
        estado = AnalizadorTurbos._determinar_estado(0.46, 0.05, 5000, config)
        self.assertEqual(estado, "CRITICO")

    def test_critico_por_horas_cero(self):
        config = self._config()
        estado = AnalizadorTurbos._determinar_estado(0.10, 0.05, 0, config)
        self.assertEqual(estado, "CRITICO")


# ─────────────────────────────────────────────────────────────
# Tests de analizar_todos
# ─────────────────────────────────────────────────────────────
class TestAnalizarTodos(TestCase):

    def setUp(self):
        for num in [301, 302, 303]:
            eq = crear_equipo(num)
            crear_mediciones_turbo(eq)

    def test_genera_proyeccion_para_cada_equipo(self):
        AnalizadorTurbos.analizar_todos()
        self.assertEqual(ProyeccionTurbo.objects.count(), 3)

    def test_rerrun_no_duplica_proyecciones(self):
        AnalizadorTurbos.analizar_todos()
        AnalizadorTurbos.analizar_todos()
        self.assertEqual(ProyeccionTurbo.objects.count(), 3)
