import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

try:
    res = supabase.table("documentos_viagem").select("*").limit(1).execute()
    print("documentos_viagem data:")
    print(res.data)
except Exception as e:
    print(f"Erro: {e}")
