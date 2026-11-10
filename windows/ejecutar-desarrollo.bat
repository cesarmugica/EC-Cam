@echo off
rem Ejecuta EC-Cam desde el c?digo (sin instalar). Requiere Python 3.12 y FFmpeg en el PATH.
cd /d "%~dp0.."
python eccam_server.py %*
pause
