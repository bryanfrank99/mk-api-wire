#!/bin/bash

# Script de actualización automática (Always-On)
# Uso: ./update-system.sh

APP_SERVICE="wg-premium-backend"
echo "=============================================="
echo "   WIREGUARD MANAGER - ACTUALIZADOR SISTEMA   "
echo "=============================================="
echo "Iniciado: $(date)"

# Asegurar que estamos en el directorio correcto
cd "$(dirname "$0")"

echo "[1/6] Deteniendo servicio..."
if systemctl is-active --quiet $APP_SERVICE; then
    sudo systemctl stop $APP_SERVICE
    echo " -> Servicio detenido."
else
    echo " -> El servicio no estaba corriendo."
fi

echo "[2/6] Actualizando repositorio GIT..."
# Guardar cambios locales si existen para evitar conflictos
git stash
git pull origin main || git pull origin master

echo "[3/6] Actualizando dependencias Python..."
if [ -d "venv" ]; then
    source venv/bin/activate
    pip install -r requirements.txt
else
    echo "ERROR: Entorno virtual no encontrado!"
    exit 1
fi

echo "[4/6] Aplicando migraciones de base de datos..."
python migrate_db.py

echo "[5/6] Reiniciando servicio..."
sudo systemctl start $APP_SERVICE

echo "[6/6] Verificando estado..."
sleep 2
if systemctl is-active --quiet $APP_SERVICE; then
    echo "✅ EXITOSO: El sistema se ha actualizado y está corriendo."
else
    echo "❌ ERROR: El servicio no se pudo iniciar. Revisa los logs con: journalctl -u $APP_SERVICE -e"
fi

echo "=============================================="
