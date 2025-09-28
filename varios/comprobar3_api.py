import requests
import time
import json

# --- Configuración ---
SANDBOX = True  # Cambiar a False para producción
VIN = "1C4NJPBA4FD399353"  # VIN de ejemplo, cámbialo por el que quieras probar

# URL base según sandbox o producción
if SANDBOX:
    BASE_URL = "https://sandbox.api.vehicledatabases.com/auction"
    API_KEY = "b790d4f0874111f08d1e0242ac12"   # ← pon aquí la clave del sandbox
else:
    BASE_URL = "https://api.vehicledatabases.com/auction"
    API_KEY = "b790d4f0874111f08d1e0242ac120002"      # ← pon aquí la clave real de producción

url = f"{BASE_URL}/{VIN}"
headers = {
    "x-AuthKey": API_KEY
}

print(f"🔍 Consultando VIN {VIN} en {'sandbox' if SANDBOX else 'producción'}...")

# Intentar varias veces por si aún no se sincroniza el VIN
for intento in range(5):  # máximo 5 intentos
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("✅ Conexión exitosa")
        try:
            data = response.json()
            print("📦 Respuesta procesada:")
            print(json.dumps(data, indent=4))
        except Exception as e:
            print("⚠️ No se pudo parsear JSON:", e)
        break

    elif response.status_code == 401:
        print("❌ Clave API inválida o no autorizada.")
        break

    elif response.status_code == 404:
        print("❌ VIN no encontrado en la base de datos.")
        break

    elif response.status_code == 400:
        print(f"⚠️ Error 400: {response.text}")
        print("⏳ Reintentando en 60 segundos...")
        time.sleep(60)  # esperar antes de reintentar
    else:
        print(f"⚠️ Error desconocido. Código HTTP: {response.status_code}")
        print("Respuesta:", response.text)
        break
