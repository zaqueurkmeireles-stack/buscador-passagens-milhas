import os
import requests
from dotenv import load_dotenv

# Carrega as chaves do arquivo .env local
load_dotenv()

print("\n🔍 INICIANDO DIAGNÓSTICO DE APIs...\n")

def testar_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token: return "⚠️ NÃO ENCONTRADA"
    r = requests.get(f"https://api.telegram.org/bot{token}/getMe")
    return "✅ SUCESSO (Bot Autorizado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Chave Inválida"

def testar_gemini():
    chave = os.getenv("GOOGLE_GEMINI_API_KEY")
    if not chave: return "⚠️ NÃO ENCONTRADA"
    r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={chave}")
    return "✅ SUCESSO (Acesso Autorizado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Chave Inválida"

def testar_openai():
    chave = os.getenv("OPENAI_API_KEY")
    if not chave: return "⚠️ NÃO ENCONTRADA"
    headers = {"Authorization": f"Bearer {chave}"}
    r = requests.get("https://api.openai.com/v1/models", headers=headers)
    return "✅ SUCESSO (Acesso Autorizado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Chave Inválida"

def testar_supabase():
    url = os.getenv("SUPABASE_URL")
    chave = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not chave: return "⚠️ NÃO ENCONTRADA"
    headers = {"apikey": chave, "Authorization": f"Bearer {chave}"}
    r = requests.get(f"{url}/rest/v1/", headers=headers)
    return "✅ SUCESSO (Acesso Autorizado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Verifique URL ou Chave"

def testar_amadeus():
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    if not client_id or not client_secret: return "⚠️ NÃO ENCONTRADA"
    data = {"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret}
    r = requests.post("https://test.api.amadeus.com/v1/security/oauth2/token", data=data)
    return "✅ SUCESSO (Token Gerado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Credenciais Rejeitadas"

def testar_duffel():
    chave = os.getenv("DUFFEL_API_KEY")
    if not chave: return "⚠️ NÃO ENCONTRADA"
    headers = {"Authorization": f"Bearer {chave}", "Duffel-Version": "beta"}
    r = requests.get("https://api.duffel.com/air/airlines", headers=headers)
    return "✅ SUCESSO (Acesso Autorizado)" if r.status_code == 200 else f"❌ ERRO {r.status_code}: Chave Inválida"

# Execução dos testes
print(f"1. TELEGRAM: {testar_telegram()}")
print(f"2. GEMINI:   {testar_gemini()}")
print(f"3. OPENAI:   {testar_openai()}")
print(f"4. SUPABASE: {testar_supabase()}")
print(f"5. AMADEUS:  {testar_amadeus()}")
print(f"6. DUFFEL:   {testar_duffel()}")
print("\n🏁 TESTE CONCLUÍDO.\n")
