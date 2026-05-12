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
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Usada para Fallback e Embeddings
    
    # Orquestração (LangGraph)
    LANGCHAIN_TRACING_V2 = os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true"
    LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT")
    
    # Celery & Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # Credenciais de Scraper das Cias Aéreas
    SMILES_CPF = os.getenv("SMILES_CPF")
    SMILES_PASSWORD = os.getenv("SMILES_PASSWORD")
    LATAM_CPF = os.getenv("LATAM_CPF")
    LATAM_PASSWORD = os.getenv("LATAM_PASSWORD")
    
    # Infraestrutura e Proxies
    BRIGHTDATA_PROXY_URL = os.getenv("PROXY_URL")
    CAPSOLVER_API_KEY = os.getenv("CAPSOLVER_API_KEY")
    
    # Aviação (Amadeus)
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

config = Config()
