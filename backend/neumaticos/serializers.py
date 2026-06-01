from rest_framework import serializers
from .models import Medicion, TasaDesgaste, Proyeccion, Neumatico


class MedicionSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    equipo_tipo_codigo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    equipo_codigo_completo = serializers.CharField(source="equipo.codigo_completo", read_only=True)
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    posiciones = serializers.DictField(read_only=True)
    registrado_por_nombre = serializers.CharField(
        source="registrado_por.get_full_name", read_only=True, default=""
    )

    class Meta:
        model = Medicion
        fields = [
            "id", "equipo", "equipo_numero", "equipo_tipo_codigo", "equipo_codigo_completo",
            "fecha", "tipo", "tipo_display",
            "marca_nombre",
            "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8",
            "d1", "d2",
            "posiciones",
            "origen", "registrado_por", "registrado_por_nombre",
            "horometro", "observaciones",
            "created_at",
        ]
        read_only_fields = ["id", "created_at", "posiciones"]


class MedicionCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear mediciones desde terreno"""
    equipo_numero = serializers.IntegerField(write_only=True)
    tipo_equipo_codigo = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = Medicion
        fields = [
            "equipo_numero", "tipo_equipo_codigo",
            "fecha", "tipo", "marca_nombre",
            "horometro",
            "h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8",
            "d1", "d2",
            "horometro", "observaciones",
        ]

    def validate(self, data):
        from equipos.models import Equipo
        numero = data.pop("equipo_numero")
        tipo_codigo = data.pop("tipo_equipo_codigo", "")
        try:
            if tipo_codigo:
                data["_equipo"] = Equipo.objects.get(numero=numero, tipo__codigo=tipo_codigo)
            else:
                data["_equipo"] = Equipo.objects.get(numero=numero)
        except Equipo.DoesNotExist:
            lbl = f"{tipo_codigo}-{numero}" if tipo_codigo else str(numero)
            raise serializers.ValidationError({"equipo_numero": [f"No existe equipo {lbl}"]})
        except Equipo.MultipleObjectsReturned:
            raise serializers.ValidationError({
                "equipo_numero": [f"Hay varios equipos con número {numero}. Especifica el tipo (GPCO, TETR, CHA…)"]
            })
        return data

    def create(self, validated_data):
        equipo = validated_data.pop("_equipo")
        validated_data["equipo"] = equipo
        validated_data["origen"] = "terreno"
        validated_data["registrado_por"] = self.context["request"].user
        return super().create(validated_data)


class TasaDesgasteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TasaDesgaste
        fields = [
            "id", "marca_nombre", "tipo", "posicion",
            "tasa_mm_dia", "tasa_mm_hora", "tasa_mm_100h",
            "total_mm_acum", "total_dias_acum", "n_mediciones",
            "calculado_en",
        ]


class ProyeccionSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    equipo_tipo_codigo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    equipo_codigo_completo = serializers.CharField(source="equipo.codigo_completo", read_only=True)
    estado = serializers.CharField(read_only=True)

    class Meta:
        model = Proyeccion
        fields = [
            "id", "equipo", "equipo_numero", "equipo_tipo_codigo", "equipo_codigo_completo", "tipo",
            "marca_nombre", "posicion_critica", "valor_actual_mm",
            "horas_restantes", "fecha_cambio_estimada",
            "fecha_ultima_medicion", "estado", "calculado_en",
        ]


class NeumaticSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)

    class Meta:
        model = Neumatico
        fields = [
            "id", "equipo", "equipo_numero", "marca", "marca_nombre",
            "tipo", "posicion", "serie",
            "fecha_instalacion", "horometro_instalacion",
            "profundidad_inicial_mm", "activo",
            "fecha_retiro", "motivo_retiro",
        ]
