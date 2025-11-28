@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python no encontrado. Instala Python 3.10+ y vuelve a intentar.
    pause
    exit /b 1
  )
)

if not exist ".venv" (
  echo Creando entorno virtual...
  py -m venv .venv 2>nul
  if errorlevel 1 (
    python -m venv .venv
  )
)
call ".venv\Scripts\activate.bat"

if exist ".env" (
  for /f "usebackq tokens=1,2 delims==" %%A in (".env") do (
    set "%%A=%%B"
  )
)

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo AVISO: FFmpeg no encontrado en PATH. Instala FFmpeg para reproducir audio.
  echo Descarga: https://www.gyan.dev/ffmpeg/builds/
)

if not defined DISCORD_TOKEN (
  echo Falta DISCORD_TOKEN. Introduce el token ahora.
  set /p DISCORD_TOKEN=DISCORD_TOKEN:
)

if not defined LICENSE_SECRET (
  echo AVISO: LICENSE_SECRET no configurado. La activacion de licencias no funcionara.
)

if not exist "logs" mkdir logs
powershell -NoProfile -Command "$p='logs\\atenea.log'; if(Test-Path $p){ $s=(Get-Item $p).Length; if($s -gt 5242880){ $ts=Get-Date -Format 'yyyyMMdd_HHmmss'; Move-Item $p \"logs\\atenea_$ts.log\" } }"
echo ===== Inicio %date% %time% =====>> logs\atenea.log

python -m pip install -r requirements.txt

:loop
".venv\Scripts\python.exe" bot.py >> logs\atenea.log 2>&1
if errorlevel 1 (
  echo Bot detenido. Reiniciando en 5 segundos...>> logs\atenea.log
  timeout /t 5 /nobreak >nul
  goto loop
)
echo Bot finalizado correctamente.>> logs\atenea.log
pause
