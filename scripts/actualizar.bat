@echo off
setlocal
title TireWatch - Actualizar

REM ============================================================
REM  TireWatch — actualizar.bat
REM  Ejecutar cada vez que copies cambios de codigo al servidor.
REM  Detiene el servicio, actualiza, y lo vuelve a levantar.
REM  Requiere permisos de Administrador.
REM ============================================================

set SCRIPTS_DIR=%~dp0
set PROYECTO=%SCRIPTS_DIR%..\backend
set SERVICIO_NOMBRE=TireWatch

cd /d "%PROYECTO%"

echo.
echo  =====================================================
echo   TireWatch - Actualizacion de Codigo
echo  =====================================================
echo.

REM Verificar Administrador
net session >nul 2>&1
if errorlevel 1 (
    echo  ADVERTENCIA: Sin permisos de Administrador.
    echo  El reinicio del servicio podria fallar.
    echo.
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM ── 1. Detener servicio ──────────────────────────────────────
echo [1/5] Deteniendo servicio %SERVICIO_NOMBRE%...
nssm stop %SERVICIO_NOMBRE% >nul 2>&1
timeout /t 3 >nul
echo  OK
echo.

REM ── 2. Dependencias ──────────────────────────────────────────
echo [2/5] Verificando nuevas dependencias...
pip install -r requirements.txt --quiet
echo  OK
echo.

REM ── 3. Migraciones ───────────────────────────────────────────
echo [3/5] Aplicando migraciones de base de datos...
python manage.py migrate --noinput
if errorlevel 1 (
    echo  ERROR en migraciones - revisa los logs antes de reiniciar.
    pause
    exit /b 1
)
echo  OK
echo.

REM ── 4. Archivos estaticos ────────────────────────────────────
echo [4/5] Actualizando archivos estaticos...
python manage.py collectstatic --noinput --clear
echo  OK
echo.

REM ── 5. Reiniciar servicio ────────────────────────────────────
echo [5/5] Reiniciando servicio...
nssm start %SERVICIO_NOMBRE%
timeout /t 5 >nul
nssm status %SERVICIO_NOMBRE%
echo.

echo  Actualizacion completada.
echo  URL: http://localhost:8011
echo.
pause
