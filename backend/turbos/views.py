from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import MedicionTurbo, ProyeccionTurbo
from .serializers import (
    MedicionTurboSerializer, MedicionTurboCreateSerializer, ProyeccionTurboSerializer
)

class MedicionTurboViewSet(viewsets.ModelViewSet):
    """
    CRUD completo para Mediciones de Turbos.
    """
    queryset = MedicionTurbo.objects.select_related("equipo", "registrado_por").all()
    filterset_fields = ["equipo", "estado_visual"]
    ordering_fields = ["-fecha", "-horometro_motor"]
    
    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MedicionTurboCreateSerializer
        return MedicionTurboSerializer


class ProyeccionTurboViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Lectura de proyecciones analíticas para dashboards y gráficos.
    """
    queryset = ProyeccionTurbo.objects.select_related("equipo").all()
    serializer_class = ProyeccionTurboSerializer
    filterset_fields = ["equipo", "estado"]
    ordering_fields = ["horas_motor_restantes", "estado"]

    @action(detail=False, methods=["get"], url_path=r"grafico/(?P<equipo_numero>\d+)")
    def grafico(self, request, equipo_numero=None):
        """
        Retorna la serie de tiempo (fecha, valores radial/axial) para un equipo.
        /api/turbos/proyecciones/grafico/101/
        """
        mediciones = MedicionTurbo.objects.filter(
            equipo__numero=equipo_numero
        ).order_by("fecha")

        series = []
        for m in mediciones:
            series.append({
                "fecha": m.fecha,
                "horometro": m.horometro_motor,
                "valores": {
                    "Radial": m.juego_radial,
                    "Axial": m.juego_axial
                }
            })

        return Response({
            "equipo": equipo_numero,
            "series": series
        })
