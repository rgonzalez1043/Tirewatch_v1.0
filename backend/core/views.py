from rest_framework import status, generics, permissions
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import login, logout
from .models import Departamento
from .serializers import (
    LoginSerializer, RegistroSerializer, UsuarioSerializer, DepartamentoSerializer
)


class LoginView(APIView):
    """POST /api/auth/login/"""
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        
        # Iniciar sesión en Django (crea la cookie de sesión para las vistas web)
        login(request, user)
        
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "usuario": UsuarioSerializer(user).data,
        })


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    def post(self, request):
        if hasattr(request.user, "auth_token"):
            request.user.auth_token.delete()
        
        # Cerrar sesión en Django (elimina la cookie)
        logout(request)
        
        return Response({"detail": "Sesión cerrada"}, status=status.HTTP_200_OK)


class PerfilView(APIView):
    """GET /api/auth/perfil/"""
    def get(self, request):
        return Response(UsuarioSerializer(request.user).data)


class RegistroView(generics.CreateAPIView):
    """POST /api/auth/registro/ — Solo administradores pueden crear cuentas vía API."""
    serializer_class = RegistroSerializer
    permission_classes = [permissions.IsAdminUser]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "usuario": UsuarioSerializer(user).data,
        }, status=status.HTTP_201_CREATED)


class DepartamentoListView(generics.ListAPIView):
    """GET /api/auth/departamentos/"""
    queryset = Departamento.objects.filter(activo=True)
    serializer_class = DepartamentoSerializer
    permission_classes = [permissions.AllowAny]
