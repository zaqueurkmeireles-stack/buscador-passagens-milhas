import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

tables = ["users", "search_alerts", "flight_results", "mile_wallets"]

for table in tables:
    try:
        res = supabase.table(table).select("*").limit(0).execute()
        print(f"Tabela {table} encontrada.")
    except Exception as e:
        print(f"Erro ao acessar {table}: {e}")
