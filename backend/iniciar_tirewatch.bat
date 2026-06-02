@echo off
REM ============================================================
REM  TireWatch — Script de inicio del servidor
REM  NSSM ejecuta este archivo como servicio de Windows
REM ============================================================

REM Ir al directorio del proyecto (ajusta si instalas en otra ruta)
cd /d "C:\TireWatch\backend"

REM Cargar variables de entorno desde .env
for /f "usebackq tokens=* eol=#" %%a in (".env") do set "%%a"

REM Activar entorno virtual
call venv\Scripts\activate.bat

REM Iniciar servidor Waitress (WSGI para Windows)
REM --host=0.0.0.0  : acepta conexiones de la red local
REM --port=8000     : cambia si necesitas otro puerto
REM --threads=4     : conexiones paralelas (ajusta segun CPU del servidor)
echo Iniciando TireWatch en puerto 8011...
python -m waitress --host=0.0.0.0 --port=8011 --threads=4 tirewatch.wsgi:application
