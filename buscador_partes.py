import requests

# Configuración
VIN = "1C4NJPBA4FD399353"   # Ejemplo Jeep
API_KEY_VINDECODER = "TU_API_KEY"  # (pide registro gratis en vindecodervehicle.com)
USER_VINDECODER = "TU_USER"

def get_from_vindecoder(vin: str):
    """Consulta VINDecoderVehicle.com"""
    try:
        url = f"https://vindecodervehicle.com/api/?user={USER_VINDECODER}&key={API_KEY_VINDECODER}&vin={vin}"
        r = requests.get(url, timeout=10)
        data = r.json()

        if "carId" not in data:
            return None

        car_id = data["carId"]
        url_parts = f"https://vindecodervehicle.com/api/?user={USER_VINDECODER}&key={API_KEY_VINDECODER}&carId={car_id}&oemParts=1"
        r2 = requests.get(url_parts, timeout=15)
        return r2.json()
    except Exception as e:
        print(f"[VINDecoder] Error: {e}")
        return None


def get_from_17vin(vin: str):
    """Consulta 17vin.com (ejemplo simulando endpoint público)"""
    try:
        url = f"https://api.17vin.com/vindecoder?vin={vin}&apikey=TU_API_KEY"
        r = requests.get(url, timeout=10)
        return r.json()
    except Exception as e:
        print(f"[17vin] Error: {e}")
        return None


def get_oem_parts(vin: str):
    """Intentar con varias fuentes (fallback)"""
    print(f"🔎 Buscando partes OEM para VIN {vin}...")

    data = get_from_vindecoder(vin)
    if data and "data" in data:
        print("✅ Datos obtenidos desde VINDecoderVehicle")
        return data["data"]

    data = get_from_17vin(vin)
    if data and "oemParts" in data:
        print("✅ Datos obtenidos desde 17vin.com")
        return data["oemParts"]

    print("❌ No se encontraron datos en ninguna API")
    return None


if __name__ == "__main__":
    parts = get_oem_parts(VIN)
    if parts:
        for p in parts[:10]:  # Mostrar solo los primeros 10 resultados
            print(f"- {p}")
    else:
        print("No se pudieron obtener partes OEM para este VIN.")
