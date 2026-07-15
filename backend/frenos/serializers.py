from rest_framework import serializers
from .models import ComponenteFreno, MedicionFreno, ProyeccionFreno


class ComponenteFrenoSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    posicion_display = serializers.CharField(source="get_posicion_display", read_only=True)
    tipo_freno_display = serializers.CharField(source="get_tipo_freno_display", read_only=True)
    motivo_retiro_display = serializers.CharField(source="get_motivo_retiro_display", read_only=True, default="")
    registrado_por_nombre = serializers.CharField(
        source="registrado_por.get_full_name", read_only=True, default=""
    )

    # Proyección embebida (si existe)
    estado = serializers.CharField(source="proyeccion.estado", read_only=True, default="OK")
    espesor_actual_mm = serializers.FloatField(source="proyeccion.espesor_actual_mm", read_only=True, default=None)
    desgaste_pct = serializers.FloatField(source="proyeccion.desgaste_pct", read_only=True, default=None)
    horas_restantes = serializers.FloatField(source="proyeccion.horas_restantes", read_only=True, default=99999)
    fecha_cambio_estimada = serializers.DateField(source="proyeccion.fecha_cambio_estimada", read_only=True, default=None)
    tasa_desgaste_mm_1000h = serializers.FloatField(source="proyeccion.tasa_desgaste_mm_1000h", read_only=True, default=0)
    n_mediciones = serializers.IntegerField(source="proyeccion.n_mediciones", read_only=True, default=0)
    ultima_medicion_fecha = serializers.DateField(source="proyeccion.ultima_medicion_fecha", read_only=True, default=None)

    class Meta:
        model = ComponenteFreno
        fields = [
            "id", "equipo", "equipo_numero",
            "posicion", "posicion_display",
            "tipo_freno", "tipo_freno_display",
            "espesor_fabrica_mm",
            "fecha_instalacion", "horometro_instalacion",
            "activo", "fecha_retiro", "motivo_retiro", "motivo_retiro_display",
            "notas", "registrado_por", "registrado_por_nombre",
            "created_at",
            # Proyección embebida
            "estado", "espesor_actual_mm", "desgaste_pct",
            "horas_restantes", "fecha_cambio_estimada",
            "tasa_desgaste_mm_1000h", "n_mediciones", "ultima_medicion_fecha",
        ]
        read_only_fields = ["id", "created_at"]


class MedicionFrenoSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    componente_posicion = serializers.CharField(
        source="componente.get_posicion_display", read_only=True
    )
    componente_tipo = serializers.CharField(
        source="componente.get_tipo_freno_display", read_only=True
    )
    registrado_por_nombre = serializers.CharField(
        source="registrado_por.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = MedicionFreno
        fields = [
            "id", "componente", "componente_posicion", "componente_tipo",
            "equipo", "equipo_numero",
            "fecha", "horometro", "espesor_mm",
            "observaciones", "registrado_por", "registrado_por_nombre",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProyeccionFrenoSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    equipo_tipo = serializers.CharField(source="equipo.tipo.nombre", read_only=True, default="")
    posicion = serializers.CharField(source="componente.posicion", read_only=True)
    posicion_display = serializers.CharField(source="componente.get_posicion_display", read_only=True)
    tipo_freno = serializers.CharField(source="componente.tipo_freno", read_only=True)
    tipo_freno_display = serializers.CharField(source="componente.get_tipo_freno_display", read_only=True)
    espesor_fabrica_mm = serializers.FloatField(source="componente.espesor_fabrica_mm", read_only=True)

    class Meta:
        model = ProyeccionFreno
        fields = [
            "id", "componente",
            "equipo", "equipo_numero", "equipo_tipo",
            "posicion", "posicion_display",
            "tipo_freno", "tipo_freno_display",
            "espesor_fabrica_mm",
            "espesor_actual_mm", "desgaste_pct",
            "tasa_desgaste_mm_1000h", "horas_restantes",
            "fecha_cambio_estimada", "estado",
            "ultima_medicion_fecha", "ultima_medicion_horometro",
            "n_mediciones", "updated_at",
        ]
        read_only_fields = fields


class ReemplazoFrenoSerializer(serializers.Serializer):
    """Payload para registrar el reemplazo de un componente de freno."""
    fecha_retiro = serializers.DateField()
    motivo_retiro = serializers.ChoiceField(choices=ComponenteFreno.MOTIVO_RETIRO_CHOICES)
    nuevo_espesor_fabrica_mm = serializers.FloatField(min_value=1.0)
    fecha_instalacion = serializers.DateField()
    horometro_instalacion = serializers.FloatField(required=False, allow_null=True)
    notas = serializers.CharField(required=False, allow_blank=True, default="")
