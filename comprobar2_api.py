import requests
import time

# Configuración
VIN = "8X7F1B113CD002984"  # Cambia por el VIN que quieras probar
API_KEY = "b790d4f0874111f08d1e0242ac120002"  # Tu clave real
MAX_INTENTOS = 6  # Intentos máximos (6 min si esperas 60s entre cada uno)
ESPERA_SEGUNDOS = 60  # Tiempo de espera entre cada intento

def comprobar_api():
    url = f"https://api.vehicledatabases.com/auction/{VIN}"
    headers = {"x-AuthKey": API_KEY}

    for intento in range(1, MAX_INTENTOS + 1):
        print(f"\n🔎 Intento {intento}/{MAX_INTENTOS}...")
        try:
            response = requests.get(url, headers=headers, timeout=15)

            if response.status_code == 200:
                print("✅ Conexión exitosa")
                print("Respuesta de la API:")
                print(response.json())
                return

            elif response.status_code == 401:
                print("❌ Error: Clave API inválida o no autorizada.")
                return

            elif response.status_code == 404:
                print("❌ VIN no encontrado en la base de datos.")
                return

            elif response.status_code == 400:
                msg = response.json()
                print(f"⚠️ Aún no hay datos para este VIN. Mensaje: {msg}")
                if intento < MAX_INTENTOS:
                    print(f"⏳ Esperando {ESPERA_SEGUNDOS} segundos antes de reintentar...")
                    time.sleep(ESPERA_SEGUNDOS)
                else:
                    print("❌ Se alcanzó el número máximo de intentos. Intenta más tarde.")
                    return

            else:
                print(f"⚠️ Error desconocido. Código HTTP: {response.status_code}")
                print("Respuesta:", response.text)
                return

        except requests.exceptions.RequestException as e:
            print("❌ Error de conexión:", e)
            return

if __name__ == "__main__":
    comprobar_api()
