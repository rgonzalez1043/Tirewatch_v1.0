from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Cambia la unicidad de Equipo.numero de global a por-tipo.
    Antes: numero=unique (global) → no se puede tener GPCO-50 y TETR-50.
    Ahora: unique_together=(numero, tipo) → cada tipo tiene su propio espacio numérico.
    """

    dependencies = [
        ("equipos", "0001_initial"),
    ]

    operations = [
        # 1. Quitar el índice único global de numero
        migrations.AlterField(
            model_name="equipo",
            name="numero",
            field=models.IntegerField(
                help_text="Número identificador del equipo (único dentro del tipo)"
            ),
        ),
        # 2. Agregar unicidad compuesta (numero, tipo)
        migrations.AlterUniqueTogether(
            name="equipo",
            unique_together={("numero", "tipo")},
        ),
        # 3. Actualizar ordering para incluir tipo
        migrations.AlterModelOptions(
            name="equipo",
            options={
                "ordering": ["tipo__codigo", "numero"],
                "verbose_name": "Equipo",
                "verbose_name_plural": "Equipos",
            },
        ),
    ]
