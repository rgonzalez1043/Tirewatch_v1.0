from django.db import migrations


def setup_tipos(apps, schema_editor):
    TipoEquipo = apps.get_model("equipos", "TipoEquipo")

    # Agregar CHA (Chasis portacontenedoras)
    TipoEquipo.objects.get_or_create(
        codigo="CHA",
        defaults={
            "nombre": "Chasis",
            "descripcion": "Chasis portacontenedoras. "
                           "Neumáticos solo eje trasero (trasero izq/der/int/ext). "
                           "Frenos de tambor de aire en eje trasero.",
        },
    )

    # Eliminar STS y RTG — 0 equipos, fuera del alcance de Terreno
    TipoEquipo.objects.filter(codigo__in=["STS", "RTG"]).delete()


def reverse_setup(apps, schema_editor):
    TipoEquipo = apps.get_model("equipos", "TipoEquipo")
    TipoEquipo.objects.filter(codigo="CHA").delete()
    TipoEquipo.objects.get_or_create(codigo="STS", defaults={"nombre": "STS"})
    TipoEquipo.objects.get_or_create(codigo="RTG", defaults={"nombre": "RTG"})


class Migration(migrations.Migration):

    dependencies = [
        ("equipos", "0003_fix_tipo_equipo_codigos"),
    ]

    operations = [
        migrations.RunPython(setup_tipos, reverse_code=reverse_setup),
    ]
