import os
import json
import asyncio
import logging
from dotenv import load_dotenv
from playwright.async_api import async_playwright, Page, BrowserContext, Browser, Route
from playwright_stealth import Stealth

logger = logging.getLogger(__name__)

class ScrapingEngine:
    """
    Motor assíncrono base para os scrapers do Personal Travel & Mileage Manager.
    Implementa proteção Stealth, otimização de RAM e gestão de sessão via cookies.
    """
    
    def __init__(self, headless: bool = True):
        """Cofre de Credenciais (Vault): Carrega as variáveis de ambiente."""
        load_dotenv()
        self.headless = headless
        self.proxy_url = os.getenv("PROXY_URL")
        self.capsolver_api_key = os.getenv("CAPSOLVER_API_KEY")
        self.sessions_dir = "scraper/sessions"
        
        # Garante que o diretório de sessões exista
        os.makedirs(self.sessions_dir, exist_ok=True)
    
    async def _abort_unnecessary_resources(self, route: Route):
        """
        Otimização de RAM:
        Bloqueia o carregamento de imagens e fontes para acelerar a raspagem em background.
        """
        excluded_types = ["image", "media", "font"]
        if route.request.resource_type in excluded_types:
            await route.abort()
        else:
            await route.continue_()

    async def init_browser_context(self, p, airline_name: str, headless: bool = None):
        """
        Inicia o Chromium com stealth_async injetado para evitar detecção (Cloudflare/Datadome).
        Injeta Proxy se disponível e carrega sessão se existir.
        
        Args:
            p: Instância de async_playwright (passada pelo contexto 'async with')
            airline_name: Nome da companhia aérea (usado para localizar a sessão de cookies)
            headless: Se o browser deve rodar em modo invisível (sobrescreve o padrão da engine).
            
        Returns:
            Tuple[Browser, BrowserContext, Page]
        """
        is_headless = headless if headless is not None else self.headless
        launch_args = {
            "headless": is_headless,
            "args": ["--disable-blink-features=AutomationControlled"]
        }
        
        # Injeção dinâmica de proxy com tratamento robusto de autenticação
        if self.proxy_url:
            if "@" in self.proxy_url:
                # Formato http://user:pass@host:port
                prefix, host_port = self.proxy_url.split("://")
                auth, server = host_port.split("@")
                username, password = auth.split(":")
                launch_args["proxy"] = {
                    "server": f"{prefix}://{server}",
                    "username": username,
                    "password": password
                }
            else:
                launch_args["proxy"] = {"server": self.proxy_url}
            
        browser = await p.chromium.launch(**launch_args)
        
        context_args = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Gestão de Sessão (Cookies)
        session_file = os.path.join(self.sessions_dir, f"{airline_name}_cookies.json")
        if os.path.exists(session_file):
            context_args["storage_state"] = session_file
            
        context = await browser.new_context(**context_args)
        page = await context.new_page()
        
        # Proteção Stealth (mascarando navigator.webdriver, etc)
        stealth = Stealth()
        await stealth.apply_stealth_async(page)
        
        # Otimização de RAM: Bloquear imagens e fontes via roteamento
        await page.route("**/*", self._abort_unnecessary_resources)
        
        return browser, context, page

    async def save_session(self, context: BrowserContext, airline_name: str):
        """
        Salva o estado atual (cookies, local storage) para reaproveitamento em futuras execuções.
        """
        session_file = os.path.join(self.sessions_dir, f"{airline_name}_cookies.json")
        await context.storage_state(path=session_file)

class MileageScraper(ScrapingEngine):
    """
    Coordenador de raspagem de milhas para múltiplas companhias.
    Utilizado pelas tasks do Celery para atualização de saldos.
    """
    async def run_all(self):
        # TODO: Implementar a orquestração real das rotinas (smiles, latam, etc)
        # Por enquanto retorna valores dummy para não quebrar o fluxo
        logger.info("Executando run_all() do MileageScraper (Mock)...")
        return {"smiles": 0, "latam": 0}

