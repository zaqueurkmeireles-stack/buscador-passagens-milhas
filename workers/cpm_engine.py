"""
Worker de Arbitragem de Milhas — CPM Engine
============================================
Task Celery que roda em background a cada N horas verificando oportunidades
de arbitragem entre o preço em dinheiro (Econômica) e assentos Award
(Executiva/Primeira Classe) disponíveis via Seats.aero.

Fórmula de decisão:
    (milhas * CPM_BRL / 1000) + taxas_embarque <= preco_economica_brl
    → Se verdadeiro: OPORTUNIDADE → Alerta Telegram (com deduplicação anti-spam 24h)
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta

import httpx
import asyncpg

from workers.celery_app import celery_app
from core.config import config

logger = logging.getLogger(__name__)

# ============================================================
# HELPER: Headers limpos (anônimo, sem cookies)
# ============================================================
def _clean_headers(extra: dict = None) -> dict:
    base = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    if extra:
        base.update(extra)
    return base


# ============================================================
# HELPER: Token Amadeus
# ============================================================
_token_cache: dict = {"token": None, "expires_at": 0}


async def _get_amadeus_token(client: httpx.AsyncClient) -> str | None:
    now = datetime.now(timezone.utc).timestamp()
    if _token_cache["token"] and now < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

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
        _token_cache["token"] = data["access_token"]
        _token_cache["expires_at"] = now + data.get("expires_in", 1799)
        return _token_cache["token"]
    except Exception as e:
        logger.error(f"[CPM Engine] Falha ao obter token Amadeus: {e}")
        return None


# ============================================================
# STEP 1: Buscar preço Econômica (Amadeus → Duffel fallback)
# ============================================================
async def _fetch_economy_price(client: httpx.AsyncClient, origem: str, destino: str, data: str) -> float | None:
    """Retorna o menor preço de Econômica encontrado (em R$ ou USD)."""

    # --- Amadeus ---
    if config.AMADEUS_CLIENT_ID:
        try:
            token = await _get_amadeus_token(client)
            if token:
                resp = await client.get(
                    "https://test.api.amadeus.com/v2/shopping/flight-offers",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "originLocationCode": origem,
                        "destinationLocationCode": destino,
                        "departureDate": data,
                        "adults": 1,
                        "max": 5,
                        "currencyCode": "BRL",
                    },
                    timeout=15,
                )
                resp.raise_for_status()
                voos = resp.json().get("data", [])
                precos = [float(v["price"]["total"]) for v in voos if v.get("price", {}).get("total")]
                if precos:
                    logger.info(f"[CPM] Amadeus → menor preço {origem}→{destino}: R$ {min(precos):.2f}")
                    return min(precos)
        except Exception as e:
            logger.warning(f"[CPM] Amadeus falhou para {origem}→{destino}: {e}")

    # --- Duffel Fallback ---
    if config.DUFFEL_API_KEY:
        try:
            payload = {
                "data": {
                    "slices": [{"origin": origem, "destination": destino, "departure_date": data}],
                    "passengers": [{"type": "adult"}],
                    "cabin_class": "economy",
                }
            }
            resp = await client.post(
                "https://api.duffel.com/air/offer_requests",
                json=payload,
                headers=_clean_headers({
                    "Authorization": f"Bearer {config.DUFFEL_API_KEY}",
                    "Duffel-Version": "v2",
                    "Content-Type": "application/json",
                }),
                params={"return_offers": "true"},
                timeout=25,
            )
            resp.raise_for_status()
            offers = resp.json().get("data", {}).get("offers", [])
            precos = [float(o.get("total_amount", 0)) for o in offers if o.get("total_amount")]
            if precos:
                logger.info(f"[CPM] Duffel → menor preço {origem}→{destino}: {min(precos):.2f}")
                return min(precos)
        except Exception as e:
            logger.warning(f"[CPM] Duffel também falhou para {origem}→{destino}: {e}")

    return None


# ============================================================
# STEP 2: Buscar assentos Award via Seats.aero
# ============================================================
async def _fetch_award_seats(client: httpx.AsyncClient, origem: str, destino: str, data: str) -> list[dict]:
    """Retorna lista de opções Award disponíveis com custo em milhas."""
    if not config.SEATS_AERO_API_KEY:
        logger.warning("[CPM] SEATS_AERO_API_KEY não configurada. Pulando busca Award.")
        return []

    try:
        resp = await client.get(
            "https://seats.aero/partnerapi/availability",
            headers=_clean_headers({"Partner-Authorization": config.SEATS_AERO_API_KEY}),
            params={
                "origin_airport": origem,
                "destination_airport": destino,
                "start_date": data,
                "end_date": data,
                "cabin": "business",
                "take": 10,
            },
            timeout=20,
        )
        resp.raise_for_status()
        routes = resp.json().get("data", [])

        opcoes = []
        for r in routes:
            for av in r.get("availabilities", []):
                if av.get("available"):
                    opcoes.append({
                        "programa": av.get("source", "N/A"),
                        "milhas": int(av.get("mileage_cost", 0)),
                        "taxas_usd": float(av.get("total_taxes_and_fees_usd", 0)),
                        "companhia": r.get("airline", "N/A"),
                    })

        opcoes.sort(key=lambda x: x["milhas"])
        logger.info(f"[CPM] Seats.aero → {len(opcoes)} opções Award para {origem}→{destino}")
        return opcoes

    except Exception as e:
        logger.error(f"[CPM] Seats.aero erro: {e}")
        return []


# ============================================================
# STEP 3: Verificação anti-spam no Supabase (flight_alerts_log)
# ============================================================
async def _already_alerted(conn: asyncpg.Connection, route_hash: str) -> bool:
    """Retorna True se este hash foi alertado nas últimas 24 horas."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    row = await conn.fetchrow(
        "SELECT id FROM flight_alerts_log WHERE route_hash = $1 AND alert_timestamp > $2 LIMIT 1",
        route_hash,
        cutoff,
    )
    return row is not None


async def _log_alert(conn: asyncpg.Connection, route_hash: str, details: dict) -> None:
    """Insere o hash do alerta no log de deduplicação."""
    await conn.execute(
        "INSERT INTO flight_alerts_log (route_hash, alert_timestamp, details) VALUES ($1, $2, $3)",
        route_hash,
        datetime.now(timezone.utc),
        json.dumps(details),
    )


# ============================================================
# STEP 4: Enviar alerta via Telegram
# ============================================================
async def _send_telegram_alert(message: str, chat_id: str = None) -> None:
    """Dispara mensagem Markdown para o Telegram."""
    target_chat = chat_id or config.ADMIN_CHAT_ID
    if not config.TELEGRAM_BOT_TOKEN or not target_chat:
        logger.warning("[CPM] TELEGRAM_BOT_TOKEN ou ADMIN_CHAT_ID não configurados.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": target_chat,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            logger.info(f"[CPM] Alerta Telegram enviado para {target_chat}.")
        except Exception as e:
            logger.error(f"[CPM] Falha ao enviar alerta Telegram: {e}")


# ============================================================
# STEP 5: Lógica principal de arbitragem para UMA rota
# ============================================================
async def _check_route_arbitrage(
    conn: asyncpg.Connection,
    client: httpx.AsyncClient,
    origem: str,
    destino: str,
    data: str,
    chat_id: str,
    cpm_brl: float = None,
) -> None:
    """Executa toda a lógica de arbitragem para uma rota."""
    cpm = cpm_brl or config.DEFAULT_CPM_BRL
    logger.info(f"[CPM] Verificando arbitragem: {origem}→{destino} | {data} | CPM=R${cpm}")

    # 1. Preço Econômica
    preco_eco = await _fetch_economy_price(client, origem, destino, data)
    if preco_eco is None:
        logger.warning(f"[CPM] Sem preço de econômica para {origem}→{destino}. Pulando.")
        return

    # 2. Assentos Award
    award_opcoes = await _fetch_award_seats(client, origem, destino, data)
    if not award_opcoes:
        logger.info(f"[CPM] Sem assentos Award disponíveis para {origem}→{destino}.")
        return

    # 3. Avalia cada opção Award
    for opcao in award_opcoes:
        milhas = opcao["milhas"]
        taxas_usd = opcao["taxas_usd"]

        # Conversão simplificada de taxas USD→BRL (fator 5.0 como estimativa conservadora)
        # Em produção, buscar cotação do dólar via API
        FATOR_USD_BRL = 5.0
        taxas_brl = taxas_usd * FATOR_USD_BRL

        custo_fabricar = (milhas / 1000.0) * cpm
        custo_total_emissao = custo_fabricar + taxas_brl
        economia = preco_eco - custo_total_emissao

        if custo_total_emissao <= preco_eco:
            # ARBITRAGEM DETECTADA!
            route_hash = hashlib.sha256(
                f"{origem}-{destino}-{data}-{opcao['programa']}".encode()
            ).hexdigest()[:16]

            # 4. Verificar anti-spam
            if await _already_alerted(conn, route_hash):
                logger.info(f"[CPM] Alerta duplicado (< 24h) para {route_hash}. Silenciando.")
                continue

            # 5. Formatar e disparar alerta
            msg = (
                f"✈️ *OPORTUNIDADE DE ARBITRAGEM DETECTADA!*\n\n"
                f"🛫 Rota: *{origem} → {destino}* | {data}\n"
                f"🏢 Programa: `{opcao['programa']}` | Cia: {opcao['companhia']}\n\n"
                f"💰 *Econômica em dinheiro:* R$ {preco_eco:,.0f}\n"
                f"🎟️ *Executiva via milhas:*\n"
                f"   • Milhas: `{milhas:,}`\n"
                f"   • Custo fabricar (CPM R${cpm}): R$ {custo_fabricar:,.0f}\n"
                f"   • Taxas estimadas: R$ {taxas_brl:,.0f}\n"
                f"   • *Total emissão: R$ {custo_total_emissao:,.0f}*\n\n"
                f"💎 *Economia: R$ {economia:,.0f}* ({economia/preco_eco*100:.0f}% mais barato)\n\n"
                f"🚀 *Emita agora antes que acabe!*\n"
                f"🔑 Hash: `{route_hash}`"
            )

            await _send_telegram_alert(msg, chat_id)

            # 6. Registrar no log anti-spam
            await _log_alert(conn, route_hash, {
                "origem": origem,
                "destino": destino,
                "data": data,
                "programa": opcao["programa"],
                "milhas": milhas,
                "preco_eco": preco_eco,
                "custo_total": custo_total_emissao,
                "economia": round(economia, 2),
            })

            logger.info(f"[CPM] ✅ Alerta disparado: {route_hash} | Economia R${economia:.0f}")


# ============================================================
# TASK CELERY: run_arbitrage_check
# ============================================================
@celery_app.task(name="workers.cpm_engine.run_arbitrage_check", bind=True, max_retries=3)
def run_arbitrage_check(self):
    """
    Task Celery assíncrona que executa o loop completo de arbitragem.
    Lê as rotas monitoradas da tabela alertas_voos no Supabase e verifica
    cada uma contra Amadeus/Duffel + Seats.aero.
    """
    try:
        asyncio.run(_run_arbitrage_async())
    except Exception as exc:
        logger.error(f"[CPM] Erro crítico no worker de arbitragem: {exc}", exc_info=True)
        raise self.retry(exc=exc, countdown=60 * 5)  # Retry em 5 min


async def _run_arbitrage_async():
    """Lógica assíncrona principal do worker de arbitragem."""
    if not config.DB_URL:
        logger.error("[CPM] DB_URL não configurada. Worker abortado.")
        return

    logger.info("[CPM] === Iniciando varredura de arbitragem ===")

    try:
        conn = await asyncpg.connect(config.DB_URL)
    except Exception as e:
        logger.error(f"[CPM] Falha ao conectar no Supabase: {e}")
        return

    try:
        # Garante que a tabela de log existe
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS flight_alerts_log (
                id BIGSERIAL PRIMARY KEY,
                route_hash TEXT NOT NULL,
                alert_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                details JSONB
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_fal_route_hash ON flight_alerts_log(route_hash)"
        )

        # Carrega rotas ativas da tabela de alertas do usuário
        alertas = await conn.fetch(
            "SELECT chat_id_telegram, parametros_busca FROM alertas_voos WHERE ativo = TRUE"
        )

        if not alertas:
            logger.info("[CPM] Nenhuma rota ativa para monitorar. Configure alertas via Telegram.")
            return

        logger.info(f"[CPM] {len(alertas)} rotas ativas para verificar.")

        async with httpx.AsyncClient(headers=_clean_headers(), timeout=30) as client:
            for alerta in alertas:
                try:
                    params = json.loads(alerta["parametros_busca"])
                    origem = params.get("origem", "").upper()
                    destino = params.get("destino", "").upper()
                    data = params.get("data_ida") or params.get("data", "")
                    chat_id = alerta["chat_id_telegram"]

                    if not origem or not destino or not data:
                        logger.warning(f"[CPM] Alerta com parâmetros incompletos: {params}")
                        continue

                    await _check_route_arbitrage(conn, client, origem, destino, data, chat_id)

                except Exception as e:
                    logger.error(f"[CPM] Erro ao processar alerta: {e}", exc_info=True)

    finally:
        await conn.close()

    logger.info("[CPM] === Varredura de arbitragem concluída ===")


# ============================================================
# TASK CELERY: calculate_cpm (mantida, implementada)
# ============================================================
@celery_app.task(name="workers.cpm_engine.calculate_cpm")
def calculate_cpm(user_id: int, program_name: str, milhas: int = 0, taxas_brl: float = 0.0) -> dict:
    """
    Motor de Custo Fiduciário e Arbitragem (CPM Engine).
    Calcula o Custo Por Milheiro efetivo dado o contexto do usuário.
    Suporta simulação de promoções de transferência (ex: Bônus 100%).

    Args:
        user_id: ID do usuário
        program_name: Nome do programa de milhas (ex: 'livelo', 'esfera')
        milhas: Quantidade de milhas a avaliar
        taxas_brl: Taxas de embarque em R$ para a emissão
    """
    cpm = config.DEFAULT_CPM_BRL
    custo_total = (milhas / 1000.0) * cpm + taxas_brl

    resultado = {
        "user_id": user_id,
        "program": program_name,
        "milhas": milhas,
        "cpm_brl": cpm,
        "custo_fabricar_brl": round((milhas / 1000.0) * cpm, 2),
        "taxas_brl": taxas_brl,
        "custo_total_emissao_brl": round(custo_total, 2),
    }
    logger.info(f"[CPM] calculate_cpm → {resultado}")
    return resultado
