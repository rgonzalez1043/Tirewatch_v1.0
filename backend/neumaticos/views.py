from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from .models import Medicion, TasaDesgaste, Proyeccion, Neumatico
from .serializers import (
    MedicionSerializer, MedicionCreateSerializer,
    TasaDesgasteSerializer, ProyeccionSerializer, NeumaticSerializer,
)
from .services import MotorAnalisis
from .importador import importar_excel
from equipos.models import Equipo


class MedicionViewSet(viewsets.ModelViewSet):
    """
    CRUD de mediciones.

    GET /api/neumaticos/mediciones/              → lista
    GET /api/neumaticos/mediciones/?equipo=1     → filtrar por equipo
    GET /api/neumaticos/mediciones/?tipo=traccion → filtrar por tipo
    POST /api/neumaticos/mediciones/             → crear (terreno)
    """
    queryset = Medicion.objects.select_related("equipo", "registrado_por").all()
    filterset_fields = ["equipo", "tipo", "marca_nombre", "origen", "fecha"]
    search_fields = ["equipo__numero", "marca_nombre"]
    ordering_fields = ["fecha", "equipo", "created_at"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MedicionCreateSerializer
        return MedicionSerializer


class ImportarExcelView(APIView):
    """
    POST /api/neumaticos/importar/
    Importa datos desde un archivo Excel.
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivo = request.FILES.get("archivo")
        if not archivo:
            return Response(
                {"error": "No se envió ningún archivo"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not archivo.name.endswith((".xlsx", ".xls")):
            return Response(
                {"error": "El archivo debe ser .xlsx o .xls"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = importar_excel(archivo, usuario=request.user)

        if "error" in resultado:
            return Response(resultado, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "mensaje": f"Importación completada: {resultado['total']} mediciones",
            "detalle": resultado,
        })


class EjecutarAnalisisView(APIView):
    """
    POST /api/neumaticos/analisis/ejecutar/
    Ejecuta el análisis completo de desgaste.
    """
    def post(self, request):
        tipo = request.data.get("tipo", "traccion")
        if tipo not in ("traccion", "direccion"):
            return Response(
                {"error": "Tipo debe ser 'traccion' o 'direccion'"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motor = MotorAnalisis()
        resultado = motor.ejecutar_analisis(tipo=tipo)

        return Response({
            "mensaje": "Análisis ejecutado correctamente",
            "detalle": resultado,
        })


class TasaDesgasteViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/neumaticos/tasas/"""
    queryset = TasaDesgaste.objects.all()
    serializer_class = TasaDesgasteSerializer
    filterset_fields = ["marca_nombre", "tipo"]


class ProyeccionViewSet(viewsets.ReadOnlyModelViewSet):
    """GET /api/neumaticos/proyecciones/"""
    queryset = Proyeccion.objects.select_related("equipo").all()
    serializer_class = ProyeccionSerializer
    filterset_fields = ["equipo", "tipo"]
    ordering_fields = ["horas_restantes", "fecha_cambio_estimada"]


class GraficoEquipoView(APIView):
    """
    GET /api/neumaticos/grafico/<equipo_numero>/?tipo=traccion
    Retorna datos para gráfico de un equipo.
    """
    def get(self, request, equipo_numero):
        tipo = request.query_params.get("tipo", "traccion")

        try:
            equipo = Equipo.objects.get(numero=equipo_numero)
        except Equipo.DoesNotExist:
            return Response(
                {"error": f"Equipo {equipo_numero} no encontrado"},
                status=status.HTTP_404_NOT_FOUND,
            )

        motor = MotorAnalisis()
        resultado = motor.calcular_tasas(tipo=tipo)
        datos = motor.datos_grafico(
            equipo, tipo,
            resultado["tasas_marca"],
            resultado["tasa_global"],
        )

        return Response({
            "equipo": equipo_numero,
            "tipo": tipo,
            "series": datos,
        })


class DashboardView(APIView):
    """
    GET /api/neumaticos/dashboard/?tipo=traccion
    Resumen general para el dashboard.
    """
    def get(self, request):
        tipo = request.query_params.get("tipo", "traccion")

        total_equipos = Equipo.objects.count()
        total_mediciones = Medicion.objects.filter(tipo=tipo).count()
        proyecciones = Proyeccion.objects.filter(tipo=tipo).select_related("equipo")

        alertas = proyecciones.filter(horas_restantes__lt=500).order_by("horas_restantes")
        tasas = TasaDesgaste.objects.filter(tipo=tipo)

        return Response({
            "total_equipos": total_equipos,
            "total_mediciones": total_mediciones,
            "total_alertas": alertas.count(),
            "marcas_analizadas": tasas.values("marca_nombre").distinct().count(),
            "alertas": ProyeccionSerializer(alertas, many=True).data,
            "proyecciones": ProyeccionSerializer(proyecciones, many=True).data,
            "tasas": TasaDesgasteSerializer(tasas, many=True).data,
        })
