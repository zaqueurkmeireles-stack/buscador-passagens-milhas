import json
import logging
from typing import Dict, Any
import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from core.config import config

# Configuração de log para o módulo
logger = logging.getLogger(__name__)

class LLMEngine:
    """
    Motor de IA responsável por interpretar a linguagem natural do usuário,
    extrair parâmetros de busca de viagem e gerar respostas contextualizadas
    com a persona do 'Comandante'.
    """

    def __init__(self):
        api_key = config.GEMINI_API_KEY
        if not api_key:
            logger.error("GOOGLE_GEMINI_API_KEY não encontrada no ambiente.")
            raise ValueError("Variável GOOGLE_GEMINI_API_KEY não configurada no .env")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        # System prompt estrito para forçar o papel e a saída JSON
        self.system_prompt = """Você é um viajante experiente e um consultor de aviação de alta performance (Travel Hacker). O seu objetivo é sempre entregar as 3 maneiras mais baratas e inteligentes de voar. Automaticamente, você deve considerar: aeroportos alternativos ou cidades próximas ao destino, opções com flexibilidade de horários (+/- 1 a 3 dias se aplicável), e EXCLUIR sumariamente conexões que demorem mais de 5 horas. Ao apresentar os resultados, mostre comparações de preços totais (dinheiro vs. milhas) e as companhias aéreas recomendadas.

Você atua como a inteligência central (Comandante) de um Personal Travel AI Agent.
Sua missão é ler o texto do passageiro (usuário), extrair os parâmetros de busca para voos e retornar EXCLUSIVAMENTE um JSON.

O JSON DEVE ter a seguinte estrutura exata:
{
  "status": "complete" ou "incomplete",
  "reply_message": "Sua resposta como 'Comandante'. Se complete, confirme que os radares foram ativados para o monitoramento. Se incomplete, peça amigavelmente as informações que faltam.",
  "intent": "flight_search",
  "destination": "Código IATA (ex: MCZ) ou nome da cidade",
  "destination_radius_km": inteiro (ex: 150),
  "excluded_airports": ["Lista", "de", "IATA", "ou", "cidades", "a", "excluir"],
  "month": "MM/YYYY ou data especificada",
  "pax_adults": inteiro (assuma 1 se não houver menção),
  "pax_children": inteiro (assuma 0 se não houver menção)
}

REGRAS ABSOLUTAS:
1. O retorno DEVE ser um JSON válido e nada mais. Sem blocos de código (```json), sem explicações adicionais.
2. Para que o status seja "complete", é necessário ter, no mínimo, um destino claro e uma data/mês de viagem.
3. Se faltar destino ou data, defina "status": "incomplete" e use o campo "reply_message" para perguntar o que falta de forma acolhedora.
4. Se "status": "complete", use "reply_message" para informar ao usuário (com a sua criatividade de Comandante) que o alerta e monitoramento de preços foi registrado com sucesso.
"""

    async def process_text(self, user_text: str) -> Dict[str, Any]:
        """
        Processa o texto do usuário de forma assíncrona, chamando a API do Gemini.
        Garante o retorno de um dicionário com os parâmetros e estado da conversa.
        """
        try:
            # Configura a geração para forçar o MIME type como JSON (recurso suportado no Gemini 1.5)
            # O parâmetro temperature baixo ajuda a manter a estrutura previsível.
            config = GenerationConfig(
                response_mime_type="application/json",
                temperature=0.2
            )
            
            prompt = f"{self.system_prompt}\n\nMensagem do passageiro:\n{user_text}"
            
            response = await self.model.generate_content_async(
                contents=[{"role": "user", "parts": [prompt]}],
                generation_config=config
            )
            
            # Realiza o parse do JSON retornado pelo Gemini
            data = json.loads(response.text)
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Falha ao interpretar JSON do LLM: {e} | Resposta crua: {response.text}")
            return {
                "status": "error",
                "reply_message": "Comandante enfrentando turbulência nos radares (erro de formato). Pode repetir, por favor?"
            }
        except Exception as e:
            logger.error(f"Erro inesperado no LLMEngine: {e}", exc_info=True)
            return {
                "status": "error",
                "reply_message": "Painel de controle temporariamente offline devido a uma pane técnica. Retente em breve."
            }
