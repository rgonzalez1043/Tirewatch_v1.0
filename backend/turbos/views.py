from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import MedicionTurbo, ProyeccionTurbo
from .serializers import (
    MedicionTurboSerializer, MedicionTurboCreateSerializer, ProyeccionTurboSerializer
)
from .services import AnalizadorTurbos


class MedicionTurboViewSet(viewsets.ModelViewSet):
    """CRUD completo para Mediciones de Turbos."""
    queryset = MedicionTurbo.objects.select_related("equipo", "registrado_por").all()
    filterset_fields = ["equipo", "equipo__numero", "estado_visual"]
    ordering_fields = ["-fecha", "-horometro_motor"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MedicionTurboCreateSerializer
        return MedicionTurboSerializer


class ProyeccionTurboViewSet(viewsets.ReadOnlyModelViewSet):
    """Lectura de proyecciones analíticas para dashboards y gráficos."""
    queryset = ProyeccionTurbo.objects.select_related("equipo").all()
    serializer_class = ProyeccionTurboSerializer
    filterset_fields = ["equipo", "estado"]
    ordering_fields = ["horas_motor_restantes", "estado"]

    @action(detail=False, methods=["get"], url_path=r"grafico/(?P<equipo_numero>\d+)")
    def grafico(self, request, equipo_numero=None):
        """
        GET /api/turbos/proyecciones/grafico/<equipo_numero>/
        Retorna la serie de tiempo para gráfico de un equipo.
        """
        mediciones = MedicionTurbo.objects.filter(
            equipo__numero=equipo_numero
        ).order_by("horometro_motor")

        series = [
            {
                "fecha": m.fecha,
                "horometro": m.horometro_motor,
                "valores": {"Radial": m.juego_radial, "Axial": m.juego_axial},
            }
            for m in mediciones
        ]
        return Response({"equipo": equipo_numero, "series": series})


class EjecutarAnalisisTurbosView(APIView):
    """
    POST /api/turbos/analizar/
    Recalcula las proyecciones de todos los equipos usando el historial completo.
    """
    def post(self, request):
        AnalizadorTurbos.analizar_todos()
        total = ProyeccionTurbo.objects.count()
        return Response(
            {"mensaje": "Análisis de turbos completado", "proyecciones_actualizadas": total},
            status=status.HTTP_200_OK,
        )
