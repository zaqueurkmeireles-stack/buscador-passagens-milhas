import os
import asyncio
from dotenv import load_dotenv
from core.health_matrix import get_redundant_llm
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

async def test_llms():
    print("Testando chaves LLM...")
    
    gemini_key = os.getenv("GOOGLE_GEMINI_API_KEY")
    print(f"Gemini Key: {gemini_key[:10]}...")
    
    try:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=gemini_key)
        res = await llm.ainvoke([HumanMessage(content="Hello")])
        print("GEMINI SUCESSO:", res.content)
    except Exception as e:
        print("GEMINI ERRO:", e)
        
    try:
        from core.health_matrix import auditar_apis_e_redundancia
        print("\nRodando matriz de saude:")
        matrix = await auditar_apis_e_redundancia.ainvoke({})
        print(matrix)
    except Exception as e:
        print("Erro matriz:", e)

if __name__ == "__main__":
    asyncio.run(test_llms())
