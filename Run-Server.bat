@echo off
setlocal
:: Habilitar colores ANSI en CMD si es posible
reg add HKEY_CURRENT_USER\Console /v VirtualTerminalLevel /t REG_DWORD /d 1 /f >nul 2>&1

title WireGuard Manager - Backend Server
cls
echo =======================================================
echo          WIREGUARD MANAGER - BACKEND SERVER
echo =======================================================
echo.

cd /d "%~dp0backend"

if not exist venv (
    echo [+] Estado: Creando Entorno Virtual...
    python -m venv venv
)

echo [+] Estado: Activando Entorno Virtual...
call venv\Scripts\activate.bat

echo [+] Estado: Verificando Dependencias...
python -m pip install -q --upgrade pip
pip install -q -r requirements.txt

if not exist wireguard_manager.db (
    echo [!] Aviso: Base de datos no encontrada. Inicializando datos...
    python seed.py
)

echo.
echo [OK] Servidor listo para peticiones...
echo -------------------------------------------------------
echo  SISTEMA DE ADMINISTRACION (Web Admin):
echo  URL: http://localhost:8000/admin-ui/index.html
echo  Usuario: admin
echo  Password: admin123
echo -------------------------------------------------------
echo.
:: Usar --no-use-colors para evitar los caracteres raros en algunos CMD
uvicorn app.main:app --host 127.0.0.1 --port 8000 --no-use-colors
pause
