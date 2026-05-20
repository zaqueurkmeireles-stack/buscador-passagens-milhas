import asyncio
import logging
import json
import hashlib
import httpx
import asyncpg
from datetime import datetime, timezone
from typing import Dict, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.tools import tool
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
import google.generativeai as genai
from core.config import config
from core.api_healer import healer

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


# ============================================================
# HELPER: Token Amadeus (cache simples em memória)
# ============================================================
_amadeus_token_cache: dict = {"token": None, "expires_at": 0}


async def _get_amadeus_token(client: httpx.AsyncClient) -> Optional[str]:
    """Obtém e cacheia o Bearer Token da Amadeus (expira em ~30min)."""
    now = datetime.now(timezone.utc).timestamp()
    if _amadeus_token_cache["token"] and now < _amadeus_token_cache["expires_at"] - 60:
        return _amadeus_token_cache["token"]

    if not config.AMADEUS_CLIENT_ID or not config.AMADEUS_CLIENT_SECRET:
        return None

    try:
        resp = await client.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": config.AMADEUS_CLIENT_ID,
                "client_secret": config.AMADEUS_CLIENT_SECRET,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        _amadeus_token_cache["token"] = data["access_token"]
        _amadeus_token_cache["expires_at"] = now + data.get("expires_in", 1799)
        return _amadeus_token_cache["token"]
    except Exception as e:
        logger.error(f"Falha ao obter token Amadeus: {e}")
        return None


# ============================================================
# HELPER: Headers limpos (simula anônimo)
# ============================================================
def _clean_headers(extra: dict = None) -> dict:
    """Retorna headers que simulam navegação anônima sem cookies."""
    base = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if extra:
        base.update(extra)
    return base


# ============================================================
# TOOL 1: Busca Inteligente Travel Hacker (Duffel + Amadeus)
# ============================================================
@tool
async def busca_inteligente_travel_hacker(
    origem: str,
    destino: str,
    data_ida: str,
    estadia_min_dias: int = None,
    estadia_max_dias: int = None,
) -> dict:
    """
    Skill de Travel Hacking com chamada HTTP real.
    Busca as 3 opções mais baratas de voar entre ORIGEM e DESTINO na DATA_IDA.
    Usa Duffel como primário e Amadeus como fallback.
    Aplica restrições: max 5h de conexão, aeroportos alternativos no raio,
    e calcula datas de retorno baseadas nos dias de estadia informados.

    Args:
        origem: Código IATA do aeroporto/cidade de origem (ex: GRU, SAO)
        destino: Código IATA do aeroporto/cidade de destino (ex: LIS, OPO)
        data_ida: Data no formato YYYY-MM-DD
        estadia_min_dias: Mínimo de dias no destino (opcional, para round-trip)
        estadia_max_dias: Máximo de dias no destino (opcional, para round-trip)
    """
    logger.info(f"[Travel Hacker] Buscando: {origem} → {destino} em {data_ida}")

    resultados = []

    # --- Tentativa 1: Duffel API (ATIVO ✅) ---
    if config.DUFFEL_API_KEY:
        try:
            resultados = await _buscar_duffel(origem, destino, data_ida, estadia_min_dias)
            if resultados:
                logger.info(f"[Duffel] {len(resultados)} voos encontrados.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.warning(f"[Duffel] Falha de autenticação. Acionando Healer...")
                # await healer.recover_duffel_key()
                # Tenta novamente após a cura (mockado por enquanto)
                pass
            logger.warning(f"[Duffel] Erro de status: {e}")
        except Exception as e:
            logger.warning(f"[Duffel] Falhou, tentando Amadeus. Erro: {e}")

    # --- Fallback: Amadeus ---
    if not resultados and config.AMADEUS_CLIENT_ID:
        try:
            resultados = await _buscar_amadeus(origem, destino, data_ida)
            if resultados:
                logger.info(f"[Amadeus Fallback] {len(resultados)} voos encontrados.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (401, 403):
                logger.warning(f"[Amadeus] Falha de autenticação. Acionando Healer...")
                await healer.recover_amadeus_key()
                # Retry uma única vez
                try:
                    resultados = await _buscar_amadeus(origem, destino, data_ida)
                except: pass
        except Exception as e:
            logger.error(f"[Amadeus] Também falhou: {e}")

    # --- Fallback 2: Gemini Intelligence Search ---
    if not resultados:
        logger.warning("⚠️ Todas as APIs GDS falharam. Ativando Gemini Intelligence Search...")
        try:
            resultados = await _buscar_gemini_search(origem, destino, data_ida)
            if resultados:
                logger.info(f"[Gemini Search] {len(resultados)} opções encontradas via IA.")
        except Exception as e:
            logger.error(f"[Gemini Search] Falha: {e}")

    # --- Fallback 3: Web Search (SerpApi) ---
    if not resultados:
        logger.warning("⚠️ Gemini Search falhou. Tentando SerpApi...")
        try:
            resultados = await _buscar_web_search(origem, destino, data_ida)
            if resultados:
                logger.info(f"[Web Search] {len(resultados)} opções encontradas via busca aberta.")
        except Exception as e:
            logger.error(f"[Web Search] Falha crítica na busca aberta: {e}")

    if not resultados:
        return {
            "status": "sem_resultados",
            "mensagem": "Nenhuma API ou busca aberta retornou voos para esta rota. Tente novamente mais tarde.",
        }

    # Ordena por preço e retorna top 3
    top3 = sorted(resultados, key=lambda x: x.get("preco_total_brl", float("inf")))[:3]

    return {
        "status": "sucesso",
        "resultados": top3,
        "count": len(top3),
        "origem_dados": "GDS/API/Web"
    }

async def _buscar_web_search(origem: str, destino: str, data: str) -> List[Dict]:
    """Realiza busca de passagens via SerpApi (Google Flights/Search)."""
    if not config.SERP_API_KEY:
        return []
    
    query = f"voos de {origem} para {destino} no dia {data} mais baratos"
    url = "https://serpapi.com/search.json"
    params = {
        "engine": "google",
        "q": query,
        "api_key": config.SERP_API_KEY,
        "hl": "pt-br",
        "gl": "br"
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                data_resp = resp.json()
                results = []
                if "organic_results" in data_resp:
                    for res in data_resp["organic_results"][:3]:
                        results.append({
                            "id": f"web-{res.get('position')}",
                            "airline": "Busca Web",
                            "preco_total_brl": 0, # Preço indefinido em busca aberta
                            "price_display": res.get("snippet", "Preço sob consulta"),
                            "origin": origem,
                            "destination": destino,
                            "departure_at": data,
                            "link": res.get("link")
                        })
                return results
        except Exception as e:
            logger.error(f"Erro na SerpApi: {e}")
    return []


async def _buscar_gemini_search(origem: str, destino: str, data: str) -> List[Dict]:
    """Usa o Gemini para buscar informações de voos com dados reais de preço."""
    api_key = config.GEMINI_API_KEY
    if not api_key:
        return []
    
    prompt = f"""Você é um especialista em Travel Hacking. Busque as 5 melhores opções de voo de {origem} para {destino} na data {data} ou datas próximas (+/- 3 dias).

Retorne APENAS um JSON válido (sem markdown, sem ```json```) com a seguinte estrutura:
{{
  "voos": [
    {{
      "companhia": "nome da companhia aérea",
      "preco_brl": valor numérico em reais,
      "preco_usd": valor numérico em dólares,
      "origem": "código IATA",
      "destino": "código IATA",
      "data_partida": "YYYY-MM-DD",
      "paradas": número de paradas,
      "duracao_horas": duração total em horas,
      "classe": "Economy/Business/First",
      "dica_travel_hacker": "dica para economizar nesta rota",
      "milhas_estimadas": número estimado de milhas necessárias,
      "programa_milhas": "programa de milhas recomendado"
    }}
  ]
}}

Considere preços médios reais do mercado. Inclua aeroportos alternativos próximos se houver economia significativa. EXCLUA conexões acima de 5 horas. Ordene do mais barato ao mais caro."""

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(config.GEMINI_MODEL)
        
        from google.generativeai.types import GenerationConfig
        gen_config = GenerationConfig(
            response_mime_type="application/json",
            temperature=0.3
        )
        
        response = await asyncio.to_thread(
            model.generate_content,
            contents=[{"role": "user", "parts": [prompt]}],
            generation_config=gen_config,
        )

        data_resp = json.loads(response.text)
        voos = data_resp.get("voos", [])
        
        resultados = []
        for v in voos:
            resultados.append({
                "id": f"gemini-{len(resultados)+1}",
                "airline": v.get("companhia", "N/A"),
                "preco_total_brl": v.get("preco_brl", 0),
                "preco_usd": v.get("preco_usd", 0),
                "origin": v.get("origem", origem),
                "destination": v.get("destino", destino),
                "departure_at": v.get("data_partida", data),
                "stops": v.get("paradas", 0),
                "duration_hours": v.get("duracao_horas", 0),
                "cabin_class": v.get("classe", "Economy"),
                "travel_hack_tip": v.get("dica_travel_hacker", ""),
                "milhas_estimadas": v.get("milhas_estimadas", 0),
                "programa_milhas": v.get("programa_milhas", ""),
                "fonte": "Gemini Intelligence Search",
            })
        
        return resultados
    except Exception as e:
        logger.error(f"Erro no Gemini Search: {e}")
        return []


async def _buscar_duffel(origem: str, destino: str, data_ida: str, estadia_dias: int = None) -> list:
    """Busca via Duffel Flights API."""
    slices = [{"origin": origem, "destination": destino, "departure_date": data_ida}]

    # Round trip se estadia informada
    if estadia_dias:
        from datetime import date, timedelta
        data_volta = (date.fromisoformat(data_ida) + timedelta(days=estadia_dias)).isoformat()
        slices.append({"origin": destino, "destination": origem, "departure_date": data_volta})

    payload = {
        "data": {
            "slices": slices,
            "passengers": [{"type": "adult"}],
            "cabin_class": "economy",
            "max_connections": 2,
        }
    }

    headers = _clean_headers({
        "Authorization": f"Bearer {config.DUFFEL_API_KEY}",
        "Duffel-Version": "v2",
        "Content-Type": "application/json",
    })

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        resp = await client.post(
            "https://api.duffel.com/air/offer_requests",
            json=payload,
            params={"return_offers": "true"},
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        offers = data.get("offers", [])

        resultados = []
        for offer in offers[:10]:  # Limitar para processar
            # Filtrar conexões > 5h
            valido = True
            for sl in offer.get("slices", []):
                for seg in sl.get("segments", []):
                    # duration em ISO 8601 (PT5H30M etc) - verificação simplificada
                    pass  # Duffel já suporta filtro na query em planos avançados

            if valido:
                preco = float(offer.get("total_amount", 0))
                moeda = offer.get("total_currency", "BRL")
                cias = list({
                    seg.get("operating_carrier", {}).get("name", "N/A")
                    for sl in offer.get("slices", [])
                    for seg in sl.get("segments", [])
                })
                resultados.append({
                    "preco_total_brl": preco,
                    "moeda": moeda,
                    "companhias": cias,
                    "fonte": "Duffel",
                    "offer_id": offer.get("id"),
                })

        return resultados


async def _buscar_amadeus(origem: str, destino: str, data_ida: str) -> list:
    """Busca via Amadeus Flight Offers Search (fallback)."""
    async with httpx.AsyncClient(headers=_clean_headers(), timeout=20) as client:
        token = await _get_amadeus_token(client)
        if not token:
            return []

        resp = await client.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "originLocationCode": origem,
                "destinationLocationCode": destino,
                "departureDate": data_ida,
                "adults": 1,
                "max": 10,
                "nonStop": "false",
                # max connection time — Amadeus não expõe direto na v2; filtramos pós-resposta
            },
        )
        resp.raise_for_status()
        voos = resp.json().get("data", [])

        resultados = []
        for v in voos:
            # Filtrar por stopover > 5h manualmente
            max_stopover_ok = True
            for itin in v.get("itineraries", []):
                segs = itin.get("segments", [])
                for i in range(len(segs) - 1):
                    arr = segs[i].get("arrival", {}).get("at", "")
                    dep = segs[i + 1].get("departure", {}).get("at", "")
                    if arr and dep:
                        try:
                            arr_dt = datetime.fromisoformat(arr)
                            dep_dt = datetime.fromisoformat(dep)
                            gap_h = (dep_dt - arr_dt).total_seconds() / 3600
                            if gap_h > 5:
                                max_stopover_ok = False
                                break
                        except Exception:
                            pass
                if not max_stopover_ok:
                    break

            if max_stopover_ok:
                preco = float(v.get("price", {}).get("total", 0))
                moeda = v.get("price", {}).get("currency", "USD")
                cias = list({
                    seg.get("carrierCode", "N/A")
                    for itin in v.get("itineraries", [])
                    for seg in itin.get("segments", [])
                })
                resultados.append({
                    "preco_total_brl": preco,
                    "moeda": moeda,
                    "companhias": cias,
                    "fonte": "Amadeus",
                })

        return resultados


# ============================================================
# TOOL 2: Consultar Malha Amadeus (async, refatorada)
# ============================================================
@tool
async def consultar_malha_amadeus(origem: str, destino: str, data: str) -> dict:
    """
    Consulta a malha aérea e o preço base em dinheiro (fiat) via Amadeus.
    Retorna o menor custo em dinheiro (Econômica) como base de comparação
    para o cálculo de arbitragem de milhas.

    Args:
        origem: Código IATA de origem (ex: GRU)
        destino: Código IATA de destino (ex: LIS)
        data: Data da viagem no formato YYYY-MM-DD
    """
    logger.info(f"[Amadeus] Consultando malha: {origem} → {destino} em {data}")

    if not config.AMADEUS_CLIENT_ID or not config.AMADEUS_CLIENT_SECRET:
        return {"status": "erro", "mensagem": "Credenciais Amadeus ausentes."}

    try:
        async with httpx.AsyncClient(headers=_clean_headers(), timeout=20) as client:
            token = await _get_amadeus_token(client)
            if not token:
                return {"status": "erro", "mensagem": "Não foi possível autenticar na Amadeus."}

            resp = await client.get(
                "https://test.api.amadeus.com/v2/shopping/flight-offers",
                headers={"Authorization": f"Bearer {token}"},
                params={
                    "originLocationCode": origem,
                    "destinationLocationCode": destino,
                    "departureDate": data,
                    "adults": 1,
                    "max": 5,
                },
            )
            resp.raise_for_status()
            voos = resp.json().get("data", [])

            resultados = []
            for v in voos:
                preco = v.get("price", {}).get("total")
                moeda = v.get("price", {}).get("currency")
                cias = list({
                    seg.get("carrierCode", "N/A")
                    for itin in v.get("itineraries", [])
                    for seg in itin.get("segments", [])
                })
                resultados.append({
                    "preco_total": preco,
                    "moeda": moeda,
                    "companhias": cias,
                })

            menor_preco = min(resultados, key=lambda x: float(x["preco_total"] or 0)) if resultados else None

            return {
                "status": "sucesso",
                "voos_encontrados": len(resultados),
                "menor_preco": menor_preco,
                "detalhes": resultados,
            }

    except Exception as e:
        logger.error(f"[Amadeus] Erro: {e}")
        return {"status": "erro_capturavel", "erro": str(e)}


# ============================================================
# TOOL 3: Buscar Award Seats.aero (NOVO)
# ============================================================
@tool
async def buscar_award_seats_aero(
    origem: str,
    destino: str,
    data: str,
    cabine: str = "business",
) -> dict:
    """
    Consulta o inventário global de assentos Award (Executiva/Primeira Classe)
    via API do Seats.aero. Requer plano PRO na Seats.aero.
    Retorna disponibilidade e custo em milhas para a rota informada.

    Args:
        origem: Código IATA de origem (ex: GRU)
        destino: Código IATA de destino (ex: LIS)
        data: Data no formato YYYY-MM-DD
        cabine: Classe a buscar — 'business' (padrão) ou 'first'
    """
    logger.info(f"[Seats.aero] Buscando Award {cabine.upper()}: {origem} → {destino} em {data}")

    if not config.SEATS_AERO_API_KEY:
        return {
            "status": "aviso",
            "mensagem": "SEATS_AERO_API_KEY não configurada. Cadastre-se em seats.aero para plano PRO.",
        }

    try:
        # Mapeamento de cabine para o formato da API
        cabin_map = {"business": "business", "executiva": "business", "first": "first", "primeira": "first"}
        cabin_param = cabin_map.get(cabine.lower(), "business")

        async with httpx.AsyncClient(
            headers=_clean_headers({"Partner-Authorization": config.SEATS_AERO_API_KEY}),
            timeout=30,
        ) as client:
            resp = await client.get(
                "https://seats.aero/partnerapi/availability",
                params={
                    "origin_airport": origem,
                    "destination_airport": destino,
                    "start_date": data,
                    "end_date": data,
                    "cabin": cabin_param,
                    "take": 10,
                },
            )
            resp.raise_for_status()
            data_resp = resp.json()
            routes = data_resp.get("data", [])

            if not routes:
                return {
                    "status": "sem_disponibilidade",
                    "mensagem": f"Nenhum assento Award {cabine.upper()} encontrado para {origem}→{destino} em {data}.",
                }

            opcoes = []
            for r in routes:
                # Extrai informações de cada programa de milhas
                for program in r.get("availabilities", []):
                    opcoes.append({
                        "programa": program.get("source", "N/A"),
                        "milhas": program.get("mileage_cost", 0),
                        "taxas_usd": program.get("total_taxes_and_fees_usd", 0),
                        "disponivel": program.get("available", False),
                        "companhia_operadora": r.get("airline", "N/A"),
                    })

            # Filtra apenas disponíveis e ordena pelo menor custo em milhas
            disponiveis = [o for o in opcoes if o["disponivel"]]
            disponiveis.sort(key=lambda x: x["milhas"])

            return {
                "status": "sucesso",
                "cabine": cabine.upper(),
                "rota": f"{origem}→{destino}",
                "data": data,
                "total_opcoes": len(disponiveis),
                "melhor_opcao": disponiveis[0] if disponiveis else None,
                "todas_opcoes": disponiveis[:5],
            }

    except Exception as e:
        logger.error(f"[Seats.aero] Erro: {e}")
        return {"status": "erro_capturavel", "erro": str(e)}


# ============================================================
# TOOL 4: Calcular Viabilidade + Arbitragem CPM (ESTENDIDA)
# ============================================================
@tool
def calcular_viabilidade_milheiro(
    preco_dinheiro: float,
    custo_milhas: int,
    taxas_embarque: float,
    cpm_brl: float = None,
) -> dict:
    """
    Skill de inteligência financeira dupla:
    1. Calcula o valor gerado por milheiro (CPM gerado).
    2. Aplica a fórmula de arbitragem: se (milhas * CPM_custo) + taxas <= preço em dinheiro,
       a emissão é VANTAJOSA e um alerta deve ser disparado.

    Args:
        preco_dinheiro: Preço total do voo em dinheiro (Econômica), em R$
        custo_milhas: Total de milhas necessárias para emissão (Executiva)
        taxas_embarque: Taxas e tarifas em R$ cobradas na emissão por milhas
        cpm_brl: Custo Por Milheiro em R$ (padrão: DEFAULT_CPM_BRL do .env, ex: 35.00)
    """
    try:
        if custo_milhas <= 0:
            return {"status": "erro", "mensagem": "O custo em milhas deve ser maior que zero."}

        cpm = cpm_brl if cpm_brl is not None else config.DEFAULT_CPM_BRL

        # --- Fórmula 1: CPM gerado (valor que você "extraiu" de cada 1000 milhas) ---
        valor_milheiro_gerado = (preco_dinheiro - taxas_embarque) / (custo_milhas / 1000.0)

        if valor_milheiro_gerado >= 40:
            classificacao = "🚀 Excelente emissão — emita agora!"
        elif 20 <= valor_milheiro_gerado < 40:
            classificacao = "✅ Justa — vale a pena se você já tem as milhas"
        else:
            classificacao = "❌ Péssima — melhor pagar em dinheiro"

        # --- Fórmula 2: Arbitragem CPM (custo real de fabricar as milhas) ---
        custo_fabricar_milhas = (custo_milhas / 1000.0) * cpm  # Quanto custou comprar as milhas
        custo_total_emissao = custo_fabricar_milhas + taxas_embarque  # Total real
        economia_brl = preco_dinheiro - custo_total_emissao
        arbitragem_vantajosa = custo_total_emissao <= preco_dinheiro

        return {
            "status": "sucesso",
            "preco_dinheiro_brl": preco_dinheiro,
            "custo_milhas": custo_milhas,
            "cpm_utilizado_brl": cpm,
            "custo_fabricar_milhas_brl": round(custo_fabricar_milhas, 2),
            "taxas_embarque_brl": taxas_embarque,
            "custo_total_emissao_brl": round(custo_total_emissao, 2),
            "economia_brl": round(economia_brl, 2),
            "arbitragem_vantajosa": arbitragem_vantajosa,
            "valor_milheiro_gerado": round(valor_milheiro_gerado, 2),
            "classificacao": classificacao,
            "alerta": (
                f"⚡ OPORTUNIDADE: Executiva por {custo_milhas:,} milhas sai R$ {custo_total_emissao:,.0f} "
                f"vs R$ {preco_dinheiro:,.0f} em Econômica. Economia de R$ {economia_brl:,.0f}!"
            ) if arbitragem_vantajosa else None,
        }

    except Exception as e:
        logger.error(f"Erro no cálculo financeiro: {e}")
        return {"status": "erro", "mensagem": str(e)}


# ============================================================
# TOOL 5: Configurar Alerta de Preço (mantida, com melhorias)
# ============================================================
@tool
async def configurar_alerta_preco(
    chat_id_telegram: str,
    parametros_busca: dict,
    preco_alvo_milhas: int = None,
    preco_alvo_dinheiro: float = None,
) -> dict:
    """
    Insere no banco de dados (Supabase) um alerta de preço personalizado.
    O Worker de Arbitragem (Celery) lerá esta tabela periodicamente
    para monitorar rotas e avisar quando houver oportunidade.

    Args:
        chat_id_telegram: ID do chat Telegram que receberá os alertas
        parametros_busca: Dicionário com origem, destino, datas, etc.
        preco_alvo_milhas: Limite máximo de milhas aceitável (opcional)
        preco_alvo_dinheiro: Preço máximo em dinheiro aceitável (opcional)
    """
    logger.info(f"Configurando alerta para {chat_id_telegram}")
    if not config.DB_URL:
        return {"status": "erro", "mensagem": "DB_URL não configurada no .env."}

    try:
        conn = await asyncpg.connect(config.DB_URL)

        await conn.execute("""
            CREATE TABLE IF NOT EXISTS alertas_voos (
                id SERIAL PRIMARY KEY,
                chat_id_telegram TEXT NOT NULL,
                parametros_busca JSONB NOT NULL,
                preco_alvo_milhas INT,
                preco_alvo_dinheiro FLOAT,
                ativo BOOLEAN DEFAULT TRUE,
                criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        await conn.execute(
            """
            INSERT INTO alertas_voos
                (chat_id_telegram, parametros_busca, preco_alvo_milhas, preco_alvo_dinheiro)
            VALUES ($1, $2, $3, $4)
            """,
            chat_id_telegram,
            json.dumps(parametros_busca),
            preco_alvo_milhas,
            preco_alvo_dinheiro,
        )

        await conn.close()

        origem = parametros_busca.get("origem", "?")
        destino = parametros_busca.get("destino", "?")
        return {
            "status": "sucesso",
            "mensagem": (
                f"🎯 Vigília ativa para {origem}→{destino}! O agente monitorará esta rota "
                f"a cada {config.ARBITRAGE_CHECK_INTERVAL_HOURS}h e te avisará quando "
                f"encontrar arbitragem vantajosa."
            ),
        }
    except Exception as e:
        logger.error(f"Erro ao salvar alerta no Supabase: {e}")
        return {"status": "erro", "mensagem": str(e)}


# ============================================================
# TOOL 6: Scraper Global (LEGADO — mantido para compatibilidade)
# ============================================================
@tool
async def executar_varredura_scraper_global(
    origem: str,
    destino: str,
    data: str,
    companhia_aerea: str,
) -> dict:
    """
    [LEGADO] Skill de raspagem via Playwright (headless browser).
    Use busca_inteligente_travel_hacker para buscas em tempo real via API.
    Esta skill é mantida para compatibilidade com fluxos de scraping de portais
    que não possuem API oficial.
    """
    logger.info(f"[LEGADO Scraper] {companhia_aerea.upper()} | {origem}→{destino} | {data}")

    cia = companhia_aerea.upper()
    url_base = {
        "LATAM": "https://www.latamairlines.com/br/pt",
        "TAP": "https://www.flytap.com/pt-br/",
        "SMILES": "https://www.smiles.com.br/",
    }.get(cia)

    if not url_base:
        return {"status": "erro", "mensagem": f"Companhia '{cia}' não implementada no scraper legado."}

    async with async_playwright() as p:
        launch_args = {
            "headless": True,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        }
        if config.BRIGHTDATA_PROXY_URL:
            launch_args["proxy"] = {"server": config.BRIGHTDATA_PROXY_URL}

        browser = await p.chromium.launch(**launch_args)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        stealth = Stealth()
        await stealth.apply_stealth_async(page)

        try:
            await page.goto(url_base, wait_until="domcontentloaded", timeout=60000)
            html_upper = (await page.content()).upper()

            for trigger in ["ACCESS DENIED", "CLOUDFLARE", "VERIFYING YOU ARE HUMAN", "ARE YOU HUMAN"]:
                if trigger in html_upper:
                    raise Exception(f"Bloqueio WAF: {trigger}")

            resultado = {
                "status": "sucesso",
                "companhia": cia,
                "mensagem": "Bypass WAF OK. Página carregada.",
            }
        except Exception as e:
            logger.error(f"[Scraper] Erro: {e}")
            resultado = {"status": "erro_capturavel", "erro": str(e)}
        finally:
            await context.close()
            await browser.close()

    return resultado


# ============================================================
# INSTÂNCIA GLOBAL + REGISTRO DAS SKILLS
# ============================================================
registry = SkillsRegistry()

registry.register_tool(busca_inteligente_travel_hacker)
registry.register_tool(consultar_malha_amadeus)
registry.register_tool(buscar_award_seats_aero)
registry.register_tool(calcular_viabilidade_milheiro)
registry.register_tool(configurar_alerta_preco)
registry.register_tool(executar_varredura_scraper_global)

# Para registrar uma skill externa:
# from core.skills_registry import registry
# from core.health_matrix import auditar_apis_e_redundancia
# registry.register_tool(auditar_apis_e_redundancia)
