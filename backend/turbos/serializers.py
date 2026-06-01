from rest_framework import serializers
from .models import MedicionTurbo, ProyeccionTurbo


class MedicionTurboSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)
    equipo_tipo_codigo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    equipo_codigo_completo = serializers.CharField(source="equipo.codigo_completo", read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MedicionTurbo
        fields = [
            "id", "equipo", "equipo_numero", "equipo_tipo_codigo", "equipo_codigo_completo",
            "fecha", "horometro_motor",
            "juego_radial", "juego_axial", "estado_visual", "observaciones",
            "registrado_por", "registrado_por_nombre", "created_at"
        ]
        read_only_fields = ["registrado_por"]

    def get_registrado_por_nombre(self, obj):
        if obj.registrado_por:
            return obj.registrado_por.get_full_name() or obj.registrado_por.username
        return "Sistema"


class MedicionTurboCreateSerializer(serializers.ModelSerializer):
    """Para guardar mediciones rápidas desde terreno por N° Equipo."""
    equipo_numero = serializers.IntegerField(write_only=True)
    tipo_equipo_codigo = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')

    class Meta:
        model = MedicionTurbo
        fields = [
            "equipo_numero", "tipo_equipo_codigo",
            "fecha", "horometro_motor",
            "juego_radial", "juego_axial", "estado_visual", "observaciones"
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
        
        # Inyectar el usuario del request (establecido en la vista)
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data["registrado_por"] = user

        medicion = super().create(validated_data)
        
        # Ejecutar análisis predictivo de Turbos para este equipo
        from .services import AnalizadorTurbos
        AnalizadorTurbos.analizar_equipo(equipo)
        
        return medicion


class ProyeccionTurboSerializer(serializers.ModelSerializer):
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)

    class Meta:
        model = ProyeccionTurbo
        fields = [
            "equipo", "equipo_numero", "tasa_radial_1000h", "tasa_axial_1000h",
            "horas_motor_restantes", "estado", "ultima_medicion_fecha",
            "ultima_medicion_horometro", "juego_radial_actual", "juego_axial_actual",
            "updated_at"
        ]
