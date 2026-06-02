@echo off
REM ============================================================
REM  TireWatch — iniciar.bat
REM  Este script es ejecutado por NSSM como servicio de Windows.
REM  NO ejecutar manualmente para desarrollo; usa manage.py runserver.
REM ============================================================

REM Directorio de este script (scripts\)
set SCRIPTS_DIR=%~dp0

REM Directorio de la aplicacion Django (un nivel arriba, en backend\)
set PROYECTO=%SCRIPTS_DIR%..\backend

cd /d "%PROYECTO%"

REM ── Cargar variables de entorno desde .env ──────────────────
REM Se ignoran lineas en blanco y comentarios (#)
for /f "usebackq tokens=* eol=#" %%a in (".env") do (
    set "%%a"
)

REM ── Activar entorno virtual ──────────────────────────────────
call "%PROYECTO%\venv\Scripts\activate.bat"

REM ── Iniciar servidor Waitress (WSGI para Windows) ────────────
REM  --host=0.0.0.0   acepta conexiones de toda la red local
REM  --port=8011      puerto de produccion
REM  --threads=4      conexiones paralelas (ajusta segun CPU)
echo Iniciando TireWatch en puerto 8011...
python -m waitress --host=0.0.0.0 --port=8011 --threads=4 tirewatch.wsgi:application
