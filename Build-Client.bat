@echo off
setlocal
title WireGuard Premium - Compiler
cls
echo =======================================================
echo          WIREGUARD PREMIUM - CLIENT COMPILER
echo =======================================================
echo.

cd /d "%~dp0client"

if not exist venv (
    echo [+] Estado: Creando Entorno Virtual...
    python -m venv venv
)

echo [+] Estado: Activando Entorno Virtual...
call venv\Scripts\activate.bat

echo [+] Estado: Verificando Herramientas de Compilacion...
python -m pip install -q --upgrade pip
pip install -q flet PyInstaller requests Pillow cryptography pystray

echo.
echo [+] Estado: Iniciando proceso de Compilacion (PyInstaller)...
echo     (Esto puede tardar un par de minutos, por favor espere...)
echo -------------------------------------------------------

:: Ejecutar el comando de empaquetado de Flet
flet pack main.py --icon assets/icon.ico --name "WireGuardPremiumClient" --add-data "assets;assets"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo -------------------------------------------------------
    echo [OK] COMPILACION COMPLETADA CON EXITO
    echo.
    echo El archivo ejecutable se encuentra en:
    echo %~dp0client\dist\WireGuardPremiumClient.exe
    echo -------------------------------------------------------
) else (
    echo.
    echo [!] ERROR: La compilación ha fallado.
    echo Revise los mensajes superiores para mas detalles.
)

echo.
pause
