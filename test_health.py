import asyncio
import sys
import logging

# Configuração de log para visualizar os erros
logging.basicConfig(level=logging.INFO)

from core.health_matrix import auditar_apis_e_redundancia

async def main():
    print("Executando Auditoria de APIs (Health Matrix)...")
    resultado = await auditar_apis_e_redundancia.ainvoke({})
    print("\n--- RESULTADO DA MATRIZ ---")
    for key, value in resultado.items():
        print(f"{key}: {value}")
    
if __name__ == "__main__":
    # Workaround para erro de Event Loop no Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
