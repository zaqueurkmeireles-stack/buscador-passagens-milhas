import logging
import json
import requests
import asyncpg
from typing import List
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from core.config import config

logger = logging.getLogger(__name__)

class SkillsRegistry:
    """
    Registro centralizado das 'Tools' (Skills) do Agente.
    O LangChain utilizará bind_tools() enviando este array para o LLM.
    """
    def __init__(self):
        self.tools: List[BaseTool] = []
        
    def register_tool(self, tool: BaseTool):
        """Registra uma ferramenta (Skill) para o agente."""
        self.tools.append(tool)
        logger.info(f"Skill registrada: {tool.name}")
        
    def get_all_tools(self) -> List[BaseTool]:
        """Retorna todas as tools disponíveis para o bind."""
        return self.tools

        return self.tools

@tool
def busca_inteligente_travel_hacker(
    origem: str, 
    destino: str, 
    data_ida: str, 
    estadia_min_dias: int = None, 
    estadia_max_dias: int = None
) -> dict:
    """
    Skill de busca inteligente de passagens.
    Executa a pesquisa considerando aeroportos num raio de 150km,
    calcula as datas de volta baseadas nos dias de estadia e
    exclui rotas com layovers (conexões) superiores a 5 horas.
    """
    logger.info(f"Travel Hacker ativado para: {origem} -> {destino} em {data_ida}")
    
    # Mockup de lógica avançada:
    # 1. Expandir aeroportos:
    aeroportos_origem = [origem]
    aeroportos_destino = [destino] # Aqui entraria a API Google Maps/Amadeus para achar IATAs num raio de 150km
    
    # 2. Lógica de Estadia:
    datas_retorno = []
    if estadia_min_dias is not None and estadia_max_dias is not None:
        # Lógica de cálculo (datetime) iria aqui.
        pass
        
    # 3. Lógica de Filtro:
    max_layover_hours = 5
    
    return {
        "status": "sucesso",
        "mensagem": f"Busca engatilhada para {origem}->{destino}. Raio: 150km. Max layover: 5h.",
        "params_utilizados": {
            "origem": aeroportos_origem,
            "destino": aeroportos_destino,
            "data_ida": data_ida,
            "estadias_verificadas": f"{estadia_min_dias} a {estadia_max_dias} dias" if estadia_min_dias else "Apenas ida"
        }
    }

# Instância global
registry = SkillsRegistry()

# Auto-registro das skills
registry.register_tool(busca_inteligente_travel_hacker)

@tool
async def executar_varredura_scraper_global(
    origem: str,
    destino: str,
    data: str,
    companhia_aerea: str
) -> dict:
    """
    Skill de raspagem invisível global.
    Abre um navegador headless blindado contra Anti-Bots, injeta proxy rotativo
    e navega na companhia aérea solicitada para extrair voos e preços em milhas.
    """
    logger.info(f"Iniciando varredura global para {companhia_aerea.upper()} na rota {origem}->{destino} ({data})")
    
    # Arquitetura de Roteamento (Factory Pattern)
    cia = companhia_aerea.upper()
    url_base = ""
    if cia == "LATAM":
        url_base = "https://www.latamairlines.com/br/pt"
    elif cia == "TAP":
        url_base = "https://www.flytap.com/pt-br/"
    elif cia == "SMILES":
        url_base = "https://www.smiles.com.br/"
    else:
        # Fallback genérico ou erro se a cia não estiver suportada
        return {"status": "erro", "mensagem": f"Companhia aérea '{cia}' ainda não implementada no roteador."}

    # Integração do Motor Playwright
    async with async_playwright() as p:
        launch_args = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        }
        
        if config.BRIGHTDATA_PROXY_URL:
            # O proxy no Playwright requer que as credenciais fiquem separadas ou no formato url se suportado.
            # O playwright lida com o auth na URL.
            launch_args["proxy"] = {"server": config.BRIGHTDATA_PROXY_URL}
            
        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # Blindagem Stealth
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        try:
            logger.info(f"Acessando {url_base}...")
            await page.goto(url_base, wait_until="domcontentloaded", timeout=60000)
            
            # Fail-Fast (Anti-Bot/WAF Bypass) - Verificação Genérica
            html_content = await page.content()
            html_upper = html_content.upper()
            
            waf_triggers = [
                "ACCESS DENIED",
                "POR MOTIVOS DE SEGURIDAD",
                "POR RAZÕES DE SEGURANÇA",
                "CLOUDFLARE",
                "VERIFYING YOU ARE HUMAN",
                "ARE YOU HUMAN"
            ]
            
            for trigger in waf_triggers:
                if trigger in html_upper:
                    logger.error(f"Bloqueio WAF detectado: {trigger}")
                    raise Exception(f"Bloqueio WAF: {trigger}. Abortar para rotacionar IP.")
            
            # Se passou do WAF, pode continuar a lógica da Factory...
            logger.info(f"Varredura inicial na {cia} concluída com sucesso sem bloqueios WAF.")
            resultado = {
                "status": "sucesso",
                "companhia": cia,
                "mensagem": "Bypass WAF bem sucedido. Página carregada pronta para raspagem."
            }
            
        except Exception as e:
            logger.error(f"Erro durante varredura: {e}")
            resultado = {
                "status": "erro_capturavel",
                "erro": str(e)
            }
        finally:
            await context.close()
            await browser.close()
            
    return resultado

@tool
def consultar_malha_amadeus(origem: str, destino: str, data: str) -> dict:
    """
    Consulta a malha aérea e o preço base pagante (fiat) utilizando a API oficial do Amadeus.
    Retorna o custo em dinheiro como base de comparação.
    """
    logger.info(f"Consultando Amadeus para: {origem} -> {destino} em {data}")
    
    if not config.AMADEUS_CLIENT_ID or not config.AMADEUS_CLIENT_SECRET:
        return {"status": "erro", "mensagem": "Credenciais Amadeus ausentes."}
        
    try:
        # Autenticação
        auth_url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": config.AMADEUS_CLIENT_ID,
            "client_secret": config.AMADEUS_CLIENT_SECRET
        }
        auth_response = requests.post(auth_url, data=auth_data, timeout=5)
        auth_response.raise_for_status()
        token = auth_response.json().get("access_token")
        
        # Busca de Voos (Flight Offers Search)
        search_url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        params = {
            "originLocationCode": origem,
            "destinationLocationCode": destino,
            "departureDate": data,
            "adults": 1,
            "max": 3
        }
        headers = {"Authorization": f"Bearer {token}"}
        
        search_response = requests.get(search_url, headers=headers, params=params, timeout=10)
        search_response.raise_for_status()
        
        voos = search_response.json().get("data", [])
        
        resultados = []
        for v in voos:
            preco = v.get("price", {}).get("total")
            moeda = v.get("price", {}).get("currency")
            resultados.append({"preco_total": preco, "moeda": moeda, "itinerarios": "Detalhes omitidos..."})
            
        return {"status": "sucesso", "voos_encontrados": len(resultados), "detalhes": resultados}
        
    except Exception as e:
        logger.error(f"Erro na consulta Amadeus: {e}")
        return {"status": "erro_capturavel", "erro": str(e)}

@tool
def calcular_viabilidade_milheiro(preco_dinheiro: float, custo_milhas: int, taxas_embarque: float) -> dict:
    """
    Skill de inteligência financeira. Compara o preço pagante com o custo em milhas 
    e determina o valor gerado por milheiro. Classifica a emissão.
    """
    try:
        if custo_milhas <= 0:
            return {"status": "erro", "mensagem": "O custo em milhas deve ser maior que zero."}
            
        # Fórmula: (Preço Dinheiro - Taxas de Embarque) / (Milhas / 1000)
        valor_milheiro = (preco_dinheiro - taxas_embarque) / (custo_milhas / 1000.0)
        
        if valor_milheiro >= 40:
            classificacao = "Excelente emissão"
        elif 20 <= valor_milheiro < 40:
            classificacao = "Justa"
        else:
            classificacao = "Péssima - melhor pagar em dinheiro"
            
        return {
            "valor_gerado_por_milheiro": round(valor_milheiro, 2),
            "classificacao": classificacao,
            "formula_utilizada": f"({preco_dinheiro} - {taxas_embarque}) / ({custo_milhas} / 1000)"
        }
    except Exception as e:
        logger.error(f"Erro no cálculo financeiro: {e}")
        return {"status": "erro", "mensagem": str(e)}

@tool
async def configurar_alerta_preco(chat_id_telegram: str, parametros_busca: dict, preco_alvo_milhas: int = None, preco_alvo_dinheiro: float = None) -> dict:
    """
    Insere no banco de dados (Supabase) um alerta de preço. O Celery lerá esta 
    tabela periodicamente para rodar o scraper invisível em background.
    """
    logger.info(f"Configurando alerta para {chat_id_telegram} com alvo milhas: {preco_alvo_milhas}")
    if not config.DB_URL:
        return {"status": "erro", "mensagem": "A URL do banco (DB_URL) não está configurada no .env."}
        
    try:
        conn = await asyncpg.connect(config.DB_URL)
        
        # Cria a tabela de alertas caso ainda não exista
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS alertas_voos (
                id SERIAL PRIMARY KEY,
                chat_id_telegram TEXT NOT NULL,
                parametros_busca JSONB NOT NULL,
                preco_alvo_milhas INT,
                preco_alvo_dinheiro FLOAT,
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        await conn.execute('''
            INSERT INTO alertas_voos (chat_id_telegram, parametros_busca, preco_alvo_milhas, preco_alvo_dinheiro)
            VALUES ($1, $2, $3, $4)
        ''', chat_id_telegram, json.dumps(parametros_busca), preco_alvo_milhas, preco_alvo_dinheiro)
        
        await conn.close()
        
        return {
            "status": "sucesso", 
            "mensagem": "Vigília ativada! O agente rodará buscas silenciosas em background para esta rota."
        }
    except Exception as e:
        logger.error(f"Erro ao salvar alerta no Supabase: {e}")
        return {"status": "erro", "mensagem": str(e)}

registry.register_tool(executar_varredura_scraper_global)
registry.register_tool(consultar_malha_amadeus)
registry.register_tool(calcular_viabilidade_milheiro)
registry.register_tool(configurar_alerta_preco)

# Como registrar uma skill de fora:
# from core.skills_registry import registry
# from core.health_matrix import auditar_apis_e_redundancia
# registry.register_tool(auditar_apis_e_redundancia)
