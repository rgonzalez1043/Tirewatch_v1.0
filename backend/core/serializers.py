from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import Usuario, Departamento


class DepartamentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departamento
        fields = ["id", "nombre", "codigo", "activo"]


class UsuarioSerializer(serializers.ModelSerializer):
    departamento_nombre = serializers.CharField(
        source="departamento.nombre", read_only=True
    )

    class Meta:
        model = Usuario
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "rol", "cargo", "departamento", "departamento_nombre",
            "telefono", "puede_editar", "puede_administrar",
        ]
        read_only_fields = ["id", "puede_editar", "puede_administrar"]


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(**data)
        if user and user.is_active:
            return user
        raise serializers.ValidationError("Credenciales inválidas")


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = [
            "username", "email", "password", "first_name", "last_name",
            "rol", "departamento", "cargo",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user
