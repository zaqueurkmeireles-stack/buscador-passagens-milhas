import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

try:
    # Try to fetch something from MileWallet to see if it exists
    res = supabase.table("MileWallet").select("*").limit(1).execute()
    print("MileWallet existe.")
except Exception as e:
    print(f"Erro ao acessar MileWallet: {e}")

try:
    # List all tables if possible (PostgREST doesn't have a direct 'list tables' but we can try common ones)
    print("Tentando acessar tabelas comuns...")
    for table in ["MileWallet", "MileWallets", "mile_wallet", "documents"]:
        try:
            supabase.table(table).select("*").limit(0).execute()
            print(f"Tabela {table} encontrada.")
        except:
            pass
except Exception as e:
    print(f"Erro geral: {e}")
