@echo off
REM Uso: transcribir.bat reunion.mp4 [idioma]   ->  reunion.txt y reunion.srt
if "%~1"=="" (echo Uso: transcribir.bat archivo [idioma] & exit /b 1)
cd /d "%~dp0"
".venv\Scripts\python.exe" -m spoke --transcribe "%~1" %2
