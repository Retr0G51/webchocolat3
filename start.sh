#!/bin/bash

# Script de inicio para Railway
echo "🚀 Iniciando Chocolates ByB..."

# Verificar variables de entorno críticas
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  DATABASE_URL no está configurada, usando SQLite local"
fi

if [ -z "$SECRET_KEY" ]; then
    echo "⚠️  SECRET_KEY no está configurada, usando clave por defecto"
fi

echo "🔧 Configuración:"
echo "   - Puerto: ${PORT:-5000}"
echo "   - Entorno: ${FLASK_ENV:-production}"

# Iniciar la aplicación con gunicorn
echo "▶️  Iniciando servidor..."
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers 1 --timeout 300 --keep-alive 2 --max-requests 1000 --preload app:app
