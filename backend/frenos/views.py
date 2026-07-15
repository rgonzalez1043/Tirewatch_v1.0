from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404

from core.models import ConfiguracionSistema
from .models import ComponenteFreno, MedicionFreno, ProyeccionFreno
from .serializers import (
    ComponenteFrenoSerializer, MedicionFrenoSerializer,
    ProyeccionFrenoSerializer, ReemplazoFrenoSerializer,
)
from .services import analizar_componente, analizar_todos_los_frenos, registrar_reemplazo


class ComponenteFrenoViewSet(viewsets.ModelViewSet):
    """
    CRUD de componentes de freno.
    GET /api/frenos/componentes/?equipo=<id>&activo=true
    GET /api/frenos/componentes/<id>/mediciones/
    POST /api/frenos/componentes/<id>/reemplazar/
    """
    queryset = (
        ComponenteFreno.objects
        .select_related("equipo", "registrado_por")
        .prefetch_related("proyeccion")
        .order_by("equipo__numero", "posicion", "-activo")
    )
    serializer_class = ComponenteFrenoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["equipo", "activo", "posicion", "tipo_freno"]
    search_fields = ["equipo__numero"]
    ordering_fields = ["equipo__numero", "posicion", "activo"]

    def perform_create(self, serializer):
        comp = serializer.save(registrado_por=self.request.user)
        analizar_componente(comp)

    @action(detail=True, methods=["get"], url_path="mediciones")
    def mediciones(self, request, pk=None):
        """Historial completo de mediciones de este componente."""
        componente = self.get_object()
        mediciones = MedicionFreno.objects.filter(componente=componente).order_by("fecha")
        data = MedicionFrenoSerializer(mediciones, many=True).data
        return Response(data)

    @action(detail=True, methods=["post"], url_path="reemplazar")
    def reemplazar(self, request, pk=None):
        """
        Registra el reemplazo de un freno:
        - Marca el actual como retirado
        - Crea un nuevo componente en la misma posición
        - Retorna el nuevo ComponenteFreno
        Solo administradores.
        """
        if not request.user.is_staff:
            return Response(
                {"detail": "Solo administradores pueden registrar reemplazos."},
                status=status.HTTP_403_FORBIDDEN,
            )
        componente = self.get_object()
        serializer = ReemplazoFrenoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        nuevo = registrar_reemplazo(
            componente=componente,
            fecha_retiro=d["fecha_retiro"],
            motivo_retiro=d["motivo_retiro"],
            nuevo_espesor_fabrica_mm=d["nuevo_espesor_fabrica_mm"],
            fecha_instalacion=d["fecha_instalacion"],
            horometro_instalacion=d.get("horometro_instalacion"),
            notas=d.get("notas", ""),
            registrado_por=request.user,
        )
        return Response(ComponenteFrenoSerializer(nuevo).data, status=status.HTTP_201_CREATED)


class MedicionFrenoViewSet(viewsets.ModelViewSet):
    """
    CRUD de mediciones de freno.
    Al crear, recalcula automáticamente la proyección del componente.
    POST body: { componente: <id>, equipo: <id>, fecha, horometro, espesor_mm, observaciones }
    """
    queryset = (
        MedicionFreno.objects
        .select_related("componente", "equipo", "registrado_por")
        .order_by("-fecha")
    )
    serializer_class = MedicionFrenoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["componente", "equipo"]
    search_fields = ["equipo__numero"]
    ordering_fields = ["fecha", "equipo"]

    def perform_create(self, serializer):
        medicion = serializer.save(registrado_por=self.request.user)
        analizar_componente(medicion.componente)

    def perform_update(self, serializer):
        medicion = serializer.save()
        analizar_componente(medicion.componente)

    def perform_destroy(self, instance):
        componente = instance.componente
        instance.delete()
        analizar_componente(componente)


class ProyeccionFrenoViewSet(viewsets.ReadOnlyModelViewSet):
    """Proyecciones calculadas por el motor analítico."""
    queryset = (
        ProyeccionFreno.objects
        .select_related("componente", "equipo", "equipo__tipo")
        .order_by("estado", "horas_restantes")
    )
    serializer_class = ProyeccionFrenoSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["estado", "equipo"]
    ordering_fields = ["horas_restantes", "estado", "equipo__numero"]

    @action(detail=False, methods=["post"], url_path="recalcular")
    def recalcular(self, request):
        """Dispara el motor analítico para todos los componentes activos."""
        resultados = analizar_todos_los_frenos()
        return Response({"recalculados": len(resultados), "ok": True})

    @action(detail=False, methods=["get"], url_path="por-equipo")
    def por_equipo(self, request):
        """
        Retorna proyecciones agrupadas por equipo.
        Estructura: [ { equipo_numero, estado_global, componentes: [...] } ]
        """
        config = ConfiguracionSistema.load()
        proyecciones = self.get_queryset()

        equipos_dict = {}
        for p in proyecciones:
            eq_key = p.equipo.id  # PK único — evita colisión entre tipos con mismo número
            if eq_key not in equipos_dict:
                equipos_dict[eq_key] = {
                    "equipo_id": p.equipo.id,
                    "equipo_numero": p.equipo.numero,
                    "equipo_tipo_codigo": p.equipo.tipo.codigo,
                    "equipo_codigo_completo": p.equipo.codigo_completo,
                    "estado_global": "OK",
                    "componentes": [],
                }
            equipos_dict[eq_key]["componentes"].append(ProyeccionFrenoSerializer(p).data)

            # Estado global = el peor de todos los componentes
            PRIORIDAD = {"CRITICO": 2, "ATENCION": 1, "OK": 0}
            actual = equipos_dict[eq_key]["estado_global"]
            if PRIORIDAD.get(p.estado, 0) > PRIORIDAD.get(actual, 0):
                equipos_dict[eq_key]["estado_global"] = p.estado

        return Response({
            "equipos": list(equipos_dict.values()),
            "config": {
                "limite_freno_tambor_mm": config.limite_freno_tambor_mm,
                "limite_freno_disco_mm": config.limite_freno_disco_mm,
                "limite_freno_tambor_aire_mm": config.limite_freno_tambor_aire_mm,
                "umbral_alerta_pct": config.umbral_alerta_freno_pct,
            }
        })
