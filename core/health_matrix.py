import asyncio
import asyncpg
import requests
import logging
from typing import Dict, Any
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from core.config import config

logger = logging.getLogger(__name__)

# Configuração Nativa de Fallbacks (LangChain)
def get_redundant_llm():
    """
    Retorna o LLM principal configurado com fallbacks.
    Se o Gemini falhar (Rate Limit, Outage), roteia invisivelmente para a OpenAI.
    """
    # LLM Primário: Gemini
    primary_llm = ChatGoogleGenerativeAI(
        model="gemini-1.5-flash", 
        google_api_key=config.GEMINI_API_KEY,
        temperature=0
    )
    
    # LLM Secundário: OpenAI
    fallback_llm = ChatOpenAI(
        model="gpt-4o-mini", 
        api_key=config.OPENAI_API_KEY,
        temperature=0
    )
    
    # Retorna a instância com fallback acoplado
    return primary_llm.with_fallbacks([fallback_llm])


@tool
async def auditar_apis_e_redundancia() -> Dict[str, str]:
    """
    Skill obrigatória do Agente.
    Faz um ping (Health Check) a todos os nós vitais do sistema (LLMs, Supabase, Amadeus, CapSolver).
    Retorna um dicionário com o status de cada serviço.
    """
    status_matrix: Dict[str, str] = {}

    # 1. Teste Conexão LLMs (Com Fallback)
    try:
        llm = get_redundant_llm()
        # Envia uma call simples (PING)
        response = await llm.ainvoke([HumanMessage(content="PING. Reply only 'PONG'.")])
        if "pong" in response.content.lower():
            status_matrix["LLM_Redundancy"] = "[🟢 UP]"
        else:
            status_matrix["LLM_Redundancy"] = "[🟡 WARNING] Resposta inesperada."
    except Exception as e:
        logger.error(f"Erro no teste LLM: {e}")
        status_matrix["LLM_Redundancy"] = f"[🔴 DOWN] Erro: {str(e)}"

    # 2. Teste Supabase via asyncpg
    try:
        if config.DB_URL:
            conn = await asyncpg.connect(config.DB_URL)
            await conn.fetchval('SELECT 1')
            await conn.close()
            status_matrix["Supabase_DB"] = "[🟢 UP]"
        else:
            status_matrix["Supabase_DB"] = "[🟡 WARNING] DB_URL não configurado."
    except Exception as e:
        logger.error(f"Erro no teste Supabase: {e}")
        status_matrix["Supabase_DB"] = f"[🔴 DOWN] Erro: {str(e)}"

    # 3. Teste Amadeus (Bearer Token)
    try:
        if config.AMADEUS_CLIENT_ID and config.AMADEUS_CLIENT_SECRET:
            url = "https://test.api.amadeus.com/v1/security/oauth2/token"
            data = {
                "grant_type": "client_credentials",
                "client_id": config.AMADEUS_CLIENT_ID,
                "client_secret": config.AMADEUS_CLIENT_SECRET
            }
            # Idealmente assíncrono, mas requests.post() aqui como prova de conceito
            response = requests.post(url, data=data, timeout=5)
            if response.status_code == 200:
                status_matrix["Amadeus_API"] = "[🟢 UP]"
            else:
                status_matrix["Amadeus_API"] = f"[🔴 DOWN] Status Code: {response.status_code}"
        else:
            status_matrix["Amadeus_API"] = "[🟡 WARNING] Chaves do Amadeus não configuradas."
    except Exception as e:
        logger.error(f"Erro no teste Amadeus: {e}")
        status_matrix["Amadeus_API"] = f"[🔴 DOWN] Erro: {str(e)}"

    # 4. Teste CapSolver
    try:
        if config.CAPSOLVER_API_KEY:
            payload = {
                "clientKey": config.CAPSOLVER_API_KEY
            }
            response = requests.post("https://api.capsolver.com/getBalance", json=payload, timeout=5)
            if response.status_code == 200:
                status_matrix["CapSolver_API"] = "[🟢 UP]"
            else:
                status_matrix["CapSolver_API"] = f"[🔴 DOWN] Status Code: {response.status_code}"
        else:
            status_matrix["CapSolver_API"] = "[🟡 WARNING] Chave do CapSolver não configurada."
    except Exception as e:
        logger.error(f"Erro no teste CapSolver: {e}")
        status_matrix["CapSolver_API"] = f"[🔴 DOWN] Erro: {str(e)}"

    # 5. Teste Duffel API (PRIMÁRIO para buscas de voos)
    try:
        if config.DUFFEL_API_KEY:
            headers = {
                "Authorization": f"Bearer {config.DUFFEL_API_KEY}",
                "Accept": "application/json",
                "Duffel-Version": "v2"
            }
            response = requests.get("https://api.duffel.com/air/airports?limit=1", headers=headers, timeout=5)
            if response.status_code == 200:
                status_matrix["Duffel_API"] = "[🟢 UP] (Primário GDS)"
            else:
                status_matrix["Duffel_API"] = f"[🔴 DOWN] Status Code: {response.status_code}"
        else:
            status_matrix["Duffel_API"] = "[🟡 WARNING] DUFFEL_API_KEY não configurada."
    except Exception as e:
        logger.error(f"Erro no teste Duffel: {e}")
        status_matrix["Duffel_API"] = f"[🔴 DOWN] Erro: {str(e)}"

    # 6. Teste Gemini API (Fallback Intelligence Search)
    try:
        if config.GEMINI_API_KEY:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={config.GEMINI_API_KEY}",
                json={"contents": [{"parts": [{"text": "PING reply PONG"}]}]},
                timeout=5
            )
            if response.status_code == 200:
                status_matrix["Gemini_Search"] = "[🟢 UP] (Fallback Intelligence)"
            elif response.status_code == 429:
                status_matrix["Gemini_Search"] = "[🟡 RATE_LIMITED] Quota excedida temporariamente."
            else:
                status_matrix["Gemini_Search"] = f"[🔴 DOWN] Status Code: {response.status_code}"
        else:
            status_matrix["Gemini_Search"] = "[🟡 WARNING] GEMINI_API_KEY não configurada."
    except Exception as e:
        logger.error(f"Erro no teste Gemini: {e}")
        status_matrix["Gemini_Search"] = f"[🔴 DOWN] Erro: {str(e)}"

    return status_matrix
