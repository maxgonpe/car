import requests

API_KEY = "b790d4f0874111f08d1e0242ac120002"
VIN = "5FNYF4850CB601404"  # VIN de ejemplo de la documentación

url = f"https://api.vehicledatabases.com/vin-decode/{VIN}"

headers = {
    "x-AuthKey": API_KEY
}

response = requests.get(url, headers=headers)

print("HTTP Status:", response.status_code)
print("Respuesta cruda:", response.text)

try:
    data = response.json()
    if data.get("status") == "success":
        print("✅ Conexión exitosa, clave válida y VIN decodificado")
        print("Marca:", data["data"]["basic"]["make"])
        print("Modelo:", data["data"]["basic"]["model"])
        print("Año:", data["data"]["basic"]["year"])
    else:
        print("⚠️ La API respondió con error:", data)
except Exception as e:
    print("⚠️ No se pudo parsear JSON:", e)
