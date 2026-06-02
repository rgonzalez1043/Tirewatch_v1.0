@echo off
setlocal
title TireWatch - Actualizar

REM ============================================================
REM  Actualizar TireWatch cuando hay cambios de codigo
REM  Ejecutar cada vez que copies nuevos archivos al servidor
REM ============================================================

set PROYECTO=%~dp0
set SERVICIO_NOMBRE=TireWatch

cd /d "%PROYECTO%"

echo.
echo  =====================================================
echo   TireWatch - Actualizacion de Codigo
echo  =====================================================
echo.

REM Verificar Administrador (necesario para reiniciar servicio)
net session >nul 2>&1
if errorlevel 1 (
    echo  ADVERTENCIA: Sin permisos de Administrador.
    echo  El reinicio del servicio podria fallar.
    echo.
)

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Detener servicio
echo [1/5] Deteniendo servicio...
nssm stop %SERVICIO_NOMBRE% >nul 2>&1
timeout /t 3 >nul
echo OK
echo.

REM Instalar nuevas dependencias si requirements.txt cambio
echo [2/5] Verificando dependencias...
pip install -r requirements.txt --quiet
echo OK
echo.

REM Migraciones
echo [3/5] Aplicando migraciones...
python manage.py migrate --noinput
if errorlevel 1 (
    echo  ERROR en migraciones - revisa los logs
    pause
    exit /b 1
)
echo OK
echo.

REM Collectstatic
echo [4/5] Actualizando archivos estaticos...
python manage.py collectstatic --noinput --clear
echo OK
echo.

REM Reiniciar servicio
echo [5/5] Reiniciando servicio...
nssm start %SERVICIO_NOMBRE%
timeout /t 5 >nul
nssm status %SERVICIO_NOMBRE%
echo.

echo  Actualizacion completada.
echo  URL: http://localhost:8000
echo.
pause
