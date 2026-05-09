import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from core.config import config
from bot.handlers.natural_language import router as nl_router
from database.connection import init_db

# Configurações iniciais de Log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicialização do Bot e Dispatcher usando as credenciais extraídas via config
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Injeta a inteligência de linguagem natural (Agentic Workflow) no bot
dp.include_router(nl_router)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Comando base de boas vindas e acionamento do agente."""
    await message.reply("Sistemas online, Comandante. Pronto para buscar passagens e monitorar milhas.")

async def on_startup():
    """Hook ativado no instante em que o bot é ligado."""
    logger.info(">>> Iniciando inicialização da infraestrutura do Personal Travel AI Agent...")
    # Chamada obrigatória para forçar o metadata das tabelas no Supabase
    await init_db()
    logger.info(">>> Banco de dados validado e conectado.")

async def main():
    """Função de entrada do Event Loop."""
    # Registra o evento de startup
    dp.startup.register(on_startup)
    
    logger.info("Iniciando o Polling do Telegram...")
    # Mantém o aiogram rodando as requisições assíncronas
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot desligado pelo painel de controle.")
