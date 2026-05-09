import asyncio
from scraper.engine import ScrapingEngine
from scraper.routines.latam import LatamScraper

async def run_test():
    print("[Teste Vertical] A iniciar o motor base com o ecrã visível...")
    # headless=False é crucial aqui para podermos ver os movimentos do robô
    engine = ScrapingEngine(headless=False)
    scraper = LatamScraper(engine)

    print("[Teste Vertical] A arrancar com a pesquisa GRU -> LIS...")
    # Inserimos uma data futura segura (ex: Setembro de 2026) em tarifa pagante (Cash)
    await scraper.search_flight(
        origin="GRU",
        destination="LIS",
        date_str="15/09/2026",
        is_award=False
    )
    
    input("[Teste Vertical] Execução finalizada. Verifique o navegador e pressione Enter aqui para fechar...")

if __name__ == "__main__":
    asyncio.run(run_test())