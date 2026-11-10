@echo off
rem Crea o restablece usuarios de EC-Cam desde la PC servidor.
rem   crear-usuario.bat NOMBRE          -> crea un usuario visor (admin si es el primero)
rem   crear-usuario.bat NOMBRE admin    -> crea un administrador
setlocal
set EXE=%LOCALAPPDATA%\Programs\EC-Cam\eccam-server.exe
if "%~1"=="" ( echo Uso: crear-usuario.bat NOMBRE [admin^|viewer] & exit /b 1 )
if not exist "%EXE%" ( cd /d "%~dp0.." & set EXE=python eccam_server.py )
if "%~2"=="" ( %EXE% --add-user %1 ) else ( %EXE% --add-user %1 --role %2 )
pause
