import sqlalchemy
from sqlalchemy import create_engine, text

db_url = "postgresql://postgres:7453049e137348f709a9@db.ahogdfcakmbxaortadik.supabase.co:5432/postgres"

try:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database();"))
        print(f"Conectado ao banco: {result.fetchone()[0]}")
        
        # List tables in public schema
        result = conn.execute(text("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public';"))
        print("Tabelas no schema public:")
        for row in result:
            print(row[0])
            
except Exception as e:
    print(f"Erro ao conectar via SQLAlchemy: {e}")
