from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q

from core.models import ConfiguracionSistema
from .models import MedicionCadena, ProyeccionCadena
from .serializers import MedicionCadenaSerializer, ProyeccionCadenaSerializer
from .services import analizar_cadenas_equipo, analizar_todas_las_cadenas


class MedicionCadenaViewSet(viewsets.ModelViewSet):
    """CRUD de mediciones de cadena. Al crear, recalcula proyección."""
    queryset = MedicionCadena.objects.select_related("equipo", "registrado_por").order_by("-fecha")
    serializer_class = MedicionCadenaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["equipo", "tipo_cadena"]
    search_fields = ["equipo__numero"]
    ordering_fields = ["fecha", "equipo"]

    def perform_create(self, serializer):
        medicion = serializer.save(registrado_por=self.request.user)
        analizar_cadenas_equipo(medicion.equipo)

    def perform_update(self, serializer):
        medicion = serializer.save()
        analizar_cadenas_equipo(medicion.equipo)

    def perform_destroy(self, instance):
        equipo = instance.equipo
        instance.delete()
        analizar_cadenas_equipo(equipo)


class ProyeccionCadenaViewSet(viewsets.ReadOnlyModelViewSet):
    """Proyecciones de cadenas calculadas por el motor analítico."""
    queryset = ProyeccionCadena.objects.select_related("equipo", "equipo__tipo").order_by("horas_restantes")
    serializer_class = ProyeccionCadenaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["estado"]
    ordering_fields = ["horas_restantes", "estado", "elongacion_actual_pct"]

    @action(detail=False, methods=["post"], url_path="recalcular")
    def recalcular(self, request):
        """Dispara el motor analítico para todos los equipos con datos de cadenas."""
        resultados = analizar_todas_las_cadenas()
        return Response({"recalculados": len(resultados), "ok": True})

    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """Datos resumidos para el dashboard de cadenas."""
        config = ConfiguracionSistema.load()
        proyecciones = self.get_queryset()
        stats = proyecciones.aggregate(
            total=Count("id"),
            criticos=Count("id", filter=Q(estado="CRITICO")),
            atencion=Count("id", filter=Q(estado="ATENCION")),
            ok=Count("id", filter=Q(estado="OK")),
        )
        data = {
            "stats": stats,
            "config": {
                "limite_elongacion_pct": config.limite_elongacion_cadena_pct,
                "umbral_alerta_pct": config.umbral_alerta_cadena_pct,
            },
            "proyecciones": ProyeccionCadenaSerializer(proyecciones, many=True).data,
        }
        return Response(data)
