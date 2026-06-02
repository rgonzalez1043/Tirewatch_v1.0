@echo off
setlocal EnableDelayedExpansion
title TireWatch - Instalar Servicio Windows

REM ============================================================
REM  Configuracion — ajusta estos valores si es necesario
REM ============================================================
set PROYECTO=%~dp0
set SERVICIO_NOMBRE=TireWatch
set SERVICIO_DESC=TireWatch - Sistema de Control de Desgaste STI
set INICIO_BAT=%PROYECTO%iniciar_tirewatch.bat
set LOG_DIR=C:\TireWatch\logs

REM ============================================================

echo.
echo  =====================================================
echo   TireWatch - Instalacion como Servicio de Windows
echo  =====================================================
echo.

REM Verificar que se ejecuta como Administrador
net session >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Este script debe ejecutarse como Administrador.
    echo  Clic derecho en el archivo ^> "Ejecutar como administrador"
    pause
    exit /b 1
)

REM Verificar NSSM
nssm version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: NSSM no encontrado.
    echo.
    echo  Descarga NSSM desde: https://nssm.cc/download
    echo  Extrae nssm.exe (la version de 64 bits: win64\nssm.exe)
    echo  Y coloca nssm.exe en:  C:\Windows\System32\
    echo.
    pause
    exit /b 1
)
echo NSSM encontrado: OK
echo.

REM Crear directorio de logs
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo Directorio de logs creado: %LOG_DIR%
)

REM Detener y desinstalar si ya existe (para reinstalar limpiamente)
nssm status %SERVICIO_NOMBRE% >nul 2>&1
if not errorlevel 1 (
    echo Servicio existente detectado. Desinstalando version anterior...
    nssm stop %SERVICIO_NOMBRE% >nul 2>&1
    timeout /t 3 >nul
    nssm remove %SERVICIO_NOMBRE% confirm >nul 2>&1
    echo OK
)

echo Instalando servicio: %SERVICIO_NOMBRE%...
echo.

REM NSSM ejecuta cmd.exe que corre el bat de inicio
REM (el bat carga .env y lanza Waitress)
nssm install %SERVICIO_NOMBRE% "cmd.exe"
nssm set %SERVICIO_NOMBRE% AppParameters "/c ""%INICIO_BAT%"""
nssm set %SERVICIO_NOMBRE% AppDirectory "%PROYECTO%"

REM Descripcion del servicio
nssm set %SERVICIO_NOMBRE% DisplayName "TireWatch - STI"
nssm set %SERVICIO_NOMBRE% Description "%SERVICIO_DESC%"

REM Inicio automatico con Windows
nssm set %SERVICIO_NOMBRE% Start SERVICE_AUTO_START

REM Logs de salida y error
nssm set %SERVICIO_NOMBRE% AppStdout "%LOG_DIR%\tirewatch_stdout.log"
nssm set %SERVICIO_NOMBRE% AppStderr "%LOG_DIR%\tirewatch_stderr.log"
nssm set %SERVICIO_NOMBRE% AppRotateFiles 1
nssm set %SERVICIO_NOMBRE% AppRotateSeconds 86400
nssm set %SERVICIO_NOMBRE% AppRotateBytes 5242880

REM Reintentar automaticamente si falla (cada 10 segundos, hasta 3 veces)
nssm set %SERVICIO_NOMBRE% AppThrottle 10000
nssm set %SERVICIO_NOMBRE% AppExit Default Restart

echo.
echo Iniciando servicio por primera vez...
nssm start %SERVICIO_NOMBRE%
timeout /t 5 >nul

REM Verificar que inicio correctamente
nssm status %SERVICIO_NOMBRE% | findstr /i "running" >nul
if errorlevel 1 (
    echo.
    echo  ADVERTENCIA: El servicio puede no haber iniciado correctamente.
    echo  Revisa los logs en: %LOG_DIR%
    echo  O ejecuta manualmente: iniciar_tirewatch.bat
) else (
    echo  Servicio corriendo correctamente.
)

echo.
echo  =====================================================
echo   Servicio instalado!
echo  =====================================================
echo.
echo  Nombre:    %SERVICIO_NOMBRE%
echo  URL:       http://[IP-DEL-SERVIDOR]:8000
echo  Logs:      %LOG_DIR%
echo.
echo  Comandos utiles (ejecutar como Administrador):
echo    nssm start   %SERVICIO_NOMBRE%    <- iniciar
echo    nssm stop    %SERVICIO_NOMBRE%    <- detener
echo    nssm restart %SERVICIO_NOMBRE%    <- reiniciar
echo    nssm status  %SERVICIO_NOMBRE%    <- ver estado
echo    nssm edit    %SERVICIO_NOMBRE%    <- ver/editar configuracion
echo.
echo  Para ver logs en tiempo real:
echo    type "%LOG_DIR%\tirewatch_stdout.log"
echo.
pause
