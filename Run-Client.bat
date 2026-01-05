@echo off
setlocal
reg add HKEY_CURRENT_USER\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

title WireGuard Premium - Client
cls
echo =======================================================
echo          WIREGUARD MANAGER - PREMIUM CLIENT
echo =======================================================
echo.

cd /d "%~dp0client"

if not exist venv (
    echo [+] Estado: Creando Entorno Virtual...
    python -m venv venv
)

echo [+] Estado: Activando Entorno Virtual...
call venv\Scripts\activate.bat

echo [+] Estado: Verificando Dependencias...
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

echo.
echo [OK] Iniciando Cliente...
echo -------------------------------------------------------
python main.py
pause
