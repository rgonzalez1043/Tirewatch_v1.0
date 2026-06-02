@echo off
setlocal EnableDelayedExpansion
title TireWatch - Despliegue Inicial

REM ============================================================
REM  TireWatch — desplegar.bat
REM  PRIMERA INSTALACION en un servidor nuevo.
REM  Ejecutar una sola vez despues de copiar el proyecto.
REM  Requiere: Python 3.11+ instalado y en PATH.
REM ============================================================

set SCRIPTS_DIR=%~dp0
set PROYECTO=%SCRIPTS_DIR%..\backend
set SERVICIO_BAT=%SCRIPTS_DIR%instalar_servicio.bat

cd /d "%PROYECTO%"

echo.
echo  =====================================================
echo   TireWatch - Despliegue Inicial en Servidor
echo  =====================================================
echo.
echo  Directorio detectado: %PROYECTO%
echo.

REM ── 1. Verificar Python ──────────────────────────────────────
echo [1/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no encontrado en PATH.
    echo  Descarga Python 3.11+ desde https://www.python.org/downloads/
    echo  Al instalar marca "Add Python to PATH".
    echo.
    pause
    exit /b 1
)
python --version
echo  OK
echo.

REM ── 2. Entorno virtual ───────────────────────────────────────
echo [2/7] Preparando entorno virtual...
if not exist "venv" (
    echo  Creando entorno virtual nuevo en backend\venv\ ...
    python -m venv venv
    if errorlevel 1 (
        echo  ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
    echo  OK - Entorno virtual creado.
) else (
    echo  Entorno virtual ya existe, reutilizando.
)
echo.

REM Activar venv
call venv\Scripts\activate.bat

REM ── 3. Dependencias ──────────────────────────────────────────
echo [3/7] Instalando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt
if errorlevel 1 (
    echo  ERROR: Fallo la instalacion de dependencias.
    echo  Verifica requirements.txt y la conexion a internet.
    pause
    exit /b 1
)
echo  OK - Dependencias instaladas.
echo.

REM ── 4. Configuracion .env ────────────────────────────────────
echo [4/7] Configuracion del entorno (.env)...
if not exist ".env" (
    copy ".env.example" ".env" >nul
    echo.
    echo  IMPORTANTE: Se creo el archivo .env desde la plantilla.
    echo  Debes editarlo antes de continuar:
    echo.
    echo    1. DJANGO_SECRET_KEY  - Clave unica (genera en https://djecrety.ir)
    echo    2. DJANGO_ALLOWED_HOSTS - IP del servidor, ej: 192.168.1.50
    echo    3. DJANGO_DEBUG=False  - Siempre False en produccion
    echo    4. HOROMETROS_API_BASE_URL - URL de la API de horometros
    echo.
    echo  Abriendo .env en el Bloc de Notas...
    notepad "%PROYECTO%\.env"
    echo.
    echo  Presiona Enter cuando hayas guardado el archivo .env y este listo.
    pause >nul
) else (
    echo  .env ya existe, omitiendo.
)
echo.

REM ── 5. Migraciones ───────────────────────────────────────────
echo [5/7] Ejecutando migraciones de base de datos...
python manage.py migrate --noinput
if errorlevel 1 (
    echo  ERROR: Fallaron las migraciones.
    echo  Revisa la configuracion de base de datos en .env
    pause
    exit /b 1
)
echo  OK
echo.

REM ── 6. Superusuario ──────────────────────────────────────────
echo [6/7] Cuenta de administrador...
set /p CREAR_ADMIN=  Es la primera instalacion? Crear cuenta admin? (S/N): 
if /i "!CREAR_ADMIN!"=="S" (
    echo.
    python manage.py createsuperuser
)
echo.

REM ── 7. Archivos estaticos ────────────────────────────────────
echo [7/7] Recolectando archivos estaticos...
python manage.py collectstatic --noinput --clear
if errorlevel 1 (
    echo  ERROR: Fallo collectstatic.
    pause
    exit /b 1
)
echo  OK
echo.

echo  =====================================================
echo   Despliegue completado exitosamente!
echo  =====================================================
echo.
echo  Siguiente paso:
echo    Ejecuta  scripts\instalar_servicio.bat  (como Administrador)
echo    para registrar TireWatch como servicio de Windows.
echo.
echo  Para probar manualmente antes del servicio:
echo    Ejecuta  scripts\iniciar.bat
echo    y abre  http://localhost:8011  en el navegador.
echo.
pause
