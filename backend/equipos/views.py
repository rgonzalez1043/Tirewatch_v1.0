from rest_framework import viewsets, permissions
from django_filters.rest_framework import DjangoFilterBackend
from .models import Equipo, TipoEquipo, MarcaComponente
from .serializers import (
    EquipoSerializer, TipoEquipoSerializer, MarcaComponenteSerializer
)


class EquipoViewSet(viewsets.ModelViewSet):
    """CRUD de Equipos"""
    queryset = Equipo.objects.select_related("tipo").all()
    serializer_class = EquipoSerializer
    filterset_fields = ["tipo", "estado"]
    search_fields = ["numero", "nombre"]
    ordering_fields = ["numero", "estado", "fecha_registro"]


class TipoEquipoViewSet(viewsets.ModelViewSet):
    """CRUD de Tipos de Equipo"""
    queryset = TipoEquipo.objects.prefetch_related("equipos").all()
    serializer_class = TipoEquipoSerializer
    search_fields = ["nombre", "codigo"]


class MarcaComponenteViewSet(viewsets.ModelViewSet):
    """CRUD de Marcas de Componentes"""
    queryset = MarcaComponente.objects.all()
    serializer_class = MarcaComponenteSerializer
    filterset_fields = ["tipo", "activo"]
    search_fields = ["nombre"]
