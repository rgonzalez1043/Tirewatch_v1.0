from rest_framework import serializers
from .models import MedicionCadena, ProyeccionCadena


class MedicionCadenaSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    registrado_por_nombre = serializers.CharField(
        source="registrado_por.get_full_name", read_only=True, default=""
    )
    elongacion_pct = serializers.FloatField(read_only=True)
    tipo_cadena_display = serializers.CharField(source="get_tipo_cadena_display", read_only=True)

    class Meta:
        model = MedicionCadena
        fields = [
            "id", "equipo", "equipo_numero", "fecha", "horometro",
            "tipo_cadena", "tipo_cadena_display",
            "longitud_nominal_mm", "longitud_medida_mm", "num_eslabones",
            "elongacion_pct",
            "observaciones", "registrado_por", "registrado_por_nombre",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ProyeccionCadenaSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    equipo_tipo_codigo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    equipo_tipo = serializers.CharField(source="equipo.tipo.nombre", read_only=True)
    equipo_codigo_completo = serializers.CharField(source="equipo.codigo_completo", read_only=True)

    class Meta:
        model = ProyeccionCadena
        fields = [
            "id", "equipo", "equipo_numero", "equipo_tipo_codigo", "equipo_tipo",
            "equipo_codigo_completo",
            "tipo_cadena",
            "elongacion_actual_pct", "longitud_nominal_mm", "longitud_actual_mm",
            "tasa_elongacion_pct_1000h", "horas_restantes",
            "fecha_reemplazo_estimada", "estado",
            "ultima_medicion_fecha", "ultima_medicion_horometro",
            "updated_at",
        ]
        read_only_fields = fields
