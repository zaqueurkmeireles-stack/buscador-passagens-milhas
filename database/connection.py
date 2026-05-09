import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import config
from database.models import Base

logger = logging.getLogger(__name__)

# O SQLAlchemy nativamente precisa de uma connection string no formato postgresql+asyncpg://
db_url = config.DB_URL

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://")
elif not db_url:
    db_url = "sqlite+aiosqlite:///travel_agent.db"

# Inicializa o AsyncEngine
engine = create_async_engine(db_url, echo=False)

# Configura o session maker assíncrono
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def init_db():
    """
    Função assíncrona executada no startup para garantir que as
    tabelas declaradas no metadata sejam criadas no Supabase/DB.
    """
    try:
        async with engine.begin() as conn:
            logger.info("Verificando consistência estrutural do banco de dados...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tabelas inicializadas com sucesso.")
    except Exception as e:
        logger.error(f"Erro crasso ao inicializar banco de dados: {e}")
