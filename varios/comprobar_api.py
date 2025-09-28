import requests

def consultar_vehiculo(vin, api_key):
    url = f"https://api.vehicledatabases.com/auction/{vin}"
    headers = {
        "x-AuthKey": api_key
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)

        # Verificar si el servidor respondió
        if response.status_code == 200:
            data = response.json()
            print("✅ Conexión exitosa con la API.")
            
            # Verificamos si viene información del vehículo
            if data:
                print("🔎 VIN encontrado y procesado correctamente.")
                return data
            else:
                print("⚠️ La API respondió pero no devolvió datos del vehículo.")
                return None

        elif response.status_code == 401:
            print("❌ Error: API Key inválida o no autorizada.")
        elif response.status_code == 404:
            print("❌ Error: VIN no encontrado o inválido.")
        elif response.status_code == 429:
            print("⚠️ Límite de consultas alcanzado. Intenta más tarde.")
        else:
            print(f"⚠️ Error desconocido. Código HTTP: {response.status_code}")
            print("Respuesta:", response.text)

    except requests.exceptions.Timeout:
        print("⏳ Error: Tiempo de espera agotado al conectar con la API.")
    except requests.exceptions.ConnectionError:
        print("🌐 Error: No se pudo establecer conexión con la API.")
    except Exception as e:
        print("⚠️ Error inesperado:", str(e))


# ----------------------------
# USO DEL SCRIPT
# ----------------------------
if __name__ == "__main__":
    VIN = "1C4NJPBA4FD399353"   # Ejemplo de VIN
    API_KEY = "b790d4f0874111f08d1e0242ac120002" # Reemplázala con tu clave real

    datos = consultar_vehiculo(VIN, API_KEY)
    
    if datos:
        print("\n📋 Datos recibidos:")
        print(datos)
