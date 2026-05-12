import asyncio
import sys
from scraper.engine import ScrapingEngine
from scraper.routines.latam import LatamScraper

async def run_test():
    print('[Teste Vertical] A iniciar o motor base...')
    engine = ScrapingEngine(headless=True)
    scraper = LatamScraper(engine)

    print('[Teste Vertical] A pesquisar GRU -> LIS para 15/09/2026...')
    try:
        await scraper.search_flight(
            origin='GRU',
            destination='LIS',
            date_str='15/09/2026',
            is_award=False
        )
    except Exception as e:
        print(f'[ERRO] Ocorreu um problema: {e}')
    
    print('[Teste Vertical] Fim. Verifique o log para detalhes...')

if __name__ == '__main__':
    asyncio.run(run_test())
