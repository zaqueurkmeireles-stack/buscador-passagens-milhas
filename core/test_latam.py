import asyncio
from scraper.engine import ScrapingEngine
from scraper.routines.latam import LatamScraper

async def run_test():
    print("[Teste Vertical] A iniciar o motor base em modo headless (invisível)...")
    # headless=True para execução em background/VPS
    engine = ScrapingEngine(headless=True)
    scraper = LatamScraper(engine)

    print("[Teste Vertical] A arrancar com a pesquisa GRU -> LIS...")
    # Inserimos uma data futura segura (ex: Setembro de 2026) em tarifa pagante (Cash)
    await scraper.search_flight(
        origin="GRU",
        destination="LIS",
        date_str="15/09/2026",
        is_award=False
    )
    
    print("[Teste Vertical] Execução finalizada com sucesso.")

if __name__ == "__main__":
    asyncio.run(run_test())