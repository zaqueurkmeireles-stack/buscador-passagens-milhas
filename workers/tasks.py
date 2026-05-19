import asyncio
import logging
from typing import Optional

import aiohttp
from supabase import Client, create_client

from core.config import config
from scraper.engine import MileageScraper
from workers.celery_app import celery_app

logger = logging.getLogger(__name__)

_supabase: Optional[Client] = None


def _get_supabase() -> Optional[Client]:
    """Inicialização lazy do Supabase — evita crash no import sem credenciais."""
    global _supabase
    if _supabase is not None:
        return _supabase
    if not config.SUPABASE_URL or not config.SUPABASE_KEY:
        logger.warning("Supabase não configurado; sync de milhas desabilitado.")
        return None
    _supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _supabase


async def notify_telegram(message: str) -> None:
    """Envia resumo silencioso matinal pelo bot do Telegram."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado, pulando notificação.")
        return

    chat_id = config.ADMIN_CHAT_ID
    if not chat_id:
        logger.warning("ADMIN_CHAT_ID não configurado; pulando notificação.")
        return

    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "disable_notification": True}

    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json=payload)
        except Exception as e:
            logger.error(f"Falha ao contatar Telegram API: {e}")


async def _sync_miles_async() -> None:
    """Lógica pesada assíncrona invocada pela Task do Celery."""
    supabase = _get_supabase()
    if supabase is None:
        logger.error("Supabase indisponível; abortando sync de milhas.")
        return

    logger.info("Iniciando rotina de raspagem e atualização de milhas...")
    scraper = MileageScraper()
    balances = await scraper.run_all()

    logger.info(f"Saldos extraídos: {balances}")

    user_id = "zaqueu_master_id"

    try:
        upsert_data = [
            {"user_id": user_id, "program": "smiles", "balance": balances["smiles"]},
            {"user_id": user_id, "program": "latam", "balance": balances["latam"]},
        ]

        response = supabase.table("MileWallet").upsert(upsert_data).execute()
        logger.info(f"Supabase MileWallet atualizado com sucesso: {response.data}")

        msg = (
            f"🌅 Bom dia, Comandante!\nSaldos atualizados na calada da noite:\n"
            f"✈️ Smiles: {balances['smiles']} milhas\n"
            f"✈️ Latam: {balances['latam']} pontos."
        )
        await notify_telegram(msg)

    except Exception as e:
        logger.error(f"Falha de I/O com banco Supabase: {e}")


@celery_app.task(name="workers.tasks.sync_mileage_wallets")
def sync_mileage_wallets():
    """
    Task síncrona de entrada do Celery.
    Isola e executa o event loop para as corrotinas de scrape assíncrono.
    """
    asyncio.run(_sync_miles_async())
