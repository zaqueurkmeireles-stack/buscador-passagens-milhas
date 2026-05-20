import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GOOGLE_GEMINI_API_KEY")

print(f"Testing v1 version with key: {key[:10]}...")
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key={key}"
json_data = {"contents": [{"parts": [{"text": "Ping"}]}]}

try:
    r = requests.post(url, json=json_data, timeout=10)
    print(f"v1 Status: {r.status_code}")
    print(f"v1 Response: {r.text}")
except Exception as e:
    print(f"v1 Error: {e}")
