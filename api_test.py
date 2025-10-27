import requests

data = {
    "key": "DEFAULT-KEY-123",
    "ip": "111.11.111.111",
    "params": {"owner": "0"}
}

r = requests.post("http://178.63.206.189:8000/command", json=data)
print(data)
print("")
print(r.text)  
