import logging
from functools import lru_cache
from typing import Dict, Any, Literal

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

from core.agent_state import AgentState
from core.skills_registry import registry
from core.config import config
from core.api_healer import healer

logger = logging.getLogger(__name__)

tools = registry.get_all_tools()
tool_node = ToolNode(tools)

travel_hacker_prompt = """Você é um viajante experiente e um consultor de aviação de alta performance (Travel Hacker). O seu objetivo é sempre entregar as 3 maneiras mais baratas e inteligentes de voar. Automaticamente, você deve considerar: aeroportos alternativos ou cidades próximas ao destino, opções com flexibilidade de horários (+/- 1 a 3 dias se aplicável), e EXCLUIR sumariamente conexões que demorem mais de 5 horas. Ao apresentar os resultados, mostre comparações de preços totais (dinheiro vs. milhas) e as companhias aéreas recomendadas.

Você atua como a inteligência central (Comandante) de um Personal Travel AI Agent."""


@lru_cache(maxsize=1)
def _build_agent_chat_model() -> ChatGoogleGenerativeAI:
    """
    LLM do grafo ReAct com payload compatível com function calling do Gemini.

    O LangChain (google-genai) serializa system_instruction e tools no formato
    da API v1beta. Forçar api_version=v1 quebra com 'Unknown name systemInstruction/tools'.
    """
    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        google_api_key=config.GEMINI_API_KEY,
        temperature=0,
    )


def _get_llm_with_tools() -> ChatGoogleGenerativeAI:
    """Vincula as skills ao modelo sem alterar api_version do SDK."""
    return _build_agent_chat_model().bind_tools(tools)


def _prepare_messages(state: AgentState) -> list:
    """Garante system prompt e histórico no formato LangChain (convertido pelo SDK)."""
    messages = list(state.get("messages", []))
    if not messages or not isinstance(messages[0], SystemMessage):
        messages = [SystemMessage(content=travel_hacker_prompt)] + messages
    return messages


async def call_model(state: AgentState) -> dict:
    """Nó principal: invoca Gemini com tools via payload aceito pela API (v1beta wire format)."""
    logger.info(">>> Executando Node: call_model")
    messages = _prepare_messages(state)

    try:
        response = await _get_llm_with_tools().ainvoke(messages)
        return {"messages": [response]}
    except Exception as e:
        logger.error(f"Erro ao chamar LLM: {e}", exc_info=True)

        err_str = str(e).upper()
        if "API_KEY" in err_str or "UNAUTHORIZED" in err_str or "401" in err_str or "403" in err_str:
            logger.warning("Falha de autenticação no LLM. Acionando Healer...")
            new_key = await healer.recover_google_gemini_key()
            if new_key:
                _build_agent_chat_model.cache_clear()
                try:
                    response = await _get_llm_with_tools().ainvoke(messages)
                    return {"messages": [response]}
                except Exception as retry_err:
                    logger.error(f"Retry após Healer falhou: {retry_err}")

        error_msg = AIMessage(
            content="Comandante enfrentando forte turbulência nos satélites de comunicação. Retente em minutos."
        )
        return {"messages": [error_msg]}


def should_continue(state: AgentState) -> Literal["tools", "__end__"]:
    """Aresta condicional: decide se chama as ferramentas ou encerra o loop."""
    messages = state.get("messages", [])
    if not messages:
        return "__end__"

    last_message = messages[-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"O Agente decidiu usar as skills: {[t['name'] for t in last_message.tool_calls]}")
        return "tools"

    logger.info("O Agente finalizou o raciocínio. Encerrando fluxo.")
    return "__end__"


def compile_agent_graph():
    """Constrói o Grafo do Agente ReAct."""
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "agent")

    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "__end__": END,
        },
    )

    workflow.add_edge("tools", "agent")

    return workflow.compile()


agent_app = compile_agent_graph()


async def processar_mensagem_telegram(mensagem: str, chat_id: str) -> str:
    """
    Ponto de entrada público para o Bot do Telegram ou Webhooks.
    Inicializa o estado com a mensagem do utilizador e invoca o grafo.
    """
    logger.info(f"Recebendo mensagem do chat {chat_id}: {mensagem}")

    initial_state = {
        "messages": [HumanMessage(content=mensagem)],
        "intent": None,
        "extracted_parameters": {},
        "api_errors": {},
    }

    final_state = await agent_app.ainvoke(initial_state)

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
