"""
Database Migrations — Travel Hacking Skill
==========================================
Script de criação/validação das tabelas necessárias para o sistema de
arbitragem de milhas. Executado automaticamente no startup do bot (init_db)
e pode ser rodado manualmente para migrar o schema.

Tabelas gerenciadas:
  - flight_alerts_log: Log anti-spam (deduplicação de alertas 24h)
  - alertas_voos: Alertas parametrizados do usuário (já criada via skill)
"""

import asyncio
import logging

import asyncpg

from core.config import config

logger = logging.getLogger(__name__)


# ============================================================
# DDL: Definições das tabelas
# ============================================================

DDL_FLIGHT_ALERTS_LOG = """
CREATE TABLE IF NOT EXISTS flight_alerts_log (
    id            BIGSERIAL     PRIMARY KEY,
    route_hash    TEXT          NOT NULL,
    alert_timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    details       JSONB
);
"""

DDL_FLIGHT_ALERTS_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_fal_route_hash
    ON flight_alerts_log (route_hash);
"""

DDL_ALERTAS_VOOS = """
CREATE TABLE IF NOT EXISTS alertas_voos (
    id                    SERIAL       PRIMARY KEY,
    chat_id_telegram      TEXT         NOT NULL,
    parametros_busca      JSONB        NOT NULL,
    preco_alvo_milhas     INT,
    preco_alvo_dinheiro   FLOAT,
    ativo                 BOOLEAN      DEFAULT TRUE,
    criado_em             TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
);
"""

DDL_ALERTAS_VOOS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_av_chat_id ON alertas_voos (chat_id_telegram);",
    "CREATE INDEX IF NOT EXISTS idx_av_ativo ON alertas_voos (ativo);",
]


# ============================================================
# Função principal de migração
# ============================================================
async def create_tables(conn: asyncpg.Connection = None) -> dict:
    """
    Cria ou valida todas as tabelas necessárias no Supabase/PostgreSQL.
    Pode receber uma conexão externa ou abrirá uma própria.

    Returns:
        dict com status de cada tabela criada/validada
    """
    close_conn = False
    status = {}

    if conn is None:
        if not config.DB_URL:
            logger.error("[Migrations] DB_URL não configurada.")
            return {"status": "erro", "mensagem": "DB_URL ausente no .env"}
        try:
            conn = await asyncpg.connect(config.DB_URL)
            close_conn = True
        except Exception as e:
            logger.error(f"[Migrations] Falha ao conectar: {e}")
            return {"status": "erro", "mensagem": str(e)}

    try:
        # --- flight_alerts_log ---
        await conn.execute(DDL_FLIGHT_ALERTS_LOG)
        await conn.execute(DDL_FLIGHT_ALERTS_LOG_INDEX)
        status["flight_alerts_log"] = "✅ OK"
        logger.info("[Migrations] Tabela flight_alerts_log validada.")

        # --- alertas_voos ---
        await conn.execute(DDL_ALERTAS_VOOS)
        for idx_sql in DDL_ALERTAS_VOOS_INDEXES:
            await conn.execute(idx_sql)
        status["alertas_voos"] = "✅ OK"
        logger.info("[Migrations] Tabela alertas_voos validada.")

        status["status"] = "sucesso"

    except Exception as e:
        logger.error(f"[Migrations] Erro ao executar DDL: {e}", exc_info=True)
        status["status"] = "erro"
        status["mensagem"] = str(e)

    finally:
        if close_conn:
            await conn.close()

    return status


# ============================================================
# Alias usado pelo bot/main.py → init_db()
# ============================================================
async def init_db():
    """Ponto de entrada chamado no startup do bot (bot/main.py)."""
    result = await create_tables()
    if result.get("status") == "sucesso":
        logger.info("[DB] Schema validado com sucesso.")
    else:
        logger.warning(f"[DB] Migração com problemas: {result}")
    return result


# ============================================================
# Execução direta (python -m database.migrations)
# ============================================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    )
    result = asyncio.run(create_tables())
    print("\n=== Resultado das Migrações ===")
    for k, v in result.items():
        print(f"  {k}: {v}")
