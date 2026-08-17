from django.db import transaction
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from equipos.models import Equipo
from .models import (
    Opacimetro, MedicionOpacidad, AceleracionOpacidad,
    ProyeccionOpacidad, ImportacionOpacidad,
)
from .serializers import (
    OpacimetroSerializer, MedicionOpacidadSerializer, MedicionOpacidadCreateSerializer,
    ProyeccionOpacidadSerializer, ImportacionOpacidadSerializer,
    ConfirmarImportacionSerializer,
)
from .services.analizador import AnalizadorOpacidad
from .services import parser_texa


class OpacimetroViewSet(viewsets.ModelViewSet):
    queryset = Opacimetro.objects.all()
    serializer_class = OpacimetroSerializer
    filterset_fields = ["activo", "fabricante"]


class MedicionOpacidadViewSet(viewsets.ModelViewSet):
    """CRUD de mediciones. El borrado fisico esta deshabilitado: se anula."""
    queryset = (
        MedicionOpacidad.objects
        .select_related("equipo", "equipo__tipo", "opacimetro", "registrado_por")
        .prefetch_related("aceleraciones")
    )
    filterset_fields = [
        "equipo", "equipo__numero", "equipo__tipo__codigo",
        "periodo", "aprobado", "origen", "anulado", "calibracion_vigente",
    ]
    search_fields = ["operador", "observaciones"]
    ordering_fields = ["fecha", "k_medio", "equipo__numero"]

    def get_serializer_class(self):
        if self.action in ("create", "update", "partial_update"):
            return MedicionOpacidadCreateSerializer
        return MedicionOpacidadSerializer

    def perform_create(self, serializer):
        medicion = serializer.save()
        AnalizadorOpacidad.analizar_equipo(medicion.equipo)

    def perform_update(self, serializer):
        medicion = serializer.save()
        AnalizadorOpacidad.analizar_equipo(medicion.equipo)

    def destroy(self, request, *args, **kwargs):
        return Response(
            {"detail": "Las mediciones no se eliminan. Use la accion /anular/ indicando motivo."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"])
    def anular(self, request, pk=None):
        medicion = self.get_object()
        motivo = (request.data.get("motivo") or "").strip()
        if not motivo:
            return Response(
                {"motivo": "Obligatorio para anular una medicion."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        medicion.anular(request.user, motivo)
        AnalizadorOpacidad.analizar_equipo(medicion.equipo)
        return Response(MedicionOpacidadSerializer(medicion, context={"request": request}).data)

    @action(detail=False, methods=["get"], url_path=r"grafico/(?P<equipo_id>\d+)")
    def grafico(self, request, equipo_id=None):
        """Serie de tiempo de k para un equipo, lista para graficar."""
        mediciones = (
            MedicionOpacidad.objects
            .filter(equipo_id=equipo_id, anulado=False)
            .order_by("fecha")
        )
        proy = ProyeccionOpacidad.objects.filter(equipo_id=equipo_id).first()
        return Response({
            "equipo": equipo_id,
            "limite": mediciones.last().k_limite if mediciones.exists() else None,
            "series": [
                {
                    "fecha": m.fecha,
                    "periodo": m.periodo,
                    "horometro": m.horometro_motor,
                    "k": m.k_medio,
                    "aprobado": m.aprobado,
                    "calibracion_vigente": m.calibracion_vigente,
                }
                for m in mediciones
            ],
            "proyeccion": ProyeccionOpacidadSerializer(proy).data if proy else None,
        })


class ProyeccionOpacidadViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ProyeccionOpacidad.objects.select_related("equipo", "equipo__tipo")
    serializer_class = ProyeccionOpacidadSerializer
    filterset_fields = ["equipo", "estado", "equipo__tipo__codigo", "control_vencido"]
    ordering_fields = ["pct_limite", "tasa_k_anual", "semestres_a_limite"]

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        """Tarjetas del dashboard."""
        qs = self.filter_queryset(self.get_queryset())
        agg = qs.aggregate(
            ok=Count("id", filter=Q(estado="OK")),
            atencion=Count("id", filter=Q(estado="ATENCION")),
            critico=Count("id", filter=Q(estado="CRITICO")),
            vencidos=Count("id", filter=Q(control_vencido=True)),
        )
        agg["total"] = qs.count()
        agg["en_ascenso"] = qs.filter(tasa_k_anual__gt=0.15).count()
        return Response(agg)


class ImportarPDFView(APIView):
    """
    PASO 1 de la importacion. Sube el PDF, lo parsea y deja el resultado
    en revision. NO crea la medicion: eso lo hace el paso 2 tras validacion
    humana. Este PDF trae campos digitados a mano y mapeos corridos, asi que
    la confirmacion humana no es opcional.

    Acepta UNO O VARIOS PDF en el campo 'archivo' (repetido N veces).
    POST /api/opacidad/importar/   (multipart)
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        archivos = request.FILES.getlist("archivo") or request.FILES.getlist("archivos")
        if not archivos:
            return Response(
                {"archivo": "Requerido (uno o varios PDF)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultados = [self._procesar_uno(a, request) for a in archivos]
        ok = sum(1 for r in resultados if r.get("ok"))
        return Response(
            {
                "total": len(resultados),
                "ok": ok,
                "con_error": len(resultados) - ok,
                "resultados": resultados,
            },
            status=status.HTTP_201_CREATED,
        )

    def _procesar_uno(self, archivo, request):
        """Procesa un archivo. NUNCA lanza excepcion: siempre devuelve un dict."""
        nombre = getattr(archivo, "name", "archivo.pdf")
        try:
            sha = parser_texa.sha256_archivo(archivo)

            duplicado = MedicionOpacidad.objects.filter(sha256=sha, anulado=False).first()
            if duplicado:
                return {
                    "archivo": nombre, "ok": False, "estado": "DUPLICADO",
                    "detail": "Este PDF ya fue cargado.",
                    "medicion_id": duplicado.id,
                    "equipo": duplicado.equipo.codigo_completo,
                    "fecha": str(duplicado.fecha),
                }

            try:
                datos, advertencias = parser_texa.extraer(archivo)
            except Exception as exc:
                return {
                    "archivo": nombre, "ok": False, "estado": "ERROR_LECTURA",
                    "detail": f"No se pudo leer el PDF: {exc}",
                }

            equipo = self._resolver_equipo(datos.get("matricula"), datos.get("vin"), advertencias)

            datos_json = {k: v for k, v in datos.items() if k != "texto_crudo"}
            datos_json["fecha"] = str(datos_json.get("fecha") or "")
            opac = datos_json.get("opacimetro") or {}
            if opac.get("vencimiento_control"):
                opac["vencimiento_control"] = str(opac["vencimiento_control"])
                datos_json["opacimetro"] = opac

            imp = ImportacionOpacidad.objects.create(
                archivo=archivo,
                sha256=sha,
                nombre_original=nombre,
                datos_extraidos=datos_json,
                advertencias=advertencias,
                equipo_sugerido=equipo,
                matricula_detectada=datos.get("matricula") or "",
                subido_por=request.user if request.user.is_authenticated else None,
            )
            return {
                "archivo": nombre, "ok": True, "estado": "PENDIENTE",
                "importacion": ImportacionOpacidadSerializer(imp).data,
            }
        except Exception as exc:
            return {
                "archivo": nombre, "ok": False, "estado": "ERROR",
                "detail": f"Error procesando el archivo: {exc}",
            }

    @staticmethod
    def _resolver_equipo(matricula, vin, advertencias):
        """
        La matricula del informe (ej. 2178) mapea a Equipo.numero, pero el
        numero solo es unico DENTRO del tipo. El VIN trae el tipo de forma
        no estandarizada ('TRACTO'), asi que se usa como pista, no como verdad.
        """
        if not matricula or not str(matricula).isdigit():
            advertencias.append("No se pudo asociar automaticamente a un equipo")
            return None

        candidatos = list(Equipo.objects.filter(numero=int(matricula)))
        if not candidatos:
            advertencias.append(f"No existe ningun equipo con numero {matricula}")
            return None
        if len(candidatos) == 1:
            return candidatos[0]

        pista = (vin or "").strip().upper()
        match = [e for e in candidatos if pista and pista in e.tipo.codigo.upper()]
        if len(match) == 1:
            return match[0]

        advertencias.append(
            f"El numero {matricula} existe en varios tipos de equipo "
            f"({', '.join(e.codigo_completo for e in candidatos)}). Seleccione manualmente."
        )
        return None


class ImportacionOpacidadViewSet(viewsets.ReadOnlyModelViewSet):
    """Cola de revision de importaciones."""
    queryset = ImportacionOpacidad.objects.select_related("equipo_sugerido", "medicion")
    serializer_class = ImportacionOpacidadSerializer
    filterset_fields = ["estado"]

    @action(detail=True, methods=["post"])
    def confirmar(self, request, pk=None):
        """
        PASO 2. Crea la medicion definitiva con los datos ya validados
        (y eventualmente corregidos) por la persona.
        """
        imp = self.get_object()
        if imp.estado != ImportacionOpacidad.Estado.PENDIENTE:
            return Response(
                {"detail": f"La importacion ya esta {imp.get_estado_display()}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        ser = ConfirmarImportacionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        v = ser.validated_data
        d = imp.datos_extraidos

        with transaction.atomic():
            opacimetro = self._get_opacimetro(d.get("opacimetro"))

            medicion = MedicionOpacidad(
                equipo=v["equipo"],
                fecha=v["fecha"],
                hora=d.get("hora") or None,
                horometro_motor=v.get("horometro_motor"),
                k_medio=v["k_medio"],
                k_limite=v["k_limite"],
                temp_aceite=v.get("temp_aceite"),
                rpm_ralenti=v.get("rpm_ralenti"),
                rpm_maximo=v.get("rpm_maximo"),
                opacimetro=opacimetro,
                origen=MedicionOpacidad.Origen.PDF,
                campos_manuales=d.get("campos_manuales", []),
                advertencias=imp.advertencias,
                operador=v.get("operador", "") or d.get("operador", ""),
                observaciones=v.get("observaciones", ""),
                sha256=imp.sha256,
                texto_crudo=d.get("texto_crudo", ""),
                registrado_por=request.user if request.user.is_authenticated else None,
            )
            medicion.archivo.save(imp.nombre_original, imp.archivo.file, save=False)
            medicion.save()

            for a in d.get("aceleraciones", []):
                AceleracionOpacidad.objects.create(
                    medicion=medicion,
                    numero=a["numero"],
                    k=a["k"],
                    rpm_ralenti=a.get("rpm_ralenti"),
                    rpm_maximo=a.get("rpm_maximo"),
                    tiempo_s=a.get("tiempo_s"),
                )

            imp.estado = ImportacionOpacidad.Estado.CONFIRMADA
            imp.medicion = medicion
            imp.save(update_fields=["estado", "medicion"])

        AnalizadorOpacidad.analizar_equipo(medicion.equipo)
        return Response(
            MedicionOpacidadSerializer(medicion, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def rechazar(self, request, pk=None):
        imp = self.get_object()
        imp.estado = ImportacionOpacidad.Estado.RECHAZADA
        imp.motivo_rechazo = request.data.get("motivo", "")
        imp.save(update_fields=["estado", "motivo_rechazo"])
        return Response(ImportacionOpacidadSerializer(imp).data)

    @staticmethod
    def _get_opacimetro(data):
        if not data or not data.get("numero_serie"):
            return None
        obj, _ = Opacimetro.objects.get_or_create(
            numero_serie=data["numero_serie"],
            defaults={
                "fabricante": data.get("fabricante", ""),
                "modelo": data.get("modelo", ""),
                "numero_homologacion": data.get("numero_homologacion", ""),
                "vencimiento_control": data.get("vencimiento_control"),
            },
        )
        return obj


class EjecutarAnalisisOpacidadView(APIView):
    """POST /api/opacidad/analizar/ — recalcula todas las proyecciones."""

    def post(self, request):
        n = AnalizadorOpacidad.analizar_todos()
        return Response(
            {"mensaje": "Analisis de opacidad completado", "proyecciones_actualizadas": n},
            status=status.HTTP_200_OK,
        )


class CoberturaCampanaView(APIView):
    """
    GET /api/opacidad/cobertura/?periodo=2026-S1
    Reporte de cobertura de la campana semestral. Es lo que pide una auditoria:
    no el certificado de un equipo, sino que porcentaje de la flota esta al dia.
    """

    def get(self, request):
        periodo = request.query_params.get("periodo")
        if not periodo:
            return Response(
                {"periodo": "Requerido. Formato: 2026-S1"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(AnalizadorOpacidad.cobertura_campana(periodo))
