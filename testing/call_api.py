import requests

BASE_URL = "http://127.0.0.1:5000"

payload = {"query":"What is the capitol of Wales, and how long does it take to get there from "}
response = requests.post(f"{BASE_URL}/query", json=payload)
print(response.json())