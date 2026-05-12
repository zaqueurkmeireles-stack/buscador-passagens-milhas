from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    """
    Define o Estado (State) orquestrado pelo LangGraph.
    Este estado é persistido no Supabase Checkpointer durante esperas longas.
    """
    # Histórico de mensagens da conversa (o reducer add_messages pode ser usado no Graph, 
    # mas aqui usamos list concat padrão do python ou operator.add se formos usar com LangGraph MessagesState)
    messages: Annotated[List[BaseMessage], operator.add]
    
    # Intenção extraída (ex: "buscar_passagem", "duvida_bagagem")
    intent: Optional[str]
    
    # Dicionário de parâmetros de voo/viagem já preenchidos
    extracted_parameters: Dict[str, Any]
    
    # Dicionário para logs de erros críticos ou bloqueios WAF no fluxo
    api_errors: Dict[str, str]
