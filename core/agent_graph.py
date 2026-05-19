import logging
from typing import Dict, Any, Literal
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from core.agent_state import AgentState
from core.skills_registry import registry
from core.health_matrix import get_redundant_llm
from core.api_healer import healer

logger = logging.getLogger(__name__)

# Recupera todas as tools registradas no sistema
tools = registry.get_all_tools()

# Cria o nó de ferramentas pré-construído do LangGraph
tool_node = ToolNode(tools)

# Puxa o LLM primário (Gemini) com fallback silencioso para redundância
llm = get_redundant_llm()

# Anexa (bind) as ferramentas ao LLM para que ele saiba usá-las
llm_with_tools = llm.bind_tools(tools)

# Prompt central do Agente
travel_hacker_prompt = """Você é um viajante experiente e um consultor de aviação de alta performance (Travel Hacker). O seu objetivo é sempre entregar as 3 maneiras mais baratas e inteligentes de voar. Automaticamente, você deve considerar: aeroportos alternativos ou cidades próximas ao destino, opções com flexibilidade de horários (+/- 1 a 3 dias se aplicável), e EXCLUIR sumariamente conexões que demorem mais de 5 horas. Ao apresentar os resultados, mostre comparações de preços totais (dinheiro vs. milhas) e as companhias aéreas recomendadas.

Você atua como a inteligência central (Comandante) de um Personal Travel AI Agent."""

async def call_model(state: AgentState) -> dict:
    """Nó principal que invoca o LLM com o estado atual e as ferramentas."""
    logger.info(">>> Executando Node: call_model")
    messages = state.get("messages", [])
    
    # Se não houver SystemMessage na lista, injeta no início para garantir a persona
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=travel_hacker_prompt)] + list(messages)
        
    try:
        response = await llm_with_tools.ainvoke(messages)
        # Retornamos apenas a resposta em formato de lista porque o reducer operator.add vai concatenar no estado
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}")
        
        # Lógica de Self-Healing para Gemini
        err_str = str(e).upper()
        if "API_KEY" in err_str or "UNAUTHORIZED" in err_str or "401" in err_str or "403" in err_str:
            logger.warning("🚨 Falha de Autenticação detectada no LLM. Acionando Healer...")
            new_key = await healer.recover_google_gemini_key()
            if new_key:
                logger.info("✅ Nova chave Gemini obtida. Re-tentando loop...")
                # Re-vincula o LLM com a nova chave (na prática o get_redundant_llm pegará do env atualizado)
                try:
                    new_llm = get_redundant_llm()
                    new_llm_with_tools = new_llm.bind_tools(tools)
                    response = await new_llm_with_tools.ainvoke(messages)
                    return {"messages": [response]}
                except: pass

        # Em caso de erro persistente, retorna mensagem amigável e encerra
        error_msg = AIMessage(content="Comandante enfrentando forte turbulência nos satélites de comunicação. Retente em minutos.")
        return {"messages": [error_msg]}

def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Aresta condicional: decide se chama as ferramentas ou encerra o loop."""
    messages = state.get("messages", [])
    if not messages:
        return "__end__"
        
    last_message = messages[-1]
    
    # Se o LLM gerou "tool_calls" (intenção de chamar funções/skills)
    if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
        logger.info(f"O Agente decidiu usar as skills: {[t['name'] for t in last_message.tool_calls]}")
        return "tools"
    
    logger.info("O Agente finalizou o raciocínio. Encerrando fluxo.")
    return "__end__"

# ==========================================
# COMPILAÇÃO DO STATEGRAPH
# ==========================================
def compile_agent_graph():
    """Constrói o Grafo do Agente ReAct."""
    workflow = StateGraph(AgentState)
    
    # Adiciona os nós
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    
    # Define as conexões (Arestas)
    workflow.add_edge(START, "agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "__end__": END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    # Compila a aplicação final
    return workflow.compile()

agent_app = compile_agent_graph()

# ==========================================
# ENTRYPOINT DO TELEGRAM
# ==========================================
async def processar_mensagem_telegram(mensagem: str, chat_id: str) -> str:
    """
    Ponto de entrada público para o Bot do Telegram ou Webhooks.
    Inicializa o estado com a mensagem do utilizador e invoca o grafo.
    """
    logger.info(f"Recebendo mensagem do chat {chat_id}: {mensagem}")
    
    # Inicializa o estado. Messages deve ser uma lista para o reducer operator.add funcionar
    initial_state = {
        "messages": [HumanMessage(content=mensagem)],
        "intent": None,
        "extracted_parameters": {},
        "api_errors": {}
    }
    
    # Invoca o grafo compilado de forma assíncrona
    final_state = await agent_app.ainvoke(initial_state)
    
    # Extrai a última mensagem gerada pelo Agente (conteúdo seguro para o Telegram)
    last_message = final_state["messages"][-1]
    content = getattr(last_message, "content", None)
    if isinstance(content, list):
        content = "\n".join(str(part) for part in content)
    if not content:
        content = (
            "Comandante, não consegui montar a resposta final. "
            "Tente reformular a busca com origem, destino e data."
        )
    return str(content)
