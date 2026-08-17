"""Recalcula las proyecciones de opacidad. Util para tarea programada."""
from django.core.management.base import BaseCommand

from opacidad.services.analizador import AnalizadorOpacidad


class Command(BaseCommand):
    help = "Recalcula las proyecciones de tendencia de opacidad de toda la flota"

    def handle(self, *args, **opts):
        n = AnalizadorOpacidad.analizar_todos()
        self.stdout.write(self.style.SUCCESS(f"Proyecciones actualizadas: {n}"))
