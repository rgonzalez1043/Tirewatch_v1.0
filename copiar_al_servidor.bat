@echo off
setlocal
title TireWatch - Copiar al Servidor

REM ============================================================
REM  Copia el codigo fuente al servidor (sin venv, sin cache)
REM  Ejecutar desde la maquina de DESARROLLO
REM ============================================================

REM -- Ajusta estas rutas --
set ORIGEN=C:\1.-Proyectos\tirewatch\backend
set DESTINO=\\NOMBRE-SERVIDOR\TireWatch\backend
REM Ejemplo con IP: set DESTINO=\\192.168.1.50\c$\TireWatch\backend

echo.
echo  =====================================================
echo   TireWatch - Copiar codigo al servidor
echo  =====================================================
echo.
echo  Origen:  %ORIGEN%
echo  Destino: %DESTINO%
echo.
set /p CONFIRMAR=Continuar? (S/N):
if /i not "%CONFIRMAR%"=="S" exit /b 0
echo.

REM Usar robocopy para copiar SOLO el codigo fuente
REM /MIR = Mirror (copia y elimina archivos borrados)
REM /XD  = Exclude Directories
REM /XF  = Exclude Files
robocopy "%ORIGEN%" "%DESTINO%" /MIR ^
    /XD venv __pycache__ staticfiles media .git .pytest_cache ^
    /XF "*.pyc" "*.pyo" ".env" "db.sqlite3" "*.log" ^
    /LOG:"%TEMP%\tirewatch_copia.log" ^
    /NP /NFL /NDL

if errorlevel 8 (
    echo.
    echo  ERROR: La copia fallo. Revisa la conexion al servidor.
    echo  Log: %TEMP%\tirewatch_copia.log
) else (
    echo.
    echo  Copia completada exitosamente.
    echo.
    echo  Proximos pasos en el SERVIDOR:
    echo    1. Abre C:\TireWatch\backend\
    echo    2. Ejecuta  desplegar.bat  (primera vez)
    echo    3. O ejecuta  actualizar.bat  (si ya estaba instalado)
)
echo.
pause
