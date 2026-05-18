import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("DUFFEL_API_KEY")

print(f"Testing Duffel: {key[:10]}...")
url = "https://api.duffel.com/air/airlines?limit=1"
headers = {
    "Authorization": f"Bearer {key}",
    "Duffel-Version": "2022-03-29",
}

try:
    r = requests.get(url, headers=headers, timeout=10)
    print(f"Duffel Status: {r.status_code}")
    print(f"Duffel Response: {r.text[:200]}")
except Exception as e:
    print(f"Duffel Error: {e}")
