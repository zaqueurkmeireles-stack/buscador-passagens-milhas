import asyncio
import logging
from core.agent_graph import agent_app

logging.basicConfig(level=logging.INFO)

async def simulate():
    initial_state = {
        "original_text": "quero ir para maceió em julho com milhas. somos em 3 pessoas.",
        "messages": [],
        "extracted_params": {},
        "rag_context": "",
        "mileage_balances": {},
        "final_response": ""
    }
    
    print("--- INICIANDO SIMULACAO DE REQUEST ---")
    try:
        final_state = await agent_app.ainvoke(initial_state)
        print("\n--- RESPOSTA FINAL ---")
        print(final_state.get("final_response"))
        print("\n--- PARAMETROS EXTRAIDOS ---")
        print(final_state.get("extracted_params"))
    except Exception as e:
        print(f"\n--- ERRO NA SIMULACAO ---")
        print(e)

if __name__ == "__main__":
    asyncio.run(simulate())
