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
    # Modelo deve existir em ListModels (gemini-1.5-pro foi descontinuado na API)
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    GEMINI_API_VERSION = os.getenv("GEMINI_API_VERSION", "v1")
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
    
    # Aviação (Amadeus — credenciais 401 em 2026-05-13, fallback ativo)
    AMADEUS_CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
    AMADEUS_CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
    
    # Aviação (Duffel — ATIVO e funcional ✅)
    DUFFEL_API_KEY = os.getenv("DUFFEL_API_KEY")
    
    # Web Search Fallbacks
    SERP_API_KEY = os.getenv("SERP_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

    # Travel Hacking & Arbitragem de Milhas
    # Tequila (Kiwi) - reservado para quando a key estiver disponível
    TEQUILA_API_KEY = os.getenv("TEQUILA_API_KEY")
    # Seats.aero - plano PRO necessário para inventário Award global
    SEATS_AERO_API_KEY = os.getenv("SEATS_AERO_API_KEY")
    # CPM fixo em R$ (ex: compra com 50% off na Livelo/Esfera = R$ 35/1000 pts)
    DEFAULT_CPM_BRL = float(os.getenv("DEFAULT_CPM_BRL", "35.00"))
    # Intervalo em horas para o worker de arbitragem rodar (padrão: 4h)
    ARBITRAGE_CHECK_INTERVAL_HOURS = int(os.getenv("ARBITRAGE_CHECK_INTERVAL_HOURS", "4"))

config = Config()
