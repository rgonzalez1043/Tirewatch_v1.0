from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from .models import Equipo, TipoEquipo, MarcaComponente
from .serializers import (
    EquipoSerializer, TipoEquipoSerializer, MarcaComponenteSerializer
)

# Mapeo de códigos internos → prefijos de la API externa de horómetros
_PREFIJO_API = {
    "GPCO": "POR",
    "TETR": "TRA",
    "CHA": "CHA",   # pendiente — cuando esté disponible en la API
}


class EquipoViewSet(viewsets.ModelViewSet):
    """CRUD de Equipos"""
    queryset = Equipo.objects.select_related("tipo").all()
    serializer_class = EquipoSerializer
    filterset_fields = ["tipo", "estado", "numero"]
    search_fields = ["nombre"]
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def horometro_externo(request):
    """
    Proxy hacia la API interna de horómetros.
    Consulta el horómetro de un equipo por tipo, número y fecha opcional.

    Parámetros:
        ?tipo=GPCO&numero=55[&fecha=2026-06-18]   → llama a POR-0055/horometros
        ?tipo=TETR&numero=2178[&fecha=2026-06-18] → llama a TRA-2178/horometros (o TRA-0178)

    Respuesta:
        { codigo_externo, horometro, fecha, disponible, error }
    """
    from .services import consultar_horometro_externo

    tipo = request.query_params.get("tipo", "").upper()
    numero = request.query_params.get("numero", "").strip()
    fecha = request.query_params.get("fecha", "").strip() or None

    if not tipo or not numero:
        return Response(
            {"error": "Se requieren los parámetros 'tipo' y 'numero'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    res = consultar_horometro_externo(tipo, numero, fecha=fecha)
    if not res["disponible"]:
        status_code = status.HTTP_404_NOT_FOUND if "no encontrado" in str(res.get("error", "")) else status.HTTP_200_OK
        return Response(res, status=status_code)

    return Response(res, status=status.HTTP_200_OK)

