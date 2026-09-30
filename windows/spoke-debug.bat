@echo off
REM Abre Spoke con consola y mensajes de depuración.
cd /d "%~dp0"
set SPOKE_DEBUG=1
".venv\Scripts\python.exe" -m spoke
pause
