"""
Carga historica de mediciones de opacidad desde CSV/Excel.

Estos registros quedan marcados con origen=HISTORICO y sin archivo ni sha256,
lo que los deja visualmente distinguidos como evidencia de menor jerarquia
frente a los que tienen el PDF original adjunto. Eso es lo honesto de mostrar
en una auditoria.

Columnas esperadas (encabezado en la primera fila):
    tipo_equipo   codigo del TipoEquipo (ej. TRACTO, PORTA)
    numero        numero del equipo (ej. 2178)
    fecha         DD/MM/AAAA o AAAA-MM-DD
    k_medio       ej. 1,73
    k_limite      opcional, default 3.0
    horometro     opcional
    operador      opcional
    observacion   opcional

Uso:
    python manage.py importar_opacidad_csv historico.csv --dry-run
    python manage.py importar_opacidad_csv historico.csv
"""
import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from equipos.models import Equipo, TipoEquipo
from opacidad.models import MedicionOpacidad
from opacidad.services.analizador import AnalizadorOpacidad

FORMATOS_FECHA = ["%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"]


def _fecha(txt):
    txt = (txt or "").strip()
    for f in FORMATOS_FECHA:
        try:
            return datetime.strptime(txt, f).date()
        except ValueError:
            continue
    return None


def _num(txt):
    try:
        return float(str(txt).strip().replace(",", "."))
    except (ValueError, AttributeError):
        return None


class Command(BaseCommand):
    help = "Importa mediciones historicas de opacidad desde un CSV"

    def add_arguments(self, parser):
        parser.add_argument("archivo", type=str)
        parser.add_argument("--dry-run", action="store_true",
                            help="Valida sin escribir en base de datos")
        parser.add_argument("--delimiter", default=";",
                            help="Separador del CSV (default ';')")

    def handle(self, *args, **opts):
        ruta = Path(opts["archivo"])
        if not ruta.exists():
            raise CommandError(f"No existe el archivo {ruta}")

        creadas, omitidas, errores = 0, 0, []
        equipos_tocados = set()

        with ruta.open(encoding="utf-8-sig", newline="") as fh:
            lector = csv.DictReader(fh, delimiter=opts["delimiter"])
            filas = list(lector)

        with transaction.atomic():
            for i, fila in enumerate(filas, start=2):
                fila = {(k or "").strip().lower(): v for k, v in fila.items()}
                cod_tipo = (fila.get("tipo_equipo") or "").strip().upper()
                numero = (fila.get("numero") or "").strip()
                fecha = _fecha(fila.get("fecha"))
                k = _num(fila.get("k_medio"))

                if not (cod_tipo and numero.isdigit() and fecha and k is not None):
                    errores.append(f"Fila {i}: datos incompletos o invalidos")
                    continue

                try:
                    tipo = TipoEquipo.objects.get(codigo__iexact=cod_tipo)
                    equipo = Equipo.objects.get(tipo=tipo, numero=int(numero))
                except (TipoEquipo.DoesNotExist, Equipo.DoesNotExist):
                    errores.append(f"Fila {i}: no existe el equipo {cod_tipo}-{numero}")
                    continue

                if MedicionOpacidad.objects.filter(equipo=equipo, fecha=fecha).exists():
                    omitidas += 1
                    continue

                if not opts["dry_run"]:
                    MedicionOpacidad.objects.create(
                        equipo=equipo,
                        fecha=fecha,
                        k_medio=k,
                        k_limite=_num(fila.get("k_limite")) or 3.0,
                        horometro_motor=int(_num(fila.get("horometro")) or 0) or None,
                        operador=(fila.get("operador") or "").strip(),
                        observaciones=(fila.get("observacion") or "").strip(),
                        origen=MedicionOpacidad.Origen.HISTORICO,
                    )
                creadas += 1
                equipos_tocados.add(equipo.id)

            if opts["dry_run"]:
                transaction.set_rollback(True)

        for eid in equipos_tocados if not opts["dry_run"] else []:
            AnalizadorOpacidad.analizar_equipo(Equipo.objects.get(id=eid))

        self.stdout.write(self.style.SUCCESS(
            f"{'[DRY-RUN] ' if opts['dry_run'] else ''}"
            f"Creadas: {creadas} | Omitidas (duplicadas): {omitidas} | Errores: {len(errores)}"
        ))
        for e in errores[:30]:
            self.stdout.write(self.style.WARNING(f"  {e}"))
        if len(errores) > 30:
            self.stdout.write(self.style.WARNING(f"  ... y {len(errores) - 30} mas"))
