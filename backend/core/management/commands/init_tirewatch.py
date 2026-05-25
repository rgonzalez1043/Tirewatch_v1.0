"""
Comando para inicializar datos base de TireWatch.
Uso: python manage.py init_tirewatch
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Departamento
from equipos.models import TipoEquipo, MarcaComponente

User = get_user_model()


class Command(BaseCommand):
    help = "Inicializa datos base para TireWatch (departamentos, tipos, marcas)"

    def handle(self, *args, **options):
        self.stdout.write("Inicializando TireWatch...\n")

        # Departamentos
        deptos = [
            ("Confiabilidad", "CONF"),
            ("Mantenimiento", "MANT"),
            ("Operaciones", "OPER"),
            ("Ingeniería", "ING"),
            ("Seguridad", "SEG"),
        ]
        for nombre, codigo in deptos:
            obj, created = Departamento.objects.get_or_create(
                codigo=codigo, defaults={"nombre": nombre}
            )
            status = "CREADO" if created else "existe"
            self.stdout.write(f"  Departamento: {nombre} [{status}]")

        # Tipos de equipo
        tipos = [
            ("Portacontenedor", "PC"),
            ("RTG", "RTG"),
            ("STS", "STS"),
            ("Reach Stacker", "RS"),
            ("Terminal Tractor", "TT"),
        ]
        for nombre, codigo in tipos:
            obj, created = TipoEquipo.objects.get_or_create(
                codigo=codigo, defaults={"nombre": nombre}
            )
            status = "CREADO" if created else "existe"
            self.stdout.write(f"  Tipo equipo: {nombre} [{status}]")

        # Marcas de neumáticos
        marcas_neum = [
            ("GOODYEAR", 90),
            ("CONTINENTAL", 75),
            ("BKT", 70),
        ]
        for nombre, prof in marcas_neum:
            obj, created = MarcaComponente.objects.get_or_create(
                nombre=nombre, tipo="neumatico",
                defaults={"profundidad_fabrica_mm": prof}
            )
            status = "CREADO" if created else "existe"
            self.stdout.write(f"  Marca neumático: {nombre} ({prof}mm) [{status}]")

        # Marcas de turbos (para futuro)
        marcas_turbo = ["HOLSET", "GARRETT", "BorgWarner"]
        for nombre in marcas_turbo:
            obj, created = MarcaComponente.objects.get_or_create(
                nombre=nombre, tipo="turbo"
            )
            status = "CREADO" if created else "existe"
            self.stdout.write(f"  Marca turbo: {nombre} [{status}]")

        # Superusuario
        import os
        admin_pass = os.environ.get("TIREWATCH_ADMIN_PASSWORD", "tirewatch2025")
        
        if not User.objects.filter(is_superuser=True).exists():
            user = User.objects.create_superuser(
                username="admin",
                email="admin@sti.cl",
                password=admin_pass,
                first_name="Admin",
                last_name="TireWatch",
                rol="admin",
            )
            # Nota: create_superuser automáticamente aplica hash PBKDF2 SHA-256
            self.stdout.write(
                self.style.WARNING(
                    f"\n  Superusuario creado."
                    f"\n  ¡CAMBIAR CONTRASEÑA EN PRODUCCIÓN O DEFINIR TIREWATCH_ADMIN_PASSWORD!"
                )
            )

        self.stdout.write(self.style.SUCCESS("\nTireWatch inicializado correctamente."))
