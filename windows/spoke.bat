@echo off
REM Abre Spoke (sin ventana de consola). Usa spoke-debug.bat para ver los mensajes.
cd /d "%~dp0"
start "" ".venv\Scripts\pythonw.exe" -m spoke
