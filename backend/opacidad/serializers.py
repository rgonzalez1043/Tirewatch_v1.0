from rest_framework import serializers

from equipos.models import Equipo
from .models import (
    Opacimetro, MedicionOpacidad, AceleracionOpacidad,
    ProyeccionOpacidad, ImportacionOpacidad,
)


class OpacimetroSerializer(serializers.ModelSerializer):
    vigente_hoy = serializers.BooleanField(read_only=True)

    class Meta:
        model = Opacimetro
        fields = "__all__"


class AceleracionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AceleracionOpacidad
        fields = ["numero", "k", "rpm_ralenti", "rpm_maximo", "tiempo_s"]


class MedicionOpacidadSerializer(serializers.ModelSerializer):
    equipo_codigo = serializers.CharField(source="equipo.codigo_completo", read_only=True)
    equipo_tipo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    aceleraciones = AceleracionSerializer(many=True, read_only=True)
    opacimetro_str = serializers.CharField(source="opacimetro.__str__", read_only=True)
    pct_limite = serializers.FloatField(read_only=True)
    margen = serializers.FloatField(read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = MedicionOpacidad
        fields = [
            "id", "equipo", "equipo_codigo", "equipo_tipo", "fecha", "hora", "periodo",
            "horometro_motor", "k_medio", "k_limite", "aprobado", "pct_limite", "margen",
            "temp_aceite", "rpm_ralenti", "rpm_maximo",
            "opacimetro", "opacimetro_str", "calibracion_vigente",
            "origen", "campos_manuales", "advertencias", "operador", "observaciones",
            "aceleraciones", "archivo_url", "sha256",
            "anulado", "motivo_anulacion", "created_at",
        ]
        read_only_fields = ["periodo", "aprobado", "calibracion_vigente", "sha256"]

    def get_archivo_url(self, obj):
        if not obj.archivo:
            return None
        request = self.context.get("request")
        url = obj.archivo.url
        return request.build_absolute_uri(url) if request else url


class MedicionOpacidadCreateSerializer(serializers.ModelSerializer):
    """Alta manual (medicion en terreno, sin PDF)."""
    aceleraciones = AceleracionSerializer(many=True, required=False)
    tipo_id = serializers.IntegerField(required=False, allow_null=True, write_only=True)
    numero = serializers.IntegerField(required=False, allow_null=True, write_only=True)

    class Meta:
        model = MedicionOpacidad
        fields = [
            "equipo", "tipo_id", "numero", "fecha", "hora", "horometro_motor",
            "k_medio", "k_limite", "temp_aceite", "rpm_ralenti", "rpm_maximo",
            "opacimetro", "origen", "operador", "observaciones", "aceleraciones",
        ]
        extra_kwargs = {
            "equipo": {"required": False, "allow_null": True},
        }

    def validate_k_medio(self, v):
        if v < 0 or v > 20:
            raise serializers.ValidationError("k fuera de rango fisico razonable (0-20 1/m)")
        return v

    def validate(self, attrs):
        if attrs.get("origen") not in (
            MedicionOpacidad.Origen.MANUAL, MedicionOpacidad.Origen.HISTORICO
        ):
            attrs["origen"] = MedicionOpacidad.Origen.MANUAL

        if not attrs.get("equipo"):
            tipo_id = attrs.pop("tipo_id", None)
            numero = attrs.pop("numero", None)
            if not tipo_id or not numero:
                raise serializers.ValidationError({"equipo": "Debe especificar un equipo o indicar tipo_id y numero."})
            from equipos.models import TipoEquipo
            try:
                tipo_obj = TipoEquipo.objects.get(id=tipo_id)
            except TipoEquipo.DoesNotExist:
                raise serializers.ValidationError({"tipo_id": "Tipo de equipo no válido."})
            equipo_obj, _ = Equipo.objects.get_or_create(
                tipo=tipo_obj,
                numero=numero,
                defaults={"nombre": f"{tipo_obj.nombre} {numero}"},
            )
            attrs["equipo"] = equipo_obj
        else:
            attrs.pop("tipo_id", None)
            attrs.pop("numero", None)

        return attrs

    def create(self, validated):
        acels = validated.pop("aceleraciones", [])
        user = self.context["request"].user if "request" in self.context else None
        if user and user.is_authenticated:
            validated["registrado_por"] = user
        medicion = MedicionOpacidad.objects.create(**validated)
        for a in acels:
            AceleracionOpacidad.objects.create(medicion=medicion, **a)
        return medicion


class ProyeccionOpacidadSerializer(serializers.ModelSerializer):
    equipo_codigo = serializers.CharField(source="equipo.codigo_completo", read_only=True)
    equipo_tipo = serializers.CharField(source="equipo.tipo.codigo", read_only=True)
    equipo_numero = serializers.IntegerField(source="equipo.numero", read_only=True)

    class Meta:
        model = ProyeccionOpacidad
        fields = "__all__"


class ImportacionOpacidadSerializer(serializers.ModelSerializer):
    equipo_sugerido_codigo = serializers.CharField(
        source="equipo_sugerido.codigo_completo", read_only=True, default=None
    )

    class Meta:
        model = ImportacionOpacidad
        fields = [
            "id", "nombre_original", "sha256", "datos_extraidos", "advertencias",
            "equipo_sugerido", "equipo_sugerido_codigo", "matricula_detectada",
            "estado", "medicion", "motivo_rechazo", "created_at",
        ]
        read_only_fields = fields


class ConfirmarImportacionSerializer(serializers.Serializer):
    """
    Confirmacion humana de una importacion. El usuario puede corregir
    cualquier campo antes de que se cree la medicion definitiva.
    """
    equipo = serializers.PrimaryKeyRelatedField(queryset=Equipo.objects.all(), required=False, allow_null=True)
    tipo_id = serializers.IntegerField(required=False, allow_null=True)
    numero = serializers.IntegerField(required=False, allow_null=True)
    fecha = serializers.DateField()
    k_medio = serializers.FloatField()
    k_limite = serializers.FloatField()
    horometro_motor = serializers.IntegerField(required=False, allow_null=True)
    temp_aceite = serializers.IntegerField(required=False, allow_null=True)
    rpm_ralenti = serializers.IntegerField(required=False, allow_null=True)
    rpm_maximo = serializers.IntegerField(required=False, allow_null=True)
    operador = serializers.CharField(required=False, allow_blank=True)
    observaciones = serializers.CharField(required=False, allow_blank=True)
