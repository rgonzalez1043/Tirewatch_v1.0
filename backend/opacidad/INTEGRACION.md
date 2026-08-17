# Módulo Opacidad — integración en TireWatch

App nueva `opacidad`, escrita siguiendo el patrón de `turbos`
(Medición + Proyección + Analizador + ViewSets DRF).

---

## 1. Copiar la app

Copiar la carpeta `opacidad/` completa a `C:\1.-Proyectos\tirewatch\backend\`.

## 2. `requirements.txt`

Agregar (`numpy` ya está):

```
# Lectura de informes PDF de opacidad (TEXA OPABOX)
pdfplumber>=0.11
```

```
pip install pdfplumber
```

## 3. `tirewatch/settings.py`

**INSTALLED_APPS** — después de `cadenas`:

```python
    "cadenas.apps.CadenasConfig",
    "opacidad.apps.OpacidadConfig",
    "web.apps.WebConfig",
```

**Servir los PDF en desarrollo** — `MEDIA_ROOT` ya está definido, pero falta la
ruta. En `tirewatch/urls.py`:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    ...
    path("api/opacidad/", include("opacidad.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

En producción (Waitress + WhiteNoise) WhiteNoise **no sirve `MEDIA_ROOT`**, solo
estáticos. Agregar al final de `settings.py`:

```python
WHITENOISE_ROOT = None
```

y servir `/media/` con `whitenoise.WhiteNoise` envolviendo la app WSGI, o dejar
que los PDF se descarguen por una vista autenticada. Recomendado esto último:
son documentos de auditoría, no deberían quedar públicos por URL adivinable.

**Jazzmin** — agregar al `order_with_respect_to` y a `icons`:

```python
    "order_with_respect_to": [
        "equipos", "neumaticos", "turbos", "frenos", "cadenas", "opacidad",
        "core", "auth", "authtoken",
    ],

    "icons": {
        ...
        "opacidad.opacimetro": "fas fa-tachometer-alt",
        "opacidad.medicionopacidad": "fas fa-smog",
        "opacidad.proyeccionopacidad": "fas fa-chart-line",
        "opacidad.importacionopacidad": "fas fa-file-import",
    },
```

## 4. `core/models.py` — `ConfiguracionSistema`

Agregar el bloque del módulo, siguiendo tu convención de umbrales:

```python
    # Módulo Opacidad (emisiones diésel — control semestral)
    # Ref: límite k declarado en el informe del opacímetro. NO se asume:
    # este valor es solo el default cuando el PDF no lo trae.
    limite_opacidad_k_default = models.FloatField(
        default=3.0,
        help_text="Coeficiente de absorción máximo en 1/m cuando el informe no lo declara"
    )
    umbral_alerta_opacidad_pct = models.FloatField(
        default=0.70,
        help_text="Fracción del límite (0.0 a 1.0) desde la cual generar alerta ATENCIÓN"
    )
    umbral_critico_opacidad_pct = models.FloatField(
        default=0.85,
        help_text="Fracción del límite (0.0 a 1.0) desde la cual generar alerta CRÍTICO"
    )
    meses_periodicidad_opacidad = models.IntegerField(
        default=6,
        help_text="Periodicidad del control de opacidad en meses (semestral)"
    )
```

El analizador usa `getattr()` con defaults, así que **funciona aunque no agregues
estos campos** — pero conviene tenerlos para poder calibrar los umbrales sin
tocar código.

## 5. Migraciones

```
python manage.py makemigrations core opacidad
python manage.py migrate
python manage.py test opacidad
```

---

## Endpoints

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/opacidad/importar/` | **Paso 1**: sube el PDF, lo parsea, devuelve datos + advertencias. No crea nada. |
| GET | `/api/opacidad/importaciones/?estado=PENDIENTE` | Cola de revisión |
| POST | `/api/opacidad/importaciones/{id}/confirmar/` | **Paso 2**: crea la medición con los datos validados |
| POST | `/api/opacidad/importaciones/{id}/rechazar/` | Descarta, dejando registro |
| GET/POST | `/api/opacidad/mediciones/` | CRUD; POST = medición manual en terreno |
| POST | `/api/opacidad/mediciones/{id}/anular/` | Anula (requiere `motivo`). DELETE está bloqueado. |
| GET | `/api/opacidad/mediciones/grafico/{equipo_id}/` | Serie de k + proyección |
| GET | `/api/opacidad/proyecciones/` | Semáforo por equipo |
| GET | `/api/opacidad/proyecciones/resumen/` | Tarjetas del dashboard |
| POST | `/api/opacidad/analizar/` | Recalcula todas las proyecciones |
| GET | `/api/opacidad/cobertura/?periodo=2026-S1` | **Reporte de auditoría**: cobertura de la campaña |

### Flujo de importación

```
subir PDF ──► parser ──► ImportacionOpacidad (PENDIENTE)
                            │  datos + advertencias
                            ▼
                    revisión humana en pantalla
                            │
              ┌─────────────┴─────────────┐
         confirmar/                   rechazar/
              │                            │
     MedicionOpacidad              queda registrada
     + Aceleraciones               como rechazada
              │
     AnalizadorOpacidad.analizar_equipo()
```

El parser **nunca escribe directo**. El informe TEXA trae `VIN = TRACTO`,
`Año de fabricación = Turbo Diesel` y tres campos digitados a mano: hacer commit
automático importaría basura.

---

## Comandos

```bash
# Validar que el parser soporta tus PDF (tractos y portas) sin escribir nada
python manage.py cargar_pdf_opacidad "C:\informes\2026-S1"

# Carga histórica desde CSV
python manage.py importar_opacidad_csv historico.csv --dry-run
python manage.py importar_opacidad_csv historico.csv

# Recalcular proyecciones (tarea programada)
python manage.py analizar_opacidad
```

CSV esperado (separador `;`):

```
tipo_equipo;numero;fecha;k_medio;k_limite;horometro;operador;observacion
TRACTO;2178;15/12/2025;1,55;3,00;28400;J. Pérez;
TRACTO;2178;20/06/2025;1,41;3,00;24100;;
PORTA;312;18/12/2025;2,10;3,00;;;
```

---

## Semáforo

Se mantienen los tres estados del resto de TireWatch (`OK` / `ATENCION` /
`CRITICO`) para que el dashboard consolidado no tenga que conocer un cuarto
color. Reglas, en orden de prioridad:

| Estado | Disparo |
|---|---|
| CRÍTICO | Test reprobado (k > límite) |
| CRÍTICO | k ≥ 85% del límite |
| CRÍTICO | La tendencia proyecta superar el límite en el próximo control |
| ATENCIÓN | Control semestral vencido |
| ATENCIÓN | k ≥ 70% del límite |
| ATENCIÓN | Pendiente > 0,30 (1/m)/año |
| ATENCIÓN | Salto > 0,50 respecto del control anterior |
| ATENCIÓN | Último test con opacímetro fuera de calibración |
| OK | Ninguna de las anteriores |

La regla que da valor real es la tercera: un tracto en k=1,73 con pendiente
+0,45/año aprueba los próximos cuatro controles y aun así te está avisando, con
~18 meses de anticipación, que los inyectores o el turbo se van.

---

## Trazabilidad para auditoría

- El PDF original se guarda siempre; su SHA256 queda indexado y bloquea recargas.
- Nada se borra: `anulado=True` + motivo + usuario + timestamp. `DELETE` devuelve 405.
- `calibracion_vigente` se evalúa contra la **fecha del test**, no contra hoy, y
  queda congelado. El TRA-2178 del 18/06/2026 queda marcado permanentemente como
  medido con instrumento vencido desde el 23/01/2026.
- Los registros con `origen=HISTORICO` no tienen archivo ni SHA: quedan
  distinguibles como evidencia de menor jerarquía, que es lo correcto de mostrar.
- `texto_crudo` guarda el texto extraído del PDF, para poder auditar el parseo
  sin volver a abrir el archivo.

---

## Pendientes de decisión

1. **Horómetro.** El informe TEXA no lo trae. Ya tienes
   `HOROMETROS_API_BASE_URL` apuntando a `192.168.38.14:8009/vehiculos`: conviene
   capturarlo automáticamente al confirmar la importación, igual que en el módulo
   de cables. Eso habilita `tasa_k_1000h`, mucho mejor indicador que la pendiente
   por año en una flota con utilización dispareja.

2. **Límite k por familia de equipo.** El YT220 declara 3,00. Los
   portacontenedores probablemente tengan otro. El valor se guarda **por medición**
   tal como viene del informe; falta una tabla de límites esperados por tipo para
   detectar cuando el operador del opacímetro configuró un límite equivocado.

3. **`Equipo.numero` no es único globalmente** (`unique_together = numero + tipo`).
   Si un tracto y una porta comparten número, la importación pide selección
   manual en vez de adivinar. Ver `ImportarPDFView._resolver_equipo`.
