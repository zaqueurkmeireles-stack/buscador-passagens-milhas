import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_message():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("ADMIN_CHAT_ID")
    
    if not token or not chat_id:
        print("Token ou Chat ID ausente.")
        return
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🤖 **Deploy Finalizado no Easypanel!**\n\nTodas as chaves (Supabase, Duffel, Amadeus) foram atualizadas com sucesso. O sistema está online.\n\nPor favor, me peça para buscar uma passagem ou mande um Oi para testarmos se estou operando sem o Erro 401!",
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            print("Mensagem de teste enviada com sucesso no Telegram!")
        else:
            print(f"Falha ao enviar: {response.text}")
    except Exception as e:
        print(f"Erro: {e}")

if __name__ == "__main__":
    send_message()
