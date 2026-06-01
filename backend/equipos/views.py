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
    Consulta el horómetro actual de un equipo por tipo y número.

    Parámetros:
        ?tipo=GPCO&numero=55   → llama a POR-0055/horometros
        ?tipo=TETR&numero=174  → llama a TRA-0174/horometros

    Respuesta:
        { codigo_externo, horometro, fecha, disponible }
    """
    import requests as req

    tipo = request.query_params.get("tipo", "").upper()
    numero = request.query_params.get("numero", "").strip()

    if not tipo or not numero:
        return Response(
            {"error": "Se requieren los parámetros 'tipo' y 'numero'"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    prefijo = _PREFIJO_API.get(tipo)
    if not prefijo:
        return Response(
            {"error": f"Tipo '{tipo}' no soportado. Usa GPCO, TETR o CHA."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        num_int = int(numero)
    except ValueError:
        return Response(
            {"error": "El número de equipo debe ser entero."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    codigo_api = f"{prefijo}-{str(num_int).zfill(4)}"
    base_url = getattr(settings, "HOROMETROS_API_BASE_URL", "http://192.168.38.14:8009/vehiculos")
    timeout = getattr(settings, "HOROMETROS_API_TIMEOUT", 5)
    url = f"{base_url}/{codigo_api}/horometros"

    try:
        resp = req.get(url, timeout=timeout)

        if resp.status_code == 404:
            return Response(
                {
                    "error": f"Equipo {codigo_api} no encontrado en la API de horómetros.",
                    "disponible": False,
                    "codigo_externo": codigo_api,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        resp.raise_for_status()
        data = resp.json()

        return Response({
            "codigo_externo": codigo_api,
            "horometro": data.get("horometro"),
            "fecha": data.get("fecha"),
            "disponible": True,
        })

    except req.exceptions.ConnectionError:
        return Response(
            {"error": "API de horómetros no disponible. Verifica la conexión de red.", "disponible": False},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    except req.exceptions.Timeout:
        return Response(
            {"error": "Tiempo de espera agotado al consultar la API de horómetros.", "disponible": False},
            status=status.HTTP_504_GATEWAY_TIMEOUT,
        )
    except Exception as e:
        return Response(
            {"error": f"Error inesperado: {str(e)}", "disponible": False},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
