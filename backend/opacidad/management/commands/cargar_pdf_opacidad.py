"""
Carga masiva de PDF de opacidad en modo dry-run.

Recorre una carpeta, parsea cada informe y muestra lo extraido junto con
sus advertencias, SIN escribir nada. Sirve para validar que el parser
soporta el layout de tractos y portacontenedores antes de importar en serio.

Uso:
    python manage.py cargar_pdf_opacidad C:\\informes\\2026-S1
"""
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from opacidad.services import parser_texa


class Command(BaseCommand):
    help = "Parsea PDF de opacidad de una carpeta y reporta lo extraido (dry-run)"

    def add_arguments(self, parser):
        parser.add_argument("carpeta", type=str)

    def handle(self, *args, **opts):
        carpeta = Path(opts["carpeta"])
        if not carpeta.is_dir():
            raise CommandError(f"No es una carpeta: {carpeta}")

        pdfs = sorted(carpeta.glob("*.pdf"))
        if not pdfs:
            self.stdout.write(self.style.WARNING("Sin PDF en la carpeta"))
            return

        ok = 0
        for p in pdfs:
            try:
                d, w = parser_texa.extraer(str(p))
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"{p.name}: ERROR {exc}"))
                continue

            completo = all(d.get(k) is not None for k in ("fecha", "matricula", "k_medio"))
            estilo = self.style.SUCCESS if completo else self.style.ERROR
            self.stdout.write(estilo(
                f"{p.name}: eq={d.get('matricula')} fecha={d.get('fecha')} "
                f"k={d.get('k_medio')} limite={d.get('k_limite')} "
                f"acels={len(d.get('aceleraciones', []))}"
            ))
            for a in w:
                self.stdout.write(self.style.WARNING(f"    ! {a}"))
            ok += 1 if completo else 0

        self.stdout.write(self.style.SUCCESS(
            f"\nParseados correctamente: {ok}/{len(pdfs)}"
        ))
