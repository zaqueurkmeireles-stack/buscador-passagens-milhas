import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

supabase = create_client(url, key)

try:
    res = supabase.table("usuarios").select("*").limit(5).execute()
    print("Usuarios found:")
    print(res.data)
except Exception as e:
    print(f"Erro usuarios: {e}")

# Guessing other names
for name in ["carteira_milhas", "carteiras_milhas", "milhas", "MileWallet", "mile_wallet"]:
    try:
        supabase.table(name).select("*").limit(0).execute()
        print(f"Table found: {name}")
    except:
        pass
