import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_endpoint(name, url, headers=None, params=None, method="GET", json_data=None):
    try:
        if method == "POST":
            r = requests.post(url, headers=headers, json=json_data, timeout=10)
        else:
            r = requests.get(url, headers=headers, params=params, timeout=10)
            
        if r.status_code in (200, 201) or (name == "Anthropic" and r.status_code == 400):
            print(f"[VALIDA] {name}")
        else:
            print(f"[INVALIDA] {name} - Status {r.status_code}")
    except Exception as e:
        print(f"[ERRO DE REDE] {name} - {str(e)[:30]}")

print("\n--- INICIANDO VALIDACAO DE APIs CORE ---")

if os.getenv("TELEGRAM_BOT_TOKEN"):
    test_endpoint("Telegram Bot", f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/getMe")

if os.getenv("OPENAI_API_KEY"):
    test_endpoint("OpenAI", "https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"})

if os.getenv("GOOGLE_GEMINI_API_KEY"):
    test_endpoint("Google Gemini", f"https://generativelanguage.googleapis.com/v1beta/models?key={os.getenv('GOOGLE_GEMINI_API_KEY')}")

if os.getenv("ANTHROPIC_API_KEY"):
    test_endpoint("Anthropic", "https://api.anthropic.com/v1/messages", method="POST", json_data={"model": "claude-3-haiku-20240307", "max_tokens": 1, "messages": [{"role": "user", "content": "hi"}]}, headers={"x-api-key": os.getenv("ANTHROPIC_API_KEY"), "anthropic-version": "2023-06-01"})

if os.getenv("SERP_API_KEY"):
    test_endpoint("SerpApi", f"https://serpapi.com/search.json?engine=google&q=test&api_key={os.getenv('SERP_API_KEY')}")

if os.getenv("DUFFEL_API_KEY"):
    test_endpoint("Duffel (GDS Passagens)", "https://api.duffel.com/air/airlines?limit=1", headers={"Duffel-Version": "v1", "Authorization": f"Bearer {os.getenv('DUFFEL_API_KEY')}"})

if os.getenv("CAPSOLVER_API_KEY"):
    test_endpoint("Capsolver", "https://api.capsolver.com/getBalance", method="POST", json_data={"clientKey": os.getenv("CAPSOLVER_API_KEY")})

if os.getenv("TEQUILA_API_KEY"):
    test_endpoint("Tequila (Kiwi)", "https://tequila-api.kiwi.com/locations/query?term=PRG&location_types=airport", headers={"apikey": os.getenv("TEQUILA_API_KEY")})

if os.getenv("PROXY_URL"):
    print(f"[CONFIGURADA] Proxy URL: {os.getenv('PROXY_URL')[:20]}...")

print("----------------------------------------\n")

