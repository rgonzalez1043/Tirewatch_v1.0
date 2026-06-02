"""
Comando personalizado runserver para Tirewatch.
Sobreescribe el puerto por defecto (8000) para usar el 8011.
"""
from django.contrib.staticfiles.management.commands.runserver import Command as StaticFilesRunserverCommand


class Command(StaticFilesRunserverCommand):
    default_port = "8011"
