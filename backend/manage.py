#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

DEFAULT_PORT = "8011"

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tirewatch.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    # Si se ejecuta runserver sin especificar puerto, usar el puerto por defecto
    args = sys.argv[:]
    if len(args) >= 2 and args[1] == "runserver":
        # Busca si ya hay un argumento de puerto/dirección (no empieza con '-')
        has_addr = any(
            not a.startswith("-") for a in args[2:]
        )
        if not has_addr:
            args.append(DEFAULT_PORT)

    execute_from_command_line(args)

if __name__ == "__main__":
    main()
