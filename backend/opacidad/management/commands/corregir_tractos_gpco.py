"""
Comando para corregir equipos de la serie 2000 que fueron erróneamente clasificados
como GPCO (Portas) debido al fabricante 'Kalmar' en los PDFs, reasignándolos a TETR (Tractos).

Uso:
    python manage.py corregir_tractos_gpco
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from equipos.models import Equipo, TipoEquipo
from opacidad.models import MedicionOpacidad, ProyeccionOpacidad, ImportacionOpacidad
from opacidad.services.analizador import AnalizadorOpacidad


class Command(BaseCommand):
    help = "Reasigna mediciones de tractos (números >= 100) erróneamente creados como GPCO hacia TETR."

    def handle(self, *args, **options):
        tipo_tetr = TipoEquipo.objects.filter(codigo="TETR").first()
        tipo_gpco = TipoEquipo.objects.filter(codigo="GPCO").first()

        if not tipo_tetr or not tipo_gpco:
            self.stderr.write("No se encontraron los tipos de equipo TETR y/o GPCO.")
            return

        gpcos_malos = list(Equipo.objects.filter(tipo=tipo_gpco, numero__gte=100))
        if not gpcos_malos:
            self.stdout.write(self.style.SUCCESS("No se encontraron equipos GPCO con número >= 100 para corregir."))
            return

        self.stdout.write(f"Encontrados {len(gpcos_malos)} equipos GPCO erróneos. Procediendo a corregir...")

        with transaction.atomic():
            for g in gpcos_malos:
                num = g.numero
                tetr, created = Equipo.objects.get_or_create(
                    tipo=tipo_tetr,
                    numero=num,
                    defaults={"nombre": f"Terminal Tracto {num}", "estado": g.estado}
                )
                if created:
                    self.stdout.write(f"  + Creado equipo TETR-{num}")

                # Mover mediciones
                meds = MedicionOpacidad.objects.filter(equipo=g)
                for m in meds:
                    dup = MedicionOpacidad.objects.filter(equipo=tetr, fecha=m.fecha).exclude(id=m.id).first()
                    if dup:
                        m.delete()
                    else:
                        m.equipo = tetr
                        m.save(update_fields=["equipo"])

                # Mover importaciones
                ImportacionOpacidad.objects.filter(equipo_sugerido=g).update(equipo_sugerido=tetr)

                # Eliminar proyección vieja del GPCO falso
                ProyeccionOpacidad.objects.filter(equipo=g).delete()

                # Eliminar el equipo falso GPCO
                g.delete()
                self.stdout.write(f"  ✓ Reasignado GPCO-{num} -> TETR-{num}")

            # Recalcular todas las proyecciones
            n = AnalizadorOpacidad.analizar_todos()
            self.stdout.write(self.style.SUCCESS(f"Corrección completada exitosamente. {n} proyecciones recalculadas."))
