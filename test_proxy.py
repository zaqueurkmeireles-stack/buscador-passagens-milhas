import requests
import os
from dotenv import load_dotenv

load_dotenv()

proxy_url = os.getenv("PROXY_URL")
print(f"Testando proxy: {proxy_url[:30]}...")

proxies = {
    "http": proxy_url,
    "https": proxy_url
}

try:
    r = requests.get("https://httpbin.org/ip", proxies=proxies, timeout=15)
    print(f"Sucesso! IP retornado: {r.json()}")
except Exception as e:
    print(f"Erro no proxy: {e}")
