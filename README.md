# 🔧 TireWatch v1.0
### Sistema de Control de Desgaste y Confiabilidad de Equipos Portuarios
> **STI / Hanseatic Global Terminals**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.14-red)](https://www.django-rest-framework.org/)
[![SQLite](https://img.shields.io/badge/SQLite-3-blue?logo=sqlite)](https://www.sqlite.org/)
[![Deploy](https://img.shields.io/badge/Deploy-Windows_NSSM_+_Waitress-0a7cff)]()
[![License](https://img.shields.io/badge/License-Privado-lightgrey)]()

---

## 📋 Descripción

**TireWatch** es una plataforma web de gestión y análisis de confiabilidad para flotas de equipos portuarios (reach stackers, straddle carriers, RTGs, etc.). El sistema permite registrar, analizar y proyectar el desgaste de neumáticos y turbos, generando indicadores clave de mantenimiento como MTBF, tasas de falla y fechas estimadas de cambio.

### Módulos Activos

| Módulo | Estado | Descripción |
|---|---|---|
| 🛞 **Neumáticos** | ✅ Activo | Mediciones, tasas de desgaste, proyecciones de cambio |
| 💨 **Turbos** | ✅ Activo | Control de horas de operación y overhaul |
| 🛑 **Frenos** | ✅ Activo | Desgaste de pastillas y discos de freno |
| ⛓️ **Cadenas** | ✅ Activo | Elongación y ciclos de cadenas STS / RTG |
| 🏗️ **Equipos** | ✅ Activo | Catálogo maestro de equipos y flota |
| 👤 **Core / Auth** | ✅ Activo | Usuarios, roles y departamentos |
| 📊 **Dashboard** | ✅ Activo | KPIs, speedómetros MTBF, análisis de confiabilidad |

---

## 🏛️ Arquitectura

```
tirewatch/
├── backend/                    # Aplicación principal Django
│   ├── tirewatch/              # Settings, URLs raíz, WSGI/ASGI
│   ├── core/                   # Usuarios, autenticación, departamentos
│   ├── equipos/                # Catálogo maestro de equipos
│   ├── neumaticos/             # Mediciones, análisis y proyecciones de neumáticos
│   │   ├── models.py           # Modelos: Neumatico, Medicion, TasaDesgaste
│   │   ├── services.py         # Motor de cálculo de desgaste y proyecciones
│   │   ├── importador.py       # Importación desde Excel (formato STI)
│   │   └── views.py            # API REST endpoints
│   ├── turbos/                 # Control de horas y overhaul de turbos
│   │   ├── models.py           # Modelos: Turbo, RegistroHoras
│   │   └── services.py         # Lógica de negocio para turbos
│   ├── frenos/                 # Desgaste de pastillas y discos de freno
│   ├── cadenas/                # Elongación y ciclos de cadenas STS / RTG
│   ├── web/                    # Vistas HTML (HTMX + Alpine.js)
│   │   └── views.py            # Dashboard y vistas principales
│   ├── templates/              # Plantillas HTML base
│   ├── static/                 # CSS/JS/imágenes (logos STI y holding)
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env                    # Configuración definitiva (192.168.38.14:8011)
│   └── venv/                   # Entorno virtual (no versionado)
├── scripts/                    # Despliegue en servidor Windows (NSSM + Waitress)
│   ├── desplegar.bat           # Instalación inicial en servidor nuevo
│   ├── instalar_servicio.bat   # Registra TireWatch como servicio de Windows
│   ├── iniciar.bat             # Arranque del servidor (lo ejecuta NSSM)
│   ├── actualizar.bat          # Actualizar código y reiniciar servicio
│   └── copiar_al_servidor.bat  # Copiar código desde desarrollo al servidor
└── README.md
```

---

## 🚀 Inicio Rápido

### 💻 Desarrollo local (Windows)

```powershell
# 1. Clonar y entrar al backend
git clone https://github.com/rgonzalez1043/Tirewatch_v1.0.git
cd Tirewatch_v1.0\backend

# 2. Crear y activar el entorno virtual
python -m venv venv
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. (Solo desarrollo) activar DEBUG en backend\.env
#    DJANGO_DEBUG=True

# 5. Migraciones e inicialización de datos
python manage.py migrate
python manage.py init_tirewatch

# 6. Servidor de desarrollo (puerto 8011)
python manage.py runserver
```

**Accesos:**
- 🌐 **Aplicación:** http://localhost:8011
- 🔧 **Admin Django:** http://localhost:8011/admin/

> ℹ️ El comando `runserver` está personalizado para usar el puerto **8011**. El `.env` viene con la configuración definitiva de producción; para desarrollo cambia solo `DJANGO_DEBUG=True`.

---

### 🖥️ Producción — Servidor Windows (NSSM + Waitress)

El servidor corre en **`192.168.38.14:8011`** como **servicio de Windows** (NSSM) sirviendo con **Waitress**. No usa Docker.

```powershell
# --- Primera instalación en un servidor nuevo ---
# 1. Copiar el proyecto al servidor (desde la máquina de desarrollo)
scripts\copiar_al_servidor.bat

# 2. En el servidor: despliegue inicial (crea venv, instala deps, migra, estáticos)
scripts\desplegar.bat

# 3. Registrar como servicio de Windows (como Administrador — requiere NSSM)
scripts\instalar_servicio.bat
```

```powershell
# --- Actualizar una instalación existente ---
scripts\copiar_al_servidor.bat     # copia los cambios de código
scripts\actualizar.bat             # migra, recolecta estáticos y reinicia el servicio
```

> El `.env` definitivo (con `DEBUG=False`, `ALLOWED_HOSTS` y la IP del servidor) viaja con el código. La base de datos del servidor **no** se sobrescribe: `copiar_al_servidor.bat` excluye `db.sqlite3` porque el servidor recibe datos en vivo desde la web y la app Android.

---

## ⚙️ Variables de Entorno

La configuración vive en `backend/.env` (ya incluida en el repo con los valores de producción):

```env
# ── Django ──────────────────────────────────────────────
DJANGO_SECRET_KEY=<clave-secreta-larga-y-aleatoria>
DJANGO_DEBUG=False                                     # True solo en desarrollo
DJANGO_ALLOWED_HOSTS=192.168.38.14,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://192.168.38.14:8011         # login web con DEBUG=False

# ── Base de Datos ───────────────────────────────────────
# SQLite por defecto — no requiere configuración adicional.

# ── API Externa de Horómetros (servidor de flota) ───────
HOROMETROS_API_BASE_URL=http://192.168.38.14:8009/vehiculos
HOROMETROS_API_TIMEOUT=5
```

---

## 📡 API Endpoints

### Autenticación
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/api/auth/login/` | Iniciar sesión |
| `POST` | `/api/auth/logout/` | Cerrar sesión |
| `GET` | `/api/auth/perfil/` | Perfil del usuario autenticado |
| `POST` | `/api/auth/registro/` | Registrar nuevo usuario |

### Equipos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/equipos/lista/` | Listar todos los equipos |
| `POST` | `/api/equipos/lista/` | Crear nuevo equipo |
| `GET` | `/api/equipos/marcas/` | Listar marcas disponibles |
| `GET` | `/api/equipos/tipos/` | Tipos de equipo |

### Neumáticos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/neumaticos/dashboard/` | Datos del dashboard principal |
| `GET` | `/api/neumaticos/mediciones/` | Listar mediciones |
| `POST` | `/api/neumaticos/mediciones/` | Registrar medición desde terreno |
| `POST` | `/api/neumaticos/importar/` | Importar mediciones desde Excel |
| `POST` | `/api/neumaticos/analisis/ejecutar/` | Ejecutar análisis de desgaste |
| `GET` | `/api/neumaticos/tasas/` | Tasas de desgaste calculadas |
| `GET` | `/api/neumaticos/proyecciones/` | Proyecciones de fecha de cambio |
| `GET` | `/api/neumaticos/grafico/{num}/` | Datos para gráfico por equipo |

### Turbos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/turbos/` | Listar turbos registrados |
| `POST` | `/api/turbos/` | Registrar nuevo turbo |

### Frenos
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET / POST` | `/api/frenos/componentes/` | Componentes de freno (pastillas, discos) |
| `GET / POST` | `/api/frenos/mediciones/` | Mediciones de desgaste de freno |
| `GET` | `/api/frenos/proyecciones/` | Proyecciones de cambio de freno |

### Cadenas
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET / POST` | `/api/cadenas/mediciones/` | Mediciones de elongación de cadena |
| `GET` | `/api/cadenas/proyecciones/` | Proyecciones de cambio de cadena |

---

## ✅ Funcionalidades Implementadas

- [x] Importación de mediciones desde Excel (formato planilla STI)
- [x] Registro de mediciones en terreno vía web
- [x] Cálculo de tasas de desgaste por marca, modelo y posición
- [x] Proyección de fecha y kilometraje de cambio por neumático
- [x] Módulo de frenos (pastillas y discos) con proyecciones
- [x] Módulo de cadenas (elongación STS / RTG) con proyecciones
- [x] Integración con API externa de horómetros (servidor de flota)
- [x] Dashboard con alertas, KPIs y estadísticas en tiempo real
- [x] Speedómetros MTBF por módulo (ISO 14224 / IEEE 493)
- [x] Gráficos de historial y proyección por equipo
- [x] Sistema de autenticación y control de roles
- [x] Panel de administración Django
- [x] API REST completa y documentada (consumida por la web y la app Android)
- [x] App móvil Android (Flutter) operativa para registro en terreno
- [x] Despliegue como servicio de Windows (NSSM + Waitress) en la intranet

## 🗺️ Roadmap — Módulos Futuros

- [ ] **Sensores SICK** — telemetría IoT para RTG
- [ ] **Reportes PDF** — informes automáticos mensuales
- [ ] **Notificaciones** — alertas por email y Telegram
- [ ] **App Móvil iOS** — versión para iPhone/iPad

---

## 🗄️ Base de Datos

**SQLite 3** en todos los entornos — simple y sin servidor de BD adicional, ideal para uso interno en la intranet.

> ⚠️ El servidor de producción (`192.168.38.14`) mantiene su **propia** base de datos, que recibe registros en vivo desde la web y la app Android. Los scripts de despliegue **nunca** sobrescriben `db.sqlite3` del servidor.

---

## 📱 App Android (Flutter)

Existe una app móvil ([tirewatch_apk](https://github.com/rgonzalez1043/tirewatch_apk)) para registro de mediciones en terreno. Consume la misma API REST apuntando a `http://192.168.38.14:8011`:

- `POST /api/auth/login/` — autenticación por token
- `POST /api/neumaticos/mediciones/`, `/api/turbos/mediciones/`
- `POST /api/frenos/mediciones/`, `/api/cadenas/mediciones/`
- `GET /api/equipos/lista/`, `/api/frenos/componentes/`

> ⚠️ **No modificar las rutas ni los contratos de estos endpoints** sin actualizar también la app Android.

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Python 3.11+, Django 4.2, Django REST Framework 3.14, django-filter |
| **Frontend** | HTML5, HTMX, Alpine.js, Tailwind, CSS vanilla |
| **App móvil** | Flutter (registro en terreno) |
| **Base de Datos** | SQLite 3 |
| **Análisis** | NumPy, Pandas, openpyxl |
| **Deploy** | Servicio Windows (NSSM) + Waitress + WhiteNoise |
| **Integraciones** | API REST externa de horómetros (`requests`) |
| **Estándares** | ISO 14224, IEEE 493 (confiabilidad) |

---

## 📄 Licencia

Proyecto de uso **privado e interno** — STI / Hanseatic Global Terminals.  
Desarrollado por el equipo de Ingeniería de Mantenimiento Portuario.

---

<p align="center">
  <sub>TireWatch v1.0 · Mantenimiento Portuario Inteligente</sub>
</p>
