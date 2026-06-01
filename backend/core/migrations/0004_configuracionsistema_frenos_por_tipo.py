from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_configuracionsistema_limite_elongacion_cadena_pct_and_more"),
    ]

    operations = [
        # Tambor (Kalmar T2, Terberg)
        migrations.AddField(
            model_name="configuracionsistema",
            name="limite_freno_tambor_mm",
            field=models.FloatField(
                default=6.35,
                help_text="Balata mínima en mm para frenos de TAMBOR (Kalmar T2, Terberg). Ref: 6.35 mm (1/4 pulgada)",
            ),
        ),
        migrations.AddField(
            model_name="configuracionsistema",
            name="prof_fabrica_freno_tambor_mm",
            field=models.FloatField(
                default=20.0,
                help_text="Espesor de fábrica de la balata de tambor en mm (Kalmar T2, Terberg)",
            ),
        ),
        # Disco húmedo (Konecranes)
        migrations.AddField(
            model_name="configuracionsistema",
            name="limite_freno_disco_mm",
            field=models.FloatField(
                default=3.0,
                help_text="Pastilla mínima en mm para frenos de DISCO (Konecranes — disco húmedo/bañado en aceite)",
            ),
        ),
        migrations.AddField(
            model_name="configuracionsistema",
            name="prof_fabrica_freno_disco_mm",
            field=models.FloatField(
                default=15.0,
                help_text="Espesor de fábrica de la pastilla de disco húmedo en mm (Konecranes)",
            ),
        ),
        # Tambor de aire / chasis
        migrations.AddField(
            model_name="configuracionsistema",
            name="limite_freno_tambor_aire_mm",
            field=models.FloatField(
                default=6.35,
                help_text="Balata mínima en mm para frenos de TAMBOR DE AIRE (ejes chasis / remolques portacontenedoras)",
            ),
        ),
        migrations.AddField(
            model_name="configuracionsistema",
            name="prof_fabrica_freno_tambor_aire_mm",
            field=models.FloatField(
                default=20.0,
                help_text="Espesor de fábrica de la balata de tambor de aire en mm (ejes chasis)",
            ),
        ),
    ]
