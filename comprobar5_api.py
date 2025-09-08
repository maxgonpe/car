import requests

# Usa la URL de SANDBOX, no la de producción
url = "https://api.vehicledatabases.com/auction/1HGCM82633A004352"  # VIN de prueba si lo da la doc

headers = {
    "x-AuthKey": "b790d4f0874111f08d1e0242ac120002"
}

response = requests.get(url, headers=headers)

print(response.status_code)
print(response.text)
