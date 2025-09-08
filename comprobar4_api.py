import requests 
url = "https://api.vehicledatabases.com/auction/8X7F1B113CD002984"
payload={}
headers = {
'x-AuthKey': 'b790d4f0874111f08d1e0242ac120002'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)