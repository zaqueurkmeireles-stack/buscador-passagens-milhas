import asyncio
import logging
import aiohttp
from celery import Celery
from celery.schedules import crontab
from supabase import create_client, Client
from scraper.engine import MileageScraper
from core.config import config

logger = logging.getLogger(__name__)

# Configuração da instância do Celery usando Redis
app = Celery(
    "travel_agent_tasks",
    broker=config.REDIS_URL,
    backend=config.REDIS_URL
)

# Configuração do Agendamento (Cron) - Todos os dias às 03:00 da manhã
app.conf.beat_schedule = {
    'sync-miles-every-day-3am': {
        'task': 'workers.tasks.sync_mileage_wallets',
        'schedule': crontab(hour=3, minute=0),
    },
}

# Inicialização da injeção do Supabase, aproveitando variáveis de configuração
supabase: Client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)

async def notify_telegram(message: str):
    """Envia resumo silencioso matinal pelo bot do Telegram."""
    if not config.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN não configurado, pulando notificação.")
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    # CHAT_ID do Zaqueu fictício (em prod virá do banco)
    chat_id = "ADMIN_CHAT_ID" 
    payload = {"chat_id": chat_id, "text": message, "disable_notification": True}
    
    async with aiohttp.ClientSession() as session:
        try:
            await session.post(url, json=payload)
        except Exception as e:
            logger.error(f"Falha ao contatar Telegram API: {e}")

async def _sync_miles_async():
    """Lógica pesada assíncrona invocada pela Task do Celery."""
    logger.info("Iniciando rotina de raspagem e atualização de milhas...")
    scraper = MileageScraper()
    balances = await scraper.run_all()
    
    logger.info(f"Saldos extraídos: {balances}")
    
    # Definido explicitamente o dono da carteira na Tabela
    user_id = "zaqueu_master_id"
    
    try:
        # Array de dicionários para o UPSERT em lote na tabela MileWallet
        upsert_data = [
            {"user_id": user_id, "program": "smiles", "balance": balances["smiles"]},
            {"user_id": user_id, "program": "latam", "balance": balances["latam"]}
        ]
        
        # O supabase executa um upsert. Garanta que a constraint user_id+program exista no schema.
        response = supabase.table("MileWallet").upsert(upsert_data).execute()
        logger.info(f"Supabase MileWallet atualizado com sucesso: {response.data}")
        
        # Disparo do resumo matinal
        msg = f"🌅 Bom dia, Comandante!\nSaldos atualizados na calada da noite:\n✈️ Smiles: {balances['smiles']} milhas\n✈️ Latam: {balances['latam']} pontos."
        await notify_telegram(msg)
        
    except Exception as e:
        logger.error(f"Falha de I/O com banco Supabase: {e}")

@app.task
def sync_mileage_wallets():
    """
    Task síncrona de entrada do Celery.
    Isola e executa o event loop para as corrotinas de scrape assíncrono.
    """
    asyncio.run(_sync_miles_async())
