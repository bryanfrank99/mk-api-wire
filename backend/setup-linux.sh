#!/bin/bash

# Script de configuración para el servidor en Linux
# Este script instala las dependencias y prepara la base de datos

echo "🚀 Iniciando configuración del servidor WG Premium..."

# 1. Actualizar sistema y dependencias de Python
echo "📦 Instalando dependencias de sistema..."
sudo apt update
sudo apt install -y python3-venv python3-pip sqlite3

# 2. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "🐍 Creando entorno virtual..."
    python3 -m venv venv
else
    echo "✅ El entorno virtual ya existe."
fi

# 3. Activar y actualizar pip
source venv/bin/activate
pip install --upgrade pip

# 4. Instalar librerías de Python
echo "📚 Instalando requerimientos..."
pip install -r requirements.txt

# 5. Inicializar/Migrar base de datos
if [ ! -f "wireguard_manager.db" ]; then
    echo "🗄️ Inicializando base de datos y datos de prueba..."
    python3 migrate_db.py
    python3 seed.py
else
    echo "✅ La base de datos ya existe."
fi

echo "✨ Configuración completada."
echo "Puedes iniciar el servidor con: ./run-linux.sh"
chmod +x run-linux.sh
