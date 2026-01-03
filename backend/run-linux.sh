#!/bin/bash

# Script para ejecutar el servidor backend en Linux
# Uso: ./run-linux.sh

source venv/bin/activate

echo "🔥 Iniciando servidor en puerto 8000..."
# Ejecutamos con uvicorn apuntando a la IP 0.0.0.0 para acceso externo
uvicorn app.main:app --host 0.0.0.0 --port 8000
