import logging
from django.db import transaction
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.views import APIView

from equipos.models import Equipo, TipoEquipo

logger = logging.getLogger(__name__)
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

            tipo_pista = datos.get("tipo_pista", "")
            equipo = self._resolver_equipo(datos.get("matricula"), datos.get("vin"), advertencias, tipo_pista=tipo_pista)

            datos_json = {k: v for k, v in datos.items() if k != "texto_crudo"}
            datos_json["fecha"] = str(datos_json.get("fecha") or "")
            opac = datos_json.get("opacimetro") or {}
            if opac.get("vencimiento_control"):
                opac["vencimiento_control"] = str(opac["vencimiento_control"])
                datos_json["opacimetro"] = opac

            # Consulta automática de horómetro si equipo/tipo y fecha están disponibles
            fecha_test = datos_json.get("fecha")
            if fecha_test:
                from equipos.services import consultar_horometro_externo
                tipo_cod = equipo.tipo.codigo if equipo else (tipo_pista or "GPCO")
                num_equipo = equipo.numero if equipo else datos.get("matricula")
                if tipo_cod and num_equipo:
                    try:
                        res_h = consultar_horometro_externo(tipo_cod, num_equipo, fecha=fecha_test)
                        if res_h.get("disponible") and res_h.get("horometro") is not None:
                            datos_json["horometro_motor"] = int(res_h["horometro"])
                            datos_json["horometro_origen"] = "API"
                    except Exception as e:
                        logger.warning("Error consultando horometro en importacion: %s", e)

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
    def _resolver_equipo(matricula, vin, advertencias, tipo_pista=""):
        """
        La matricula del informe (ej. 2178, 178, 70) mapea a Equipo.numero.
        Maneja heurísticas para desambiguar entre tipos y equivalencias de número (ej. 2178 <-> 178 para tractos).
        """
        if not matricula or not str(matricula).isdigit():
            advertencias.append("No se pudo asociar automaticamente a un equipo")
            return None

        num = int(matricula)
        candidatos = list(Equipo.objects.filter(numero=num).select_related("tipo"))

        # Si no se encuentra y num > 1000 (ej. 2178), buscar también por num % 1000 (ej. 178)
        if not candidatos and num > 1000:
            candidatos = list(Equipo.objects.filter(numero=num % 1000).select_related("tipo"))

        # Si no se encuentra y num < 1000 (ej. 178), buscar también por num + 2000 (ej. 2178)
        if not candidatos:
            candidatos = list(Equipo.objects.filter(numero=num + 2000).select_related("tipo"))

        if not candidatos:
            advertencias.append(f"No existe ningún equipo registrado con número {matricula}")
            return None

        if len(candidatos) == 1:
            return candidatos[0]

        pista = (tipo_pista or vin or "").strip().upper()
        # Heurística de matching por código de tipo o nombre de tipo
        tipo_map = {
            "TRACTO": "TETR", "TRA": "TETR", "TETR": "TETR",
            "PORTA": "GPCO", "POR": "GPCO", "GPCO": "GPCO",
            "CHASIS": "CHA", "CHA": "CHA",
        }
        codigo_esperado = tipo_map.get(pista)
        if codigo_esperado:
            match = [e for e in candidatos if e.tipo.codigo.upper() == codigo_esperado]
            if len(match) == 1:
                return match[0]

        match = [
            e for e in candidatos
            if pista and (pista in e.tipo.codigo.upper() or pista in e.tipo.nombre.upper())
        ]
        if len(match) == 1:
            return match[0]

        advertencias.append(
            f"El número {matricula} existe en varios tipos de equipo "
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
            equipo = v.get("equipo")
            if not equipo:
                tipo_id = v.get("tipo_id")
                numero = v.get("numero")
                if not tipo_id or not numero:
                    return Response(
                        {"detail": "Debe especificar un equipo o indicar tipo y número."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    tipo_obj = TipoEquipo.objects.get(id=tipo_id)
                except TipoEquipo.DoesNotExist:
                    return Response({"detail": "Tipo de equipo no válido."}, status=status.HTTP_400_BAD_REQUEST)

                equipo, _ = Equipo.objects.get_or_create(
                    tipo=tipo_obj,
                    numero=numero,
                    defaults={"nombre": f"{tipo_obj.nombre} {numero}"},
                )

            medicion_existente = MedicionOpacidad.objects.filter(equipo=equipo, fecha=v["fecha"], anulado=False).first()
            if medicion_existente:
                return Response(
                    {"detail": f"Ya existe una medición activa para el equipo {equipo.codigo_completo} en la fecha {v['fecha']}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            opacimetro = self._get_opacimetro(d.get("opacimetro"))

            medicion = MedicionOpacidad(
                equipo=equipo,
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
            if imp.archivo:
                try:
                    imp.archivo.open("rb")
                    medicion.archivo.save(imp.nombre_original or "informe.pdf", imp.archivo, save=False)
                except Exception as e:
                    logger.warning("No se pudo copiar archivo adjunto: %s", e)
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
        venc = data.get("vencimiento_control")
        if isinstance(venc, str):
            from datetime import date
            try:
                venc = date.fromisoformat(venc)
            except ValueError:
                venc = None

        defaults = {
            "fabricante": data.get("fabricante") or "TEXA SPA",
            "modelo": data.get("modelo") or "OPABOX Autopower",
            "numero_homologacion": data.get("numero_homologacion") or "",
        }
        if venc:
            defaults["vencimiento_control"] = venc

        obj, created = Opacimetro.objects.get_or_create(
            numero_serie=data["numero_serie"],
            defaults=defaults,
        )
        if not created and venc and obj.vencimiento_control != venc:
            obj.vencimiento_control = venc
            obj.save(update_fields=["vencimiento_control"])
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
