#!/usr/bin/env bash
set -euo pipefail

# Imagen a desplegar (debe existir localmente)
IMAGE_NAME="${IMAGE_NAME:-taller_base:latest}"

# Requiere jq para procesar inspect JSON
if ! command -v jq >/dev/null 2>&1; then
  echo "❌ Se requiere 'jq' para ejecutar este script. Instálalo y vuelve a intentar."
  exit 1
fi

echo "🔍 Buscando contenedores de clientes..."
containers=$(docker ps -a --format '{{.Names}}' | grep '^cliente_' || true)

if [[ -z "${containers}" ]]; then
  echo "⚠️ No se encontraron contenedores cliente_XXXX."
  exit 0
fi

# Verifica que la imagen exista
if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "❌ La imagen '$IMAGE_NAME' no existe localmente. Construye o obtiene la imagen antes de continuar."
  exit 1
fi

for c in $containers; do
  echo "\n=============================="
  echo "🔄 Actualizando contenedor: $c"

  # Obtiene configuración actual
  inspect_json="$(docker inspect "$c")"

  # Env vars a archivo (preserva DB_*, CLIENT_*, etc.)
  env_file="/tmp/${c}_env_$$.env"
  echo "$inspect_json" | jq -r '.[0].Config.Env // [] | .[]' > "$env_file"

  # Labels a archivo (evita problemas con backticks en reglas Traefik)
  labels_file="/tmp/${c}_labels_$$.txt"
  echo "$inspect_json" | jq -r '.[0].Config.Labels // {} | to_entries | .[] | "\(.key)=\(.value)"' > "$labels_file"

  # Volúmenes bind
  BIND_FLAGS="$(echo "$inspect_json" | jq -r '.[0].HostConfig.Binds // [] | map("-v " + .) | join(" ")')"

  # Puertos publicados
  PORT_FLAGS="$(echo "$inspect_json" | jq -r '
    .[0].HostConfig.PortBindings // {} 
    | to_entries 
    | map(. as $p | ($p.value[] | "-p "
        + (if (.HostIp!=null and .HostIp!="") then .HostIp+":" else "" end)
        + (.HostPort // "") + ":" + $p.key))
    | join(" ")')"

  # Política de restart
  RESTART_NAME="$(echo "$inspect_json" | jq -r '.[0].HostConfig.RestartPolicy.Name // ""')"
  if [[ -n "$RESTART_NAME" && "$RESTART_NAME" != "no" ]]; then
    RESTART_FLAG="--restart $RESTART_NAME"
  else
    RESTART_FLAG=""
  fi

  # Redes: primaria = primera encontrada; conectar al resto luego
  PRIMARY_NET="$(echo "$inspect_json" | jq -r '.[0].NetworkSettings.Networks | keys[0] // ""')"
  if [[ -z "$PRIMARY_NET" ]]; then
    PRIMARY_NET="traefik_default"
  fi
  mapfile -t EXTRA_NETS < <(echo "$inspect_json" | jq -r --arg p "$PRIMARY_NET" '.[0].NetworkSettings.Networks | keys | map(select(. != $p)) | .[]?')

  echo "🛑 Deteniendo $c..."
  docker stop "$c" >/dev/null 2>&1 || true

  echo "🧹 Eliminando $c..."
  docker rm "$c" >/dev/null 2>&1 || true

  echo "🚀 Recreando $c con imagen: $IMAGE_NAME"
  # shellcheck disable=SC2086
  docker run -d \
    --name "$c" \
    --network "$PRIMARY_NET" \
    $RESTART_FLAG \
    --env-file "$env_file" \
    --label-file "$labels_file" \
    $BIND_FLAGS \
    $PORT_FLAGS \
    "$IMAGE_NAME" >/dev/null

  # Conectar redes adicionales (si existían)
  if [[ ${#EXTRA_NETS[@]} -gt 0 ]]; then
    for net in "${EXTRA_NETS[@]}"; do
      echo "🔗 Conectando red extra: $net"
      docker network connect "$net" "$c" >/dev/null 2>&1 || true
    done
  fi

  # Limpieza de archivos temporales
  rm -f "$env_file" "$labels_file" || true

  echo "✅ $c recreado y apuntando a la nueva imagen."
  echo "   Las migraciones y collectstatic se ejecutarán vía ENTRYPOINT al iniciar."
done

echo "\n✅ Todos los clientes fueron actualizados preservando configuración (env, labels, redes, puertos, volúmenes y restart)."
