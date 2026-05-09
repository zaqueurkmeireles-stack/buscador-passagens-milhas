import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Use PostgREST OpenAPI spec to find tables
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

try:
    r = requests.get(f"{url}/rest/v1/", headers=headers)
    if r.status_code == 200:
        spec = r.json()
        print("Tables found in OpenAPI spec:")
        for path in spec.get("paths", {}):
            if path.startswith("/"):
                print(path[1:])
    else:
        print(f"Failed to get spec: {r.status_code}")
        print(r.text)
except Exception as e:
    print(f"Error: {e}")
