import logging
import requests as req
from django.conf import settings
from .models import TipoEquipo, Equipo

logger = logging.getLogger(__name__)

_PREFIJO_API = {
    "GPCO": "POR",
    "TETR": "TRA",
    "CHA": "CHA",
}


def consultar_horometro_externo(tipo_codigo, numero, fecha=None):
    """
    Consulta la API externa de horómetros por tipo de equipo, número y fecha opcional.
    Maneja resiliencia de formatos (ej: 2178 <-> 0178 para tractos TETR).

    Devuelve dict:
        {
            "disponible": bool,
            "horometro": float/int or None,
            "fecha": str or None,
            "codigo_externo": str,
            "error": str or None,
        }
    """
    tipo_upper = str(tipo_codigo or "").strip().upper()
    prefijo = _PREFIJO_API.get(tipo_upper)
    if not prefijo:
        # Intento de búsqueda si pasan 'TRACTO', 'PORTA', etc.
        tipo_map = {
            "TRACTO": "TRA", "TRA": "TRA", "TETR": "TRA",
            "PORTA": "POR", "POR": "POR", "GPCO": "POR",
            "CHASIS": "CHA", "CHA": "CHA",
        }
        prefijo = tipo_map.get(tipo_upper)

    if not prefijo:
        return {
            "disponible": False,
            "horometro": None,
            "fecha": None,
            "codigo_externo": "",
            "error": f"Tipo '{tipo_codigo}' no soportado en la API de horómetros.",
        }

    try:
        num_int = int(numero)
    except (ValueError, TypeError):
        return {
            "disponible": False,
            "horometro": None,
            "fecha": None,
            "codigo_externo": "",
            "error": "El número de equipo debe ser entero.",
        }

    base_url = getattr(settings, "HOROMETROS_API_BASE_URL", "http://192.168.38.14:8009/vehiculos")
    timeout = getattr(settings, "HOROMETROS_API_TIMEOUT", 5)

    # Códigos candidatos a probar (resiliencia 2178 <-> 0178 para tractos)
    codigos_a_probar = [f"{prefijo}-{str(num_int).zfill(4)}"]
    if prefijo == "TRA":
        if num_int > 1000:
            # 2178 -> 0178
            alt_num = num_int % 1000
            codigos_a_probar.append(f"{prefijo}-{str(alt_num).zfill(4)}")
        elif num_int < 1000:
            # 178 -> 2178
            alt_num = num_int + 2000
            codigos_a_probar.append(f"{prefijo}-{str(alt_num).zfill(4)}")

    params = {}
    if fecha:
        params["fecha"] = str(fecha)

    ultimo_error = None
    ultimo_codigo = codigos_a_probar[0]

    for codigo_api in codigos_a_probar:
        ultimo_codigo = codigo_api
        url = f"{base_url}/{codigo_api}/horometros"
        try:
            resp = req.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "disponible": True,
                    "horometro": data.get("horometro"),
                    "fecha": data.get("fecha") or str(fecha or ""),
                    "codigo_externo": codigo_api,
                    "error": None,
                }
            elif resp.status_code == 404:
                ultimo_error = f"Equipo {codigo_api} no encontrado en la API de horómetros."
                continue
            else:
                ultimo_error = f"API respondió con código HTTP {resp.status_code}"
        except req.exceptions.ConnectionError:
            return {
                "disponible": False,
                "horometro": None,
                "fecha": None,
                "codigo_externo": codigo_api,
                "error": "API de horómetros no disponible. Verifica la conexión de red.",
            }
        except req.exceptions.Timeout:
            return {
                "disponible": False,
                "horometro": None,
                "fecha": None,
                "codigo_externo": codigo_api,
                "error": "Tiempo de espera agotado al consultar la API de horómetros.",
            }
        except Exception as e:
            logger.warning("Error consultando horometro para %s: %s", codigo_api, e)
            ultimo_error = str(e)

    return {
        "disponible": False,
        "horometro": None,
        "fecha": None,
        "codigo_externo": ultimo_codigo,
        "error": ultimo_error or f"Equipo {ultimo_codigo} no encontrado en la API.",
    }
