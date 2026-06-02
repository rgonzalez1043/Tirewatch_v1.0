@echo off
setlocal EnableDelayedExpansion
title TireWatch - Instalar Servicio Windows

REM ============================================================
REM  TireWatch — instalar_servicio.bat
REM  Registra TireWatch como servicio de Windows usando NSSM.
REM  REQUISITOS:
REM    - Ejecutar como Administrador
REM    - NSSM instalado: https://nssm.cc/download
REM      Copiar nssm.exe (win64) a C:\Windows\System32\
REM    - Haber ejecutado desplegar.bat primero
REM ============================================================

set SCRIPTS_DIR=%~dp0
set PROYECTO=%SCRIPTS_DIR%..\backend
set INICIO_BAT=%SCRIPTS_DIR%iniciar.bat
set LOG_DIR=%SCRIPTS_DIR%..\logs
set SERVICIO_NOMBRE=TireWatch
set SERVICIO_DISPLAY=TireWatch - STI
set SERVICIO_DESC=TireWatch - Sistema de Control de Desgaste STI/HGT

echo.
echo  =====================================================
echo   TireWatch - Instalacion como Servicio de Windows
echo  =====================================================
echo.

REM ── Verificar Administrador ──────────────────────────────────
net session >nul 2>&1
if errorlevel 1 (
    echo  ERROR: Este script debe ejecutarse como Administrador.
    echo  Clic derecho en el archivo ^> "Ejecutar como administrador"
    pause
    exit /b 1
)

REM ── Verificar NSSM ───────────────────────────────────────────
nssm version >nul 2>&1
if errorlevel 1 (
    echo  ERROR: NSSM no encontrado.
    echo.
    echo  Descarga NSSM desde: https://nssm.cc/download
    echo  Extrae nssm.exe (version 64-bit: win64\nssm.exe)
    echo  Y coloca nssm.exe en: C:\Windows\System32\
    echo.
    pause
    exit /b 1
)
echo  NSSM: OK
echo.

REM ── Crear directorio de logs ─────────────────────────────────
if not exist "%LOG_DIR%" (
    mkdir "%LOG_DIR%"
    echo  Directorio de logs creado: %LOG_DIR%
)

REM ── Desinstalar version anterior si existe ───────────────────
nssm status %SERVICIO_NOMBRE% >nul 2>&1
if not errorlevel 1 (
    echo  Servicio existente detectado. Desinstalando version anterior...
    nssm stop %SERVICIO_NOMBRE% >nul 2>&1
    timeout /t 3 >nul
    nssm remove %SERVICIO_NOMBRE% confirm >nul 2>&1
    echo  OK - Servicio anterior eliminado.
    echo.
)

echo  Instalando servicio: %SERVICIO_NOMBRE%...
echo.

REM ── Instalar servicio ────────────────────────────────────────
REM NSSM lanza cmd.exe que ejecuta iniciar.bat
nssm install %SERVICIO_NOMBRE% "cmd.exe"
nssm set %SERVICIO_NOMBRE% AppParameters "/c ""%INICIO_BAT%"""
nssm set %SERVICIO_NOMBRE% AppDirectory "%PROYECTO%"

REM Descripcion
nssm set %SERVICIO_NOMBRE% DisplayName "%SERVICIO_DISPLAY%"
nssm set %SERVICIO_NOMBRE% Description "%SERVICIO_DESC%"

REM Inicio automatico con Windows
nssm set %SERVICIO_NOMBRE% Start SERVICE_AUTO_START

REM Logs (rotacion diaria, maximo 5 MB por archivo)
nssm set %SERVICIO_NOMBRE% AppStdout "%LOG_DIR%\tirewatch_stdout.log"
nssm set %SERVICIO_NOMBRE% AppStderr "%LOG_DIR%\tirewatch_stderr.log"
nssm set %SERVICIO_NOMBRE% AppRotateFiles 1
nssm set %SERVICIO_NOMBRE% AppRotateSeconds 86400
nssm set %SERVICIO_NOMBRE% AppRotateBytes 5242880

REM Reintentar si falla (cada 10 segundos)
nssm set %SERVICIO_NOMBRE% AppThrottle 10000
nssm set %SERVICIO_NOMBRE% AppExit Default Restart

REM ── Iniciar servicio ─────────────────────────────────────────
echo  Iniciando servicio por primera vez...
nssm start %SERVICIO_NOMBRE%
timeout /t 5 >nul

nssm status %SERVICIO_NOMBRE% | findstr /i "running" >nul
if errorlevel 1 (
    echo.
    echo  ADVERTENCIA: El servicio puede no haber iniciado correctamente.
    echo  Revisa los logs en: %LOG_DIR%
    echo  O ejecuta manualmente: scripts\iniciar.bat
) else (
    echo  Servicio corriendo correctamente.
)

echo.
echo  =====================================================
echo   Servicio instalado!
echo  =====================================================
echo.
echo  Nombre:  %SERVICIO_NOMBRE%
echo  URL:     http://[IP-DEL-SERVIDOR]:8011
echo  Logs:    %LOG_DIR%
echo.
echo  Comandos utiles (ejecutar como Administrador):
echo    nssm start   %SERVICIO_NOMBRE%   ^<-- iniciar
echo    nssm stop    %SERVICIO_NOMBRE%   ^<-- detener
echo    nssm restart %SERVICIO_NOMBRE%   ^<-- reiniciar
echo    nssm status  %SERVICIO_NOMBRE%   ^<-- ver estado
echo    nssm edit    %SERVICIO_NOMBRE%   ^<-- editar configuracion
echo.
echo  Ver logs en tiempo real:
echo    type "%LOG_DIR%\tirewatch_stdout.log"
echo.
pause
