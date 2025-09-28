#!/usr/bin/env python3
import subprocess
import sys
import os
import secrets
import string

# Configuración
BASE_IMAGE = "taller_base:latest"
BASE_APP_PATH = "/home/max/baseapp"   # directorio donde está tu Dockerfile base

#DOMAIN = "netgogo.cl"
DOMAIN = "94.72.119.222"

CLIENTS_DIR = "/home/max/clientes"    # donde guardaremos datos persistentes de cada cliente

def run(cmd):
    print(f"👉 Ejecutando: {cmd}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        sys.exit(1)
    return result.stdout.strip()

def build_base_image():
    print("⚙️ Construyendo imagen base...")
    run(f"docker build -t {BASE_IMAGE} {BASE_APP_PATH}")

def image_exists(image):
    result = subprocess.run(f"docker images -q {image}", shell=True, capture_output=True, text=True)
    return bool(result.stdout.strip())

def generate_password(length=12):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def alta_cliente(nombre_cliente):
    # 1. Verificar si existe la imagen base
    if not image_exists(BASE_IMAGE):
        build_base_image()

    # 2. Crear directorio para datos persistentes
    client_dir = os.path.join(CLIENTS_DIR, nombre_cliente)
    os.makedirs(client_dir, exist_ok=True)

    # 3. Generar subdominio
    subdomain = f"{nombre_cliente}.{DOMAIN}"

    # 4. Generar contraseña segura
    password = generate_password()

    # 5. Crear contenedor
    container_name = f"cliente_{nombre_cliente}"
    port = "8" + str(secrets.randbelow(9000)).zfill(3)  # ejemplo: puerto 8123-8999

    run(f"docker run -d --name {container_name} "
        f"-p {port}:8000 "
        f"-v {client_dir}:/app/media "
        f"{BASE_IMAGE}")

    print("\n✅ Cliente creado con éxito:")
    print(f"   Nombre: {nombre_cliente}")
    print(f"   Subdominio: http://{subdomain}:{port}")
    print(f"   Usuario admin: admin")
    print(f"   Contraseña: {password}")
    print(f"   Contenedor: {container_name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: alta_cliente.py NOMBRE_CLIENTE")
        sys.exit(1)

    nombre_cliente = sys.argv[1]
    alta_cliente(nombre_cliente)
