"""
Tests unitarios — Módulo Neumáticos
====================================
Cubre MotorAnalisis: cálculo de tasas, proyecciones y análisis completo.
Ejecutar: python manage.py test neumaticos
"""
from datetime import date, timedelta

from django.test import TestCase

from equipos.models import Equipo, TipoEquipo, MarcaComponente
from neumaticos.models import Medicion, TasaDesgaste, Proyeccion
from neumaticos.services import MotorAnalisis


# ─────────────────────────────────────────────────────────────
# Fixtures compartidas
# ─────────────────────────────────────────────────────────────
def crear_equipo(numero=101):
    tipo, _ = TipoEquipo.objects.get_or_create(codigo="PC", defaults={"nombre": "Portacontenedor"})
    return Equipo.objects.get_or_create(numero=numero, defaults={"tipo": tipo})[0]


def crear_mediciones_traccion(equipo, n=5, desgaste_por_periodo=2.0, periodo_dias=20):
    """
    Crea n mediciones con desgaste lineal.
    tasa teórica = desgaste_por_periodo / periodo_dias mm/día (valor absoluto).
    """
    MarcaComponente.objects.get_or_create(
        nombre="GOODYEAR", tipo="neumatico",
        defaults={"profundidad_fabrica_mm": 90},
    )
    base = date.today() - timedelta(days=periodo_dias * n)
    base_val_h1 = 60.0
    base_val_h2 = 58.0
    for i in range(n):
        Medicion.objects.create(
            equipo=equipo,
            fecha=base + timedelta(days=periodo_dias * i),
            tipo="traccion",
            marca_nombre="GOODYEAR",
            h1=base_val_h1 - desgaste_por_periodo * i,
            h2=base_val_h2 - desgaste_por_periodo * i,
        )


# ─────────────────────────────────────────────────────────────
# Tests de calcular_tasas
# ─────────────────────────────────────────────────────────────
class TestCalcularTasas(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(101)
        crear_mediciones_traccion(self.equipo)

    def test_retorna_estructura_esperada(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas(tipo="traccion")
        self.assertIn("tasas_marca", res)
        self.assertIn("tasa_global", res)
        self.assertIn("acum_marcas", res)

    def test_detecta_marca_goodyear(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas(tipo="traccion")
        self.assertIn("GOODYEAR", res["tasas_marca"])

    def test_tasas_son_negativas(self):
        """Las tasas representan desgaste → valores negativos (mm perdidos por día)."""
        motor = MotorAnalisis()
        res = motor.calcular_tasas(tipo="traccion")
        for pos, tasa in res["tasa_global"].items():
            self.assertLess(tasa, 0, f"Tasa en {pos} debería ser negativa")

    def test_magnitud_tasa_aproximada(self):
        """Con 2 mm de desgaste cada 20 días, la tasa ≈ 0.10 mm/día."""
        motor = MotorAnalisis()
        res = motor.calcular_tasas(tipo="traccion")
        tasa_h1 = res["tasa_global"].get("h1", 0)
        self.assertAlmostEqual(abs(tasa_h1), 0.10, delta=0.02)

    def test_sin_mediciones_retorna_vacios(self):
        equipo_vacio = crear_equipo(999)
        motor = MotorAnalisis()
        res = motor.calcular_tasas(tipo="traccion")
        # No hay mediciones de equipo 999 con marca distinta → tasa global sí existe
        self.assertIsInstance(res["tasas_marca"], dict)


# ─────────────────────────────────────────────────────────────
# Tests de proyectar_equipo
# ─────────────────────────────────────────────────────────────
class TestProyectarEquipo(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(102)
        crear_mediciones_traccion(self.equipo)

    def test_retorna_proyeccion_no_nula(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        proy = motor.proyectar_equipo(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertIsNotNone(proy)

    def test_horas_restantes_positivas(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        proy = motor.proyectar_equipo(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertGreater(proy["horas_restantes"], 0)

    def test_fecha_cambio_en_futuro(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        proy = motor.proyectar_equipo(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertGreater(proy["fecha_cambio"], date.today())

    def test_posicion_critica_valida(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        proy = motor.proyectar_equipo(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertIn(proy["posicion_critica"].lower(), ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"])

    def test_equipo_sin_mediciones_retorna_none(self):
        equipo_vacio = crear_equipo(888)
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        proy = motor.proyectar_equipo(equipo_vacio, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertIsNone(proy)


# ─────────────────────────────────────────────────────────────
# Tests de ejecutar_analisis (integración)
# ─────────────────────────────────────────────────────────────
class TestEjecutarAnalisis(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(103)
        crear_mediciones_traccion(self.equipo)

    def test_guarda_tasas_en_bd(self):
        motor = MotorAnalisis()
        motor.ejecutar_analisis(tipo="traccion")
        self.assertGreater(TasaDesgaste.objects.filter(tipo="traccion").count(), 0)

    def test_guarda_proyecciones_en_bd(self):
        motor = MotorAnalisis()
        motor.ejecutar_analisis(tipo="traccion")
        self.assertGreater(Proyeccion.objects.filter(tipo="traccion").count(), 0)

    def test_retorna_conteos_correctos(self):
        motor = MotorAnalisis()
        res = motor.ejecutar_analisis(tipo="traccion")
        self.assertIn("proyecciones_generadas", res)
        self.assertIn("tasas_calculadas", res)
        self.assertGreaterEqual(res["proyecciones_generadas"], 1)

    def test_estado_proyeccion_valido(self):
        motor = MotorAnalisis()
        motor.ejecutar_analisis(tipo="traccion")
        for p in Proyeccion.objects.all():
            self.assertIn(p.estado, ["ok", "atencion", "critico"])

    def test_reanalisis_reemplaza_datos_anteriores(self):
        motor = MotorAnalisis()
        motor.ejecutar_analisis(tipo="traccion")
        count1 = Proyeccion.objects.filter(tipo="traccion").count()
        motor.ejecutar_analisis(tipo="traccion")
        count2 = Proyeccion.objects.filter(tipo="traccion").count()
        self.assertEqual(count1, count2)


# ─────────────────────────────────────────────────────────────
# Tests de datos_grafico
# ─────────────────────────────────────────────────────────────
class TestDatosGrafico(TestCase):

    def setUp(self):
        self.equipo = crear_equipo(104)
        crear_mediciones_traccion(self.equipo)

    def test_retorna_lista_no_vacia(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        series = motor.datos_grafico(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertGreater(len(series), 0)

    def test_incluye_puntos_reales_y_proyeccion(self):
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        series = motor.datos_grafico(self.equipo, "traccion", res["tasas_marca"], res["tasa_global"])
        tipos = {s["tipo"] for s in series}
        self.assertIn("real", tipos)
        # Al menos un punto proyectado o límite
        self.assertTrue(tipos & {"proyeccion", "limite"})

    def test_equipo_sin_datos_retorna_lista_vacia(self):
        equipo_vacio = crear_equipo(777)
        motor = MotorAnalisis()
        res = motor.calcular_tasas("traccion")
        series = motor.datos_grafico(equipo_vacio, "traccion", res["tasas_marca"], res["tasa_global"])
        self.assertEqual(series, [])
