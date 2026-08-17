"""
Parser de informes de opacidad TEXA OPABOX Autopower.

Regla de diseno: este modulo NO escribe en base de datos y NO decide nada.
Solo extrae y levanta advertencias. La validacion la hace una persona.

Uso:
    datos, advertencias = extraer("TRA-2178.pdf")
"""
import hashlib
import re
from datetime import datetime

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None


# --- Patrones -------------------------------------------------------------

RE_FECHA_TEST = re.compile(r"Fecha del Test\s+(\d{2}/\d{2}/\d{4})", re.I)
RE_HORA_TEST = re.compile(r"Hora del test\s+(\d{1,2}:\d{2})", re.I)
RE_MATRICULA = re.compile(r"Matricula\s+([^\r\n]+)", re.I)
RE_VIN = re.compile(r"VIN\s+([^\n]+)", re.I)
RE_FABRICANTE = re.compile(r"Fabricante\s+([^\n]+)", re.I)
RE_MODELO = re.compile(r"Modelo\s+([^\n]+)", re.I)
RE_K_LIMITE = re.compile(r"k\s*\(1/m\)\s+([\d,\.]+)", re.I)
RE_TOL_BAJA = re.compile(r"Opa range\s*<\s*2[,\.]5\s*\(k\)\s+([\d,\.]+)", re.I)
RE_TOL_ALTA = re.compile(r"Opa range\s*>=\s*2[,\.]5\s*\(k\)\s+([\d,\.]+)", re.I)
RE_RESULTADO = re.compile(
    r"Opacidad/?\s*Test MOT\s*\(1/m\)\s+([\d,\.]+)\s+([\d,\.]+)\s*(\w+)?", re.I
)
RE_EXITO = re.compile(r"[EÉ]xito global\s+(\w+)", re.I)
RE_TEMP = re.compile(r"Temperatura del aceite motor\s+(#?)([\d,\.]+)", re.I)
RE_RALENTI = re.compile(r"R[eé]gimen en ralent[ií]\s+(#?)(\d+)\s*rpm", re.I)
RE_MAXIMO = re.compile(r"R[eé]gimen m[aá]ximo\s+(#?)(\d+)\s*rpm", re.I)
RE_ACELERACION = re.compile(
    r"^\s*([1-9])\s+([\d,\.]+)\s+(\d{3,5})\s+(\d{3,5})\s*([\d,\.]+|-)?\s*$", re.M
)
RE_INSTRUMENTO = re.compile(
    r"([A-Z]{2,8}\d{5,10})\s+(\S+)\s+(\d{2}/\d{2}/\d{4})"
)
RE_CADUCADO = re.compile(r"(caducad|vencid|expirad)", re.I)


def _num(txt):
    """Convierte '1,73' o '1.73' a float."""
    if txt is None:
        return None
    txt = str(txt).strip().replace(".", "").replace(",", ".") if txt.count(",") else str(txt).strip()
    try:
        return float(txt)
    except ValueError:
        return None


def _fecha(txt):
    try:
        return datetime.strptime(txt, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def sha256_archivo(fileobj):
    """SHA256 de un file-like abierto en binario. Deja el puntero al inicio."""
    h = hashlib.sha256()
    fileobj.seek(0)
    for chunk in iter(lambda: fileobj.read(8192), b""):
        h.update(chunk)
    fileobj.seek(0)
    return h.hexdigest()


def extraer_texto(fuente):
    """Acepta ruta, file-like o texto ya extraido."""
    if isinstance(fuente, str) and "\n" in fuente:
        return fuente
    if pdfplumber is None:
        raise RuntimeError("pdfplumber no esta instalado. pip install pdfplumber")
    with pdfplumber.open(fuente) as pdf:
        return "\n".join(p.extract_text() or "" for p in pdf.pages)


def extraer(fuente):
    """
    Devuelve (datos: dict, advertencias: list[str]).
    Ningun campo faltante rompe el parser: se devuelve None y se advierte.
    """
    texto = extraer_texto(fuente)
    d = {"texto_crudo": texto}
    w = []

    # --- Identificacion ---
    m = RE_FECHA_TEST.search(texto)
    d["fecha"] = _fecha(m.group(1)) if m else None
    if not d["fecha"]:
        w.append("No se pudo leer la fecha del test")

    m = RE_HORA_TEST.search(texto)
    d["hora"] = m.group(1) if m else None

    m = RE_MATRICULA.search(texto)
    raw_mat = m.group(1).strip() if m else None
    d["matricula_raw"] = raw_mat
    d["matricula"] = None
    d["tipo_pista"] = ""

    if raw_mat:
        # Extraer dígitos para el número
        digits = re.findall(r"\d+", raw_mat)
        if digits:
            d["matricula"] = str(int(digits[-1]))  # Limpiar ceros a la izquierda, ej: '0070' -> '70'
        else:
            d["matricula"] = raw_mat

        # Detectar pista de tipo desde la matrícula (ej. 'PORTA 70', 'TRA-2178')
        up_mat = raw_mat.upper()
        if any(k in up_mat for k in ("PORTA", "POR", "GPCO", "REACH")):
            d["tipo_pista"] = "GPCO"
        elif any(k in up_mat for k in ("TRACTO", "TRA", "TETR", "TERBERG")):
            d["tipo_pista"] = "TETR"
        elif any(k in up_mat for k in ("CHASIS", "CHA")):
            d["tipo_pista"] = "CHA"

    if not d["matricula"]:
        w.append("No se pudo leer la matricula del equipo")

    m = RE_VIN.search(texto)
    d["vin"] = m.group(1).strip() if m else ""
    if d["vin"]:
        up_vin = d["vin"].upper()
        if not d["tipo_pista"]:
            if any(k in up_vin for k in ("TRACTO", "TRA", "TETR", "TERBERG")):
                d["tipo_pista"] = "TETR"
            elif any(k in up_vin for k in ("PORTA", "POR", "GPCO", "REACH")):
                d["tipo_pista"] = "GPCO"
            elif any(k in up_vin for k in ("CHASIS", "CHA")):
                d["tipo_pista"] = "CHA"
        if not re.fullmatch(r"[A-HJ-NPR-Z0-9]{17}", d["vin"]):
            w.append(f"El campo VIN no contiene un VIN valido ('{d['vin']}')")

    # Fabricante/Modelo aparecen 2 veces (vehiculo e instrumento): tomar el primero
    m = RE_FABRICANTE.search(texto)
    d["fabricante"] = m.group(1).strip() if m else ""
    m = RE_MODELO.search(texto)
    d["modelo"] = m.group(1).strip() if m else ""

    if not d["tipo_pista"]:
        fab_mod = f"{d['fabricante']} {d['modelo']}".upper()
        if any(k in fab_mod for k in ("TERBERG", "YT220", "OTTAWA", "MAFI")):
            d["tipo_pista"] = "TETR"
        elif any(k in fab_mod for k in ("KALMAR", "KONECRANES", "FANTUZZI", "SMV", "DRG")):
            d["tipo_pista"] = "GPCO"

    # --- Limites ---
    m = RE_K_LIMITE.search(texto)
    d["k_limite"] = _num(m.group(1)) if m else None

    m = RE_TOL_BAJA.search(texto)
    d["tol_baja"] = _num(m.group(1)) if m else 0.50
    m = RE_TOL_ALTA.search(texto)
    d["tol_alta"] = _num(m.group(1)) if m else 0.70

    # --- Resultado ---
    m = RE_RESULTADO.search(texto)
    if m:
        d["k_limite"] = d["k_limite"] or _num(m.group(1))
        d["k_medio"] = _num(m.group(2))
    else:
        d["k_medio"] = None
        w.append("No se pudo leer el valor medio de opacidad")

    m = RE_EXITO.search(texto)
    d["exito_declarado"] = m.group(1).upper() if m else None

    # --- Condiciones y deteccion de campos digitados a mano ---
    d["campos_manuales"] = []
    for regex, clave, etiqueta in (
        (RE_TEMP, "temp_aceite", "Temperatura del aceite motor"),
        (RE_RALENTI, "rpm_ralenti", "Regimen en ralenti"),
        (RE_MAXIMO, "rpm_maximo", "Regimen maximo"),
    ):
        m = regex.search(texto)
        if not m:
            d[clave] = None
            continue
        manual, valor = m.group(1), _num(m.group(2))
        d[clave] = int(valor) if valor is not None else None
        if manual == "#":
            d["campos_manuales"].append(clave)
            w.append(f"{etiqueta}: valor digitado manualmente, no medido por el instrumento")

    # --- Aceleraciones ---
    d["aceleraciones"] = []
    for num, k, r_ral, r_max, tiempo in RE_ACELERACION.findall(texto):
        d["aceleraciones"].append({
            "numero": int(num),
            "k": _num(k),
            "rpm_ralenti": int(r_ral),
            "rpm_maximo": int(r_max),
            "tiempo_s": _num(tiempo) if tiempo and tiempo != "-" else None,
        })

    n = len(d["aceleraciones"])
    if n < 3:
        w.append(f"Solo se detectaron {n} aceleraciones (la norma exige 3)")

    if d["aceleraciones"]:
        ks = [a["k"] for a in d["aceleraciones"] if a["k"] is not None]
        if ks:
            dispersion = round(max(ks) - min(ks), 3)
            d["dispersion"] = dispersion
            ref = d["k_medio"] if d["k_medio"] is not None else max(ks)
            tol = d["tol_baja"] if ref < 2.5 else d["tol_alta"]
            d["tolerancia_aplicable"] = tol
            if tol and dispersion > tol:
                w.append(
                    f"Dispersion entre aceleraciones {dispersion} 1/m "
                    f"excede la tolerancia {tol} 1/m"
                )
            # Verificacion cruzada del promedio declarado
            if d["k_medio"] is not None:
                calc = round(sum(ks) / len(ks), 2)
                if abs(calc - d["k_medio"]) > 0.05:
                    w.append(
                        f"El promedio declarado ({d['k_medio']}) no coincide con "
                        f"el calculado de las aceleraciones ({calc})"
                    )

        if all(a["tiempo_s"] is None for a in d["aceleraciones"]):
            w.append("No se registro tiempo de aceleracion en ninguna pasada")

    # --- Instrumento ---
    d["opacimetro"] = None
    m = RE_INSTRUMENTO.search(texto)
    if m:
        venc = _fecha(m.group(3))
        d["opacimetro"] = {
            "numero_serie": m.group(1),
            "numero_homologacion": m.group(2),
            "vencimiento_control": venc,
            "fabricante": "TEXA SPA" if "TEXA" in texto.upper() else "",
            "modelo": "OPABOX Autopower" if "OPABOX" in texto.upper() else "",
        }
        if venc and d["fecha"] and d["fecha"] > venc:
            dias = (d["fecha"] - venc).days
            w.append(
                f"CALIBRACION VENCIDA: el control periodico del opacimetro vencio el "
                f"{venc.strftime('%d/%m/%Y')}, {dias} dias antes del test. "
                f"El resultado no tiene trazabilidad metrologica."
            )
    else:
        w.append("No se pudo identificar el opacimetro utilizado")

    if RE_CADUCADO.search(texto):
        nota = "El informe declara explicitamente una caducidad del control periodico"
        if nota not in w:
            w.append(nota)

    # --- Coherencia final ---
    if d.get("k_medio") is not None and d.get("k_limite"):
        d["aprobado"] = d["k_medio"] <= d["k_limite"]
        if d["exito_declarado"] and d["exito_declarado"].startswith("SUPERAD") != d["aprobado"]:
            w.append("El resultado declarado en el informe no coincide con el recalculado")
    else:
        d["aprobado"] = None

    if d.get("temp_aceite") is not None and d["temp_aceite"] < 60:
        w.append(f"Temperatura de aceite {d['temp_aceite']} C bajo el minimo de 60 C")

    m = re.search(r"Testado por\s*(?:Firma)?\s*(.*)", texto, re.I)
    nombre = (m.group(1).strip() if m else "")
    d["operador_detectado"] = bool(nombre)
    d["operador"] = nombre
    if not nombre:
        w.append("El informe no identifica al operador que realizo el test")

    return d, w
