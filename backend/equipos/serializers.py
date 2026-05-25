from rest_framework import serializers
from .models import Equipo, TipoEquipo, MarcaComponente


class MarcaComponenteSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)

    class Meta:
        model = MarcaComponente
        fields = [
            "id", "nombre", "tipo", "tipo_display",
            "profundidad_fabrica_mm", "vida_util_horas", "activo",
        ]


class TipoEquipoSerializer(serializers.ModelSerializer):
    cantidad_equipos = serializers.IntegerField(
        source="equipos.count", read_only=True
    )

    class Meta:
        model = TipoEquipo
        fields = ["id", "nombre", "codigo", "descripcion", "cantidad_equipos"]


class EquipoSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source="tipo.nombre", read_only=True)
    tipo_codigo = serializers.CharField(source="tipo.codigo", read_only=True)
    estado_display = serializers.CharField(source="get_estado_display", read_only=True)

    class Meta:
        model = Equipo
        fields = [
            "id", "numero", "tipo", "tipo_nombre", "tipo_codigo",
            "nombre", "estado", "estado_display",
            "horometro_actual", "horas_operacion_diaria",
            "fecha_registro", "notas",
        ]


class EquipoResumenSerializer(serializers.ModelSerializer):
    """Serializer ligero para listas y selects"""
    class Meta:
        model = Equipo
        fields = ["id", "numero", "nombre", "estado"]
