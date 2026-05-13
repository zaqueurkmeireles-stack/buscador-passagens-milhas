import os
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from core.config import config
from database.models import Base

logger = logging.getLogger(__name__)

# Import lazy para evitar ciclos de importação
def _get_migrations():
    from database.migrations import create_tables
    return create_tables

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
    Também executa as migrações DDL da Skill de Arbitragem de Milhas.
    """
    try:
        async with engine.begin() as conn:
            logger.info("Verificando consistência estrutural do banco de dados...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tabelas ORM inicializadas com sucesso.")
    except Exception as e:
        logger.error(f"Erro crasso ao inicializar banco de dados: {e}")

    # Migrations adicionais: tabelas de arbitragem de milhas (DDL puro via asyncpg)
    try:
        create_tables = _get_migrations()
        result = await create_tables()
        if result.get("status") == "sucesso":
            logger.info("Tabelas de arbitragem de milhas validadas.")
        else:
            logger.warning(f"Migração de arbitragem com avisos: {result}")
    except Exception as e:
        logger.warning(f"Não foi possível executar migrações de arbitragem: {e}")
