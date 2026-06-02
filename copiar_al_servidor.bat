@echo off
setlocal
title TireWatch - Copiar al Servidor

REM ============================================================
REM  TireWatch — copiar_al_servidor.bat
REM  Copia el codigo fuente al servidor via red compartida.
REM  Ejecutar desde la maquina de DESARROLLO.
REM  El servidor debe tener acceso compartido habilitado.
REM ============================================================

REM -- Ajusta el destino segun tu servidor --
set ORIGEN=C:\1.-Proyectos\tirewatch
set DESTINO=\\NOMBRE-SERVIDOR\TireWatch
REM Ejemplo con IP: set DESTINO=\\192.168.1.50\c$\TireWatch

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

REM Copiar TODO el proyecto (sin venv, cache ni archivos sensibles)
robocopy "%ORIGEN%" "%DESTINO%" /MIR ^
    /XD venv __pycache__ staticfiles media .git .pytest_cache env ^
    /XF "*.pyc" "*.pyo" ".env" "db.sqlite3" "*.log" ^
    /LOG:"%TEMP%\tirewatch_copia.log" ^
    /NP /NFL /NDL

if errorlevel 8 (
    echo.
    echo  ERROR: La copia fallo. Revisa la conexion al servidor.
    echo  Log detallado: %TEMP%\tirewatch_copia.log
) else (
    echo.
    echo  Copia completada exitosamente.
    echo.
    echo  Proximos pasos en el SERVIDOR (primera vez):
    echo    1. Abre la carpeta %DESTINO%\scripts\
    echo    2. Ejecuta  desplegar.bat
    echo    3. Luego ejecuta  instalar_servicio.bat  (como Administrador)
    echo.
    echo  Si ya esta instalado (actualizacion):
    echo    Ejecuta  scripts\actualizar.bat  (como Administrador)
)
echo.
pause
