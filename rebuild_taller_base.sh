#!/bin/bash
set -e  # Si algo falla, se detiene

# === Configuración ===
PROJECT_DIR="/home/max/myproject"
IMAGE_NAME="taller_base:latest"

echo "🚀 Iniciando rebuild del taller base..."
cd $PROJECT_DIR

echo "🔄 Aplicando migraciones..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

echo "📦 Recolectando archivos estáticos..."
python3 manage.py collectstatic --noinput

echo "🐳 Reconstruyendo imagen Docker: $IMAGE_NAME"
docker build -t $IMAGE_NAME .

echo "✅ Imagen $IMAGE_NAME reconstruida correctamente."
