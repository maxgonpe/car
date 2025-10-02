#!/bin/bash
set -e

IMAGE_NAME="taller_base:latest"

echo "🔍 Buscando contenedores de clientes..."
containers=$(docker ps -a --format '{{.Names}}' | grep '^cliente_' || true)

if [ -z "$containers" ]; then
  echo "⚠️ No se encontraron contenedores cliente_XXXX."
  exit 0
fi

for c in $containers; do
  echo "🛑 Deteniendo y eliminando $c..."
  docker stop $c || true
  docker rm $c || true

  echo "🚀 Lanzando de nuevo $c con la nueva imagen..."
  docker run -d --name $c --network traefik_default $IMAGE_NAME
done

echo "✅ Todos los clientes fueron actualizados con la nueva imagen."
