import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_amadeus():
    print("Testando autenticação na API do Amadeus...")
    client_id = os.getenv("AMADEUS_CLIENT_ID")
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("Erro: Chaves não encontradas no .env")
        return
        
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }
    
    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            print("SUCESSO! Conexão com Amadeus estabelecida.")
            print(f"Token gerado: {response.json().get('access_token')[:10]}...")
        else:
            print(f"FALHA! Código: {response.status_code}")
            print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    test_amadeus()
