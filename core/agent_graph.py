import json
import logging
import operator
from typing import TypedDict, Annotated, Sequence, Dict, Any
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from supabase.client import create_client

from core.rag_engine import RAGEngine
from core.config import config

logger = logging.getLogger(__name__)

# --- DEFINIÇÃO DO ESTADO GLOBAL DO GRAFO ---
class AgentState(TypedDict):
    """Estado tipado que percorre todos os nós do LangGraph."""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    original_text: str
    extracted_params: Dict[str, Any]
    rag_context: str
    mileage_balances: Dict[str, int]
    final_response: str

# Instanciação estática de serviços e LLMs para uso nos nós
try:
    llm_extractor = ChatGoogleGenerativeAI(model="gemini-flash-latest", api_key=config.GEMINI_API_KEY, temperature=0.1)
    llm_consensus = ChatGoogleGenerativeAI(model="gemini-pro-latest", api_key=config.GEMINI_API_KEY, temperature=0.3)
    rag_engine = RAGEngine()
    supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
except Exception as e:
    logger.error(f"Erro ao instanciar os motores na inicialização do Grafo: {e}")

# ==========================================
# DEFINIÇÃO DOS NÓS (NODES) DO LANGGRAPH
# ==========================================

async def node_extract_intent(state: AgentState) -> AgentState:
    """Nó 1: Usa o LLM para extrair parâmetros matemáticos (Destino, Preço, Pessoas)."""
    logger.info(">>> Executando Node 1: Intent & Extract")
    text = state.get("original_text", "")
    
    prompt = f"""Você é o extrator mestre do Personal Travel AI Agent.
    Analise a seguinte solicitação: '{text}'
    
    Retorne EXCLUSIVAMENTE um objeto JSON contendo:
    "destination": (string ou null se não houver),
    "price_alert": (number ou null),
    "people": (integer, assuma 1 se implícito),
    "requires_rag": (booleano, obrigatoriamente true se mencionar hotel, voucher, viagem atual, check-in ou regras passadas, senao false)
    """
    
    try:
        response = await llm_extractor.ainvoke([HumanMessage(content=prompt)])
        content = response.content
        if isinstance(content, list):
            content = "".join([str(p) for p in content])
        raw_text = content.strip().strip("```json").strip("```").strip()
        params = json.loads(raw_text)
        logger.info(f"Parâmetros extraídos: {params}")
    except Exception as e:
        logger.error(f"Erro crasso no parser de extração JSON: {e}")
        params = {"requires_rag": False, "error": str(e)}
        
    return {"extracted_params": params}

async def node_rag_retrieval(state: AgentState) -> AgentState:
    """Nó 2: Se o usuário mencionar a viagem atual/vouchers, busca no RAG."""
    logger.info(">>> Executando Node 2: Knowledge Retrieval")
    params = state.get("extracted_params", {})
    text = state.get("original_text", "")
    
    if not params.get("requires_rag", False):
        logger.info("RAG bypassado (não exigido).")
        return {"rag_context": "Sem contexto documental extra."}
        
    try:
        retriever = rag_engine.get_retriever()
        docs = await retriever.ainvoke(text)
        context = "\n".join([d.page_content for d in docs])
        logger.info(f"Contexto do RAG recuperado. Extensão: {len(context)} chars")
        return {"rag_context": context}
    except Exception as e:
        logger.error(f"Falha na recuperação do RAG: {e}")
        return {"rag_context": "Erro ao tentar buscar contexto documental."}

async def node_database_query(state: AgentState) -> AgentState:
    """Nó 3: Cruza o alerta desejado com o saldo atual de milhas (Supabase)."""
    logger.info(">>> Executando Node 3: Database Query")
    
    try:
        # Busca hardcoded para o usuário base Zaqueu
        # Nota: Tentando 'mile_wallets' se 'MileWallet' falhar no futuro
        response = supabase.table("MileWallet").select("*").eq("user_id", "zaqueu_master_id").execute()
        balances = {row["program"]: row["balance"] for row in response.data}
        logger.info(f"Saldos encontrados: {balances}")
    except Exception as e:
        logger.error(f"Supabase offline ou falha na leitura: {e}")
        balances = {"smiles": 0, "latam": 0}
        
    return {"mileage_balances": balances}

async def node_consensus_validation(state: AgentState) -> AgentState:
    """Nó 4: Realiza uma dupla checagem (Consensus) garantindo solidez matemática da emissão."""
    logger.info(">>> Executando Node 4: Consensus Validation")
    
    text = state["original_text"]
    params = state["extracted_params"]
    context = state["rag_context"]
    balances = state["mileage_balances"]
    
    prompt = f"""Assuma o papel do 'Comandante', o cérebro avançado do Personal Travel AI Agent.
    Você precisa dar o veredito final ao passageiro. O ambiente de execução exige precisão extrema.
    
    MENSAGEM DO USUÁRIO: "{text}"
    PARÂMETROS EXTRAÍDOS: {params}
    DADOS DE VOUCHERS/HOTEL (RAG): {context}
    SALDO REAL DE MILHAS EM BANCO: {balances}
    
    DIRETRIZES:
    1. Cruze a quantidade de pessoas x provável custo da passagem (estime a partir do destino, ou explique se não der).
    2. Avalie se o saldo atual de milhas nas respectivas companhias suporta a intenção do usuário.
    3. Responda se as datas cruzam adequadamente com os dados de Voucher (se fornecido).
    4. Gere uma resposta direta, humana, acolhedora e conclusiva. Se aprovado, afirme. Se as milhas não baterem, recuse com cálculos claros.
    """
    
    try:
        response = await llm_consensus.ainvoke([HumanMessage(content=prompt)])
        final_answer = response.content
    except Exception as e:
        logger.error(f"Falha do LLM no Consensus Validation: {e}")
        final_answer = "Comandante aqui: Enfrentamos uma falha de consenso no radar. Repita a operação em minutos."
    
    return {"final_response": final_answer}

# ==========================================
# COMPILAÇÃO DO STATEGRAPH
# ==========================================
def compile_agent_graph() -> Any:
    """Constrói e compila as arestas lógicas do grafo de agentes."""
    workflow = StateGraph(AgentState)
    
    # Registra nós
    workflow.add_node("extract", node_extract_intent)
    workflow.add_node("rag", node_rag_retrieval)
    workflow.add_node("db", node_database_query)
    workflow.add_node("consensus", node_consensus_validation)
    
    # Ordem de execução (Linear e determinística para este design)
    workflow.set_entry_point("extract")
    workflow.add_edge("extract", "rag")
    workflow.add_edge("rag", "db")
    workflow.add_edge("db", "consensus")
    workflow.add_edge("consensus", END)
    
    # Compila para gerar a aplicação assíncrona executável
    return workflow.compile()

# Ponto de acesso do app
agent_app = compile_agent_graph()
