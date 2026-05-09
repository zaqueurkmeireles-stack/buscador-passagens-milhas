import asyncio
import logging
from playwright.async_api import async_playwright, TimeoutError
from scraper.engine import ScrapingEngine

logger = logging.getLogger(__name__)

class LatamScraper(ScrapingEngine):
    """
    Scraper para a LATAM Airlines via Playwright.
    Herda proteção Stealth, otimização e gestão de cookies do ScrapingEngine.
    """
    
    def __init__(self, engine: ScrapingEngine = None):
        # Permite injetar uma engine (para testes) ou criar uma nova por defeito
        if engine:
            self.headless = engine.headless
            self.proxy_url = engine.proxy_url
            self.sessions_dir = engine.sessions_dir
            self.capsolver_api_key = engine.capsolver_api_key
        else:
            super().__init__()
    
    async def search_flight(self, origin: str, destination: str, date_str: str, is_award: bool):
        """
        Orquestra a busca inicial de passagem (dinheiro ou milhas).
        """
        async with async_playwright() as p:
            # 1. Inicia o contexto do browser herdando a proteção
            logger.info("Iniciando browser engine para Latam...")
            browser, context, page = await self.init_browser_context(p, airline_name="latam", headless=False)
            
            try:
                # 2. Acessa a página inicial
                logger.info("Acessando a página inicial da Latam...")
                await page.goto("https://www.latamairlines.com/br/pt", wait_until="domcontentloaded")
                
                # 3. Tratamento de Pop-ups (Cookies e Ofertas)
                try:
                    # Timeout curto de 4 segundos para evitar atrasar o motor
                    logger.info("Verificando pop-ups/banners bloqueantes...")
                    
                    # Seletores genéricos para botões de aceitar cookies ou fechar modais
                    accept_selectors = (
                        "button:has-text('Aceitar'), "
                        "button:has-text('Aceitar todos'), "
                        "button:has-text('Fechar'), "
                        "button[id*='cookie'], "
                        "[aria-label*='Fechar'], "
                        "[aria-label*='Close']"
                    )
                    
                    cookie_button = page.locator(accept_selectors).first
                    await cookie_button.click(timeout=4000)
                    logger.info("Pop-up fechado com sucesso.")
                    
                except TimeoutError:
                    # Se não houver pop-up nos primeiros segundos, prossegue silenciosamente
                    logger.info("Nenhum pop-up detetado. Seguindo o fluxo principal.")
                except Exception as e:
                    logger.debug(f"Erro menor ao tentar fechar pop-up: {e}")
                
                # 1. Origem (IATA)
                logger.info(f"Preenchendo Origem: {origin}")
                origin_input = page.locator("input[id*='Origin'], input[name*='origin'], input[aria-label*='Origem']").first
                await origin_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(origin, delay=100) # Simula digitação humana
                # Aguarda o dropdown e força o clique
                origin_option = page.locator(f"li:has-text('{origin}'), button:has-text('{origin}'), span:has-text('{origin}')").first
                await origin_option.wait_for(state="visible", timeout=10000)
                await origin_option.click()
                
                # 2. Destino (IATA)
                logger.info(f"Preenchendo Destino: {destination}")
                dest_input = page.locator("input[id*='Destination'], input[name*='destination'], input[aria-label*='Destino']").first
                await dest_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(destination, delay=100)
                dest_option = page.locator(f"li:has-text('{destination}'), button:has-text('{destination}'), span:has-text('{destination}')").first
                await dest_option.wait_for(state="visible", timeout=10000)
                await dest_option.click()
                
                # 3. Data de Ida
                logger.info(f"Injetando Data: {date_str}")
                date_input = page.locator("input[id*='Departure'], input[name*='departure'], input[aria-label*='Data'], input[placeholder*='DD/MM']").first
                await date_input.click()
                await page.keyboard.press("Control+A")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(date_str, delay=100)
                await page.keyboard.press("Enter")
                
                # 4. Toggle Award/Dinheiro
                if is_award:
                    logger.info("Marcando opção de emissão com Milhas (Award)...")
                    award_toggle = page.locator("label:has-text('Pontos'), label:has-text('Milhas'), input[id*='redeem']").first
                    await award_toggle.click()
                
                # 5. Submissão
                logger.info("Submetendo pesquisa...")
                submit_btn = page.locator("button:has-text('Buscar'), button:has-text('Procurar'), button:has-text('Search'), button[id*='btnSearch']").first
                await submit_btn.click()
                
                # 6. Espera pelos Resultados (Cartões de Voo)
                logger.info("Aguardando carregamento da grid de resultados e libertação dos preços base...")
                # A Latam usa listas ou divs para os cartões de voo (flight-info, flight-card)
                flight_cards_selector = "li.flight-card, div.flight-container, div[data-testid='flight-info'], ol > li"
                await page.wait_for_selector(flight_cards_selector, timeout=45000)
                
                # Contagem de resultados (Modo de Teste)
                flight_cards = page.locator(flight_cards_selector)
                count = await flight_cards.count()
                print(f"[TEST MODE] Total de voos encontrados no ecrã para a rota {origin}->{destination}: {count}")

                
            except Exception as e:
                logger.error(f"Erro crítico durante a navegação Latam: {e}")
                raise
            finally:
                # Garante que as portas são fechadas e a memória é liberada no master thread
                await context.close()
                await browser.close()
