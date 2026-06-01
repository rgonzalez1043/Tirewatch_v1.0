from django.db import migrations


def fix_codigos(apps, schema_editor):
    TipoEquipo = apps.get_model("equipos", "TipoEquipo")

    # PC → GPCO  (portacontenedor / reach stacker — mismo tipo en esta terminal)
    TipoEquipo.objects.filter(codigo="PC").update(
        codigo="GPCO",
        nombre="Portacontenedor / Reach Stacker",
        descripcion="Portacontenedoras y reach stackers de patio (GPCO). "
                    "Incluye: Konecranes RST, Taylor, y similares.",
    )

    # TT → TETR  (terminal tractor)
    TipoEquipo.objects.filter(codigo="TT").update(
        codigo="TETR",
        nombre="Terminal Tracto",
        descripcion="Tractos de terminal (TETR). Incluye: Kalmar T2, Terberg YT.",
    )

    # RS (Reach Stacker separado) — 0 equipos, se elimina porque queda cubierto por GPCO
    TipoEquipo.objects.filter(codigo="RS").delete()


def reverse_fix(apps, schema_editor):
    TipoEquipo = apps.get_model("equipos", "TipoEquipo")
    TipoEquipo.objects.filter(codigo="GPCO").update(codigo="PC", nombre="Portacontenedor")
    TipoEquipo.objects.filter(codigo="TETR").update(codigo="TT", nombre="Terminal Tractor")


class Migration(migrations.Migration):

    dependencies = [
        ("equipos", "0002_equipo_numero_unique_por_tipo"),
    ]

    operations = [
        migrations.RunPython(fix_codigos, reverse_code=reverse_fix),
    ]
