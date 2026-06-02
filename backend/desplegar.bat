@echo off
setlocal EnableDelayedExpansion
title TireWatch - Despliegue

echo.
echo  =====================================================
echo   TireWatch - Despliegue en Servidor Windows
echo  =====================================================
echo.

REM Directorio del proyecto (este script debe estar dentro de backend\)
set PROYECTO=%~dp0
cd /d "%PROYECTO%"

REM ── 1. Verificar Python ───────────────────────────────────
echo [1/7] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo  ERROR: Python no encontrado.
    echo  Descarga Python 3.11+ desde https://www.python.org/downloads/
    echo  Asegurate de marcar "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)
python --version
echo.

REM ── 2. Crear entorno virtual ──────────────────────────────
echo [2/7] Preparando entorno virtual...
if not exist "venv" (
    echo Creando entorno virtual nuevo...
    python -m venv venv
    if errorlevel 1 (
        echo  ERROR: No se pudo crear el entorno virtual.
        pause
        exit /b 1
    )
) else (
    echo Entorno virtual ya existe, reutilizando.
)
echo.

REM Activar venv
call venv\Scripts\activate.bat

REM ── 3. Instalar dependencias ──────────────────────────────
echo [3/7] Instalando dependencias de Python...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  ERROR: Fallo la instalacion de dependencias.
    echo  Revisa requirements.txt y la conexion a internet.
    pause
    exit /b 1
)
echo OK - Dependencias instaladas.
echo.

REM ── 4. Crear .env ─────────────────────────────────────────
echo [4/7] Configuracion del entorno...
if not exist ".env" (
    copy ".env.ejemplo" ".env" >nul
    echo.
    echo  IMPORTANTE: Se creo el archivo .env desde la plantilla.
    echo  Debes editarlo antes de continuar:
    echo.
    echo    1. Cambia DJANGO_SECRET_KEY por una clave unica
    echo    2. Agrega la IP de este servidor en DJANGO_ALLOWED_HOSTS
    echo    3. Verifica HOROMETROS_API_BASE_URL
    echo.
    echo  Abriendo .env en el Bloc de Notas...
    notepad "%PROYECTO%.env"
    echo.
    echo  Presiona Enter cuando hayas guardado el archivo .env
    pause >nul
) else (
    echo .env ya existe, omitiendo.
)
echo.

REM ── 5. Migraciones ────────────────────────────────────────
echo [5/7] Ejecutando migraciones de base de datos...
python manage.py migrate --noinput
if errorlevel 1 (
    echo  ERROR: Fallaron las migraciones.
    pause
    exit /b 1
)
echo.

REM ── 6. Superusuario ───────────────────────────────────────
echo [6/7] Cuenta de administrador...
set /p CREAR_ADMIN=   Es la primera instalacion? Crear cuenta admin? (S/N):
if /i "!CREAR_ADMIN!"=="S" (
    echo.
    python manage.py createsuperuser
)
echo.

REM ── 7. Archivos estaticos ─────────────────────────────────
echo [7/7] Recolectando archivos estaticos (CSS, JS, imagenes)...
python manage.py collectstatic --noinput --clear
if errorlevel 1 (
    echo  ERROR: Fallo collectstatic.
    pause
    exit /b 1
)
echo.

echo  =====================================================
echo   Despliegue completado exitosamente!
echo  =====================================================
echo.
echo  Siguiente paso:
echo    Ejecuta  instalar_servicio.bat  para registrar
echo    TireWatch como servicio de Windows con NSSM.
echo.
echo  Para probar antes de instalar el servicio:
echo    Ejecuta  iniciar_tirewatch.bat  manualmente
echo    y abre  http://localhost:8000  en el navegador.
echo.
pause
