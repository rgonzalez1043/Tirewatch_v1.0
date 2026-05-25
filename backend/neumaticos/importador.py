"""
Importador de Excel para TireWatch
===================================
Parsea el formato de la planilla "NEUMATICOS PORTACONTENEDORES"
con la hoja "datosp".
"""
import pandas as pd
from datetime import datetime
from django.db import transaction

from neumaticos.models import Medicion
from equipos.models import Equipo, TipoEquipo, MarcaComponente


def normalizar_marca(raw):
    """Normaliza nombre de marca"""
    s = str(raw).strip().upper()
    if "GOOD" in s:
        return "GOODYEAR"
    elif "CONT" in s:
        return "CONTINENTAL"
    elif "BKT" in s:
        return "BKT"
    return s if s and s != "NAN" else "GENERICO"


def detectar_fecha(fila):
    """Intenta detectar una fecha en cualquier celda de la fila"""
    for celda in fila:
        if pd.isna(celda):
            continue

        # Si ya es datetime
        if isinstance(celda, datetime):
            return celda

        s = str(celda)
        tiene_digito = any(c.isdigit() for c in s)
        tiene_sep = "-" in s or "/" in s

        if tiene_digito and tiene_sep:
            try:
                f = pd.to_datetime(celda, dayfirst=True, errors="coerce")
                if pd.notnull(f) and 2000 < f.year < 2050:
                    return f.to_pydatetime()
            except Exception:
                pass
    return None


@transaction.atomic
def importar_excel(archivo, usuario=None):
    """
    Importa datos desde Excel.

    Args:
        archivo: File-like object (UploadedFile de Django)
        usuario: Usuario que realiza la importación

    Returns:
        dict con estadísticas de importación
    """
    try:
        df = pd.read_excel(archivo, sheet_name="datosp", header=None)
    except Exception as e:
        # Intentar con la primera hoja
        try:
            df = pd.read_excel(archivo, sheet_name=0, header=None)
        except Exception:
            return {"error": f"No se pudo leer el archivo: {str(e)}"}

    # Asegurar tipo de equipo existe
    tipo_equipo, _ = TipoEquipo.objects.get_or_create(
        codigo="PC",
        defaults={"nombre": "Portacontenedor"}
    )

    fecha_vigente = None
    stats = {
        "mediciones_traccion": 0,
        "mediciones_direccion": 0,
        "equipos_nuevos": 0,
        "marcas_nuevas": 0,
        "errores": [],
    }

    for idx, fila in df.iterrows():
        # Detectar fecha
        fecha_detectada = detectar_fecha(fila.values)
        if fecha_detectada:
            fecha_vigente = fecha_detectada

        if not fecha_vigente:
            continue

        # ID del equipo
        try:
            id_equipo = pd.to_numeric(fila.iloc[0], errors="coerce")
            if pd.isna(id_equipo) or id_equipo <= 0:
                continue
            id_equipo = int(id_equipo)
        except Exception:
            continue

        # === TRACCIONALES ===
        try:
            marca_trac = normalizar_marca(fila.iloc[1] if len(fila) > 1 else "GENERICO")
            valores_h = {}

            for h in range(8):
                col = 2 + h
                if col < len(fila):
                    v = pd.to_numeric(fila.iloc[col], errors="coerce")
                    if pd.notnull(v) and v > 0:
                        valores_h[f"h{h+1}"] = float(v)

            if valores_h:
                equipo, created = Equipo.objects.get_or_create(
                    numero=id_equipo,
                    defaults={
                        "tipo": tipo_equipo,
                        "nombre": f"Portacontenedor {id_equipo}",
                    }
                )
                if created:
                    stats["equipos_nuevos"] += 1

                # Asegurar marca existe
                marca_obj, mc = MarcaComponente.objects.get_or_create(
                    nombre=marca_trac, tipo="neumatico",
                    defaults={"profundidad_fabrica_mm": {
                        "GOODYEAR": 90, "CONTINENTAL": 75, "BKT": 70
                    }.get(marca_trac)}
                )
                if mc:
                    stats["marcas_nuevas"] += 1

                # Evitar duplicados
                existe = Medicion.objects.filter(
                    equipo=equipo,
                    fecha=fecha_vigente.date(),
                    tipo="traccion",
                ).exists()

                if not existe:
                    Medicion.objects.create(
                        equipo=equipo,
                        fecha=fecha_vigente.date(),
                        tipo="traccion",
                        marca_nombre=marca_trac,
                        origen="excel",
                        registrado_por=usuario,
                        **valores_h,
                    )
                    stats["mediciones_traccion"] += 1

        except Exception as e:
            stats["errores"].append(f"Fila {idx} (tracción): {str(e)}")

        # === DIRECCIONALES ===
        try:
            if len(fila) > 13:
                marca_dir = normalizar_marca(fila.iloc[10] if len(fila) > 10 else "GENERICO")
                valores_d = {}

                d1 = pd.to_numeric(fila.iloc[11], errors="coerce") if len(fila) > 11 else float('nan')
                d2 = pd.to_numeric(fila.iloc[13], errors="coerce") if len(fila) > 13 else float('nan')

                if pd.notnull(d1) and d1 > 0:
                    valores_d["d1"] = float(d1)
                if pd.notnull(d2) and d2 > 0:
                    valores_d["d2"] = float(d2)

                if valores_d:
                    equipo, created = Equipo.objects.get_or_create(
                        numero=id_equipo,
                        defaults={
                            "tipo": tipo_equipo,
                            "nombre": f"Portacontenedor {id_equipo}",
                        }
                    )
                    if created:
                        stats["equipos_nuevos"] += 1

                    existe = Medicion.objects.filter(
                        equipo=equipo,
                        fecha=fecha_vigente.date(),
                        tipo="direccion",
                    ).exists()

                    if not existe:
                        Medicion.objects.create(
                            equipo=equipo,
                            fecha=fecha_vigente.date(),
                            tipo="direccion",
                            marca_nombre=marca_dir,
                            origen="excel",
                            registrado_por=usuario,
                            **valores_d,
                        )
                        stats["mediciones_direccion"] += 1

        except Exception as e:
            stats["errores"].append(f"Fila {idx} (dirección): {str(e)}")

    stats["total"] = stats["mediciones_traccion"] + stats["mediciones_direccion"]
    return stats
