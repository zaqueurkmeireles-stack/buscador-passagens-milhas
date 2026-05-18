import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_duffel():
    print("Testando autenticação na API da Duffel...")
    api_key = os.getenv("DUFFEL_API_KEY")
    
    if not api_key:
        print("Erro: Chave DUFFEL_API_KEY não encontrada no .env")
        return
        
    url = "https://api.duffel.com/air/airlines"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Duffel-Version": "beta"
    }
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("SUCESSO! Conexão com Duffel estabelecida.")
            data = response.json()
            airlines = data.get('data', [])
            print(f"Buscado {len(airlines)} companhias aéreas com sucesso!")
        else:
            print(f"FALHA! Código: {response.status_code}")
            print(f"Resposta: {response.text}")
    except Exception as e:
        print(f"Erro ao conectar: {e}")

if __name__ == "__main__":
    test_duffel()
