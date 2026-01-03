#!/bin/bash

# Script para instalar el backend como un servicio de sistema (Systemd)
# Esto garantiza que el servidor corra siempre, incluso después de reiniciar o cerrar sesión.

APP_NAME="wg-premium-backend"
USER_NAME=$(whoami)
CUR_DIR=$(pwd)
VENV_BIN="$CUR_DIR/venv/bin/python"
UVICORN_BIN="$CUR_DIR/venv/bin/uvicorn"

echo "🛠️ Creando servicio de sistema para $APP_NAME..."

SERVICE_FILE="[Unit]
Description=Gunicorn instance to serve WG Premium Backend
After=network.target

[Service]
User=$USER_NAME
Group=www-data
WorkingDirectory=$CUR_DIR
Environment=\"PATH=$CUR_DIR/venv/bin\"
ExecStart=$UVICORN_BIN app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target"

# Escribir el archivo temporalmente
echo "$SERVICE_FILE" > $APP_NAME.service

# Mover a systemd y habilitar
sudo mv $APP_NAME.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $APP_NAME
sudo systemctl start $APP_NAME

echo "🚀 El servicio se ha instalado y activado correctamente."
echo "Para ver el estado: sudo systemctl status $APP_NAME"
echo "Para ver los logs: journalctl -u $APP_NAME -f"
