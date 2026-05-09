import os
from dotenv import load_dotenv

# Carrega as variáveis do .env
load_dotenv()

class Config:
    """
    Classe centralizada para o gerenciamento de credenciais e variáveis de ambiente.
    Zero credenciais hardcoded, lidas diretamente do .env.
    """
    # Banco de Dados (Supabase/Postgres)
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") # Chave full access para RAG e BD
    DB_URL = os.getenv("DB_URL")
    
    # APIs de IA
    GEMINI_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Usada primordialmente para Embeddings
    
    # Celery & Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Credenciais de Scraper das Cias Aéreas
    SMILES_CPF = os.getenv("SMILES_CPF")
    SMILES_PASSWORD = os.getenv("SMILES_PASSWORD")
    LATAM_CPF = os.getenv("LATAM_CPF")
    LATAM_PASSWORD = os.getenv("LATAM_PASSWORD")
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

config = Config()
