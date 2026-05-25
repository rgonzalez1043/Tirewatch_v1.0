# 🔧 TireWatch v1.0
### Sistema de Control de Desgaste y Confiabilidad de Equipos Portuarios
> **STI / Hanseatic Global Terminals**

[![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/Django_REST_Framework-3.14-red)](https://www.django-rest-framework.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue?logo=docker)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-Privado-lightgrey)]()

---

## 📋 Descripción

**TireWatch** es una plataforma web de gestión y análisis de confiabilidad para flotas de equipos portuarios (reach stackers, straddle carriers, RTGs, etc.). El sistema permite registrar, analizar y proyectar el desgaste de neumáticos y turbos, generando indicadores clave de mantenimiento como MTBF, tasas de falla y fechas estimadas de cambio.

### Módulos Activos

| Módulo | Estado | Descripción |
|---|---|---|
| 🛞 **Neumáticos** | ✅ Activo | Mediciones, tasas de desgaste, proyecciones de cambio |
| 💨 **Turbos** | ✅ Activo | Control de horas de operación y overhaul |
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
│   ├── web/                    # Vistas HTML (HTMX + Alpine.js)
│   │   └── views.py            # Dashboard y vistas principales
│   ├── templates/              # Plantillas HTML base
│   ├── manage.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── docker-compose.yml
└── README.md
```

---

## 🚀 Inicio Rápido

### 🐳 Opción 1: Docker (Recomendado)

```bash
# 1. Clonar el repositorio
git clone https://github.com/rgonzalez1043/Tirewatch_v1.0.git
cd Tirewatch_v1.0

# 2. Levantar con Docker Compose
docker-compose up --build
```

**Accesos:**
- 🌐 **Aplicación:** http://localhost:8000
- 🔧 **Admin Django:** http://localhost:8000/admin/
- 👤 **Usuario inicial:** `admin` / `tirewatch2025`

> ℹ️ Hot-reload activo: los cambios en el código se reflejan automáticamente sin reiniciar.

---

### ⚙️ Opción 2: Entorno Virtual Local (sin Docker)

```bash
# 1. Clonar el repositorio
git clone https://github.com/rgonzalez1043/Tirewatch_v1.0.git
cd Tirewatch_v1.0/backend

# 2. Crear y activar el entorno virtual
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
# source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variables de entorno
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
# (Editar .env con tu SECRET_KEY y configuración de BD)

# 5. Aplicar migraciones e inicializar datos
python manage.py migrate
python manage.py init_tirewatch

# 6. Iniciar el servidor de desarrollo
python manage.py runserver
```

🌐 La app estará disponible en **http://localhost:8000**

---

### 🌍 Opción 3: Producción (Servidor)

```bash
# 1. Clonar y entrar al proyecto
git clone https://github.com/rgonzalez1043/Tirewatch_v1.0.git
cd Tirewatch_v1.0

# 2. Configurar variables de entorno de producción
cp backend/.env.example backend/.env
# Editar backend/.env con claves seguras y PostgreSQL

# 3. Construir y correr en modo producción
docker-compose up --build -d
```

---

## ⚙️ Variables de Entorno

Copiar `backend/.env.example` a `backend/.env` y configurar:

```env
# Django
DJANGO_SECRET_KEY=<clave-secreta-larga-y-aleatoria>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=tu-dominio.com,localhost

# Base de Datos (PostgreSQL para producción)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tirewatch
DB_USER=tirewatch_user
DB_PASSWORD=<contraseña-segura>
DB_HOST=localhost
DB_PORT=5432

# CORS (orígenes permitidos)
CORS_ORIGINS=https://tu-dominio.com
```

> ⚠️ **Nunca subas el archivo `.env` al repositorio.** Ya está incluido en `.gitignore`.

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

---

## ✅ Funcionalidades Implementadas

- [x] Importación de mediciones desde Excel (formato planilla STI)
- [x] Registro de mediciones en terreno vía web
- [x] Cálculo de tasas de desgaste por marca, modelo y posición
- [x] Proyección de fecha y kilometraje de cambio por neumático
- [x] Dashboard con alertas, KPIs y estadísticas en tiempo real
- [x] Speedómetros MTBF por módulo (ISO 14224 / IEEE 493)
- [x] Gráficos de historial y proyección por equipo
- [x] Sistema de autenticación y control de roles
- [x] Panel de administración Django
- [x] API REST completa y documentada
- [x] Soporte Docker para desarrollo y producción
- [x] Migración a PostgreSQL en producción

## 🗺️ Roadmap — Módulos Futuros

- [ ] **Frenos** — desgaste de pastillas y discos
- [ ] **Cadenas** — elongación y ciclos STS / RTG
- [ ] **Sensores SICK** — telemetría IoT para RTG
- [ ] **Reportes PDF** — informes automáticos mensuales
- [ ] **Notificaciones** — alertas por email y Telegram
- [ ] **App Móvil** — Flutter para registro en terreno

---

## 🗄️ Base de Datos

| Entorno | Motor | Configuración |
|---------|-------|---------------|
| Desarrollo | SQLite 3 | Automático (no requiere configuración) |
| Producción | PostgreSQL | Configurar via `.env` |

**Migración a PostgreSQL:**
```env
DB_ENGINE=django.db.backends.postgresql
DB_NAME=tirewatch
DB_USER=tirewatch_user
DB_PASSWORD=contraseña_segura
DB_HOST=localhost
DB_PORT=5432
```

---

## 🛠️ Stack Tecnológico

| Capa | Tecnología |
|------|------------|
| **Backend** | Python 3.11, Django 4.2, Django REST Framework 3.14 |
| **Frontend** | HTML5, HTMX, Alpine.js, CSS vanilla |
| **Base de Datos** | SQLite (dev) / PostgreSQL (prod) |
| **Análisis** | NumPy, Pandas |
| **Deploy** | Docker, Docker Compose, Gunicorn |
| **Estándares** | ISO 14224, IEEE 493 (confiabilidad) |

---

## 📄 Licencia

Proyecto de uso **privado e interno** — STI / Hanseatic Global Terminals.  
Desarrollado por el equipo de Ingeniería de Mantenimiento Portuario.

---

<p align="center">
  <sub>TireWatch v1.0 · Mantenimiento Portuario Inteligente</sub>
</p>
