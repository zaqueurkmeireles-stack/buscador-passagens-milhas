import os
import logging
import asyncio
import re
import json
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright_stealth import Stealth
from core.config import config

logger = logging.getLogger(__name__)

HEAL_HISTORY_FILE = "database/heal_history.json"

class APIKeyHealer:
    """
    Sistema de Self-Healing para API Keys.
    Recupera chaves expiradas ou banidas através de automação de navegador.
    """
    
    def __init__(self):
        self.browser_args = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        }
        if config.BRIGHTDATA_PROXY_URL:
            self.browser_args["proxy"] = {"server": config.BRIGHTDATA_PROXY_URL}

    def _should_attempt_heal(self, api_name: str) -> bool:
        """Verifica se já se passaram 7 dias desde a última tentativa para esta API."""
        if not os.path.exists(HEAL_HISTORY_FILE):
            return True
            
        try:
            with open(HEAL_HISTORY_FILE, "r") as f:
                history = json.load(f)
            
            last_attempt_str = history.get(api_name)
            if not last_attempt_str:
                return True
                
            last_attempt = datetime.fromisoformat(last_attempt_str)
            return datetime.now() > last_attempt + timedelta(days=7)
        except:
            return True

    def _record_heal_attempt(self, api_name: str):
        """Registra a data da tentativa atual."""
        history = {}
        if os.path.exists(HEAL_HISTORY_FILE):
            try:
                with open(HEAL_HISTORY_FILE, "r") as f:
                    history = json.load(f)
            except: pass
            
        history[api_name] = datetime.now().isoformat()
        
        os.makedirs(os.path.dirname(HEAL_HISTORY_FILE), exist_ok=True)
        with open(HEAL_HISTORY_FILE, "w") as f:
            json.dump(history, f)

    async def update_env_file(self, key_name: str, new_value: str):
        """Atualiza a chave no arquivo .env e na memória."""
        os.environ[key_name] = new_value
        env_path = ".env"
        
        if not os.path.exists(env_path):
            logger.error(f"Arquivo .env não encontrado em {os.getcwd()}")
            return

        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines = []
        found = False
        for line in lines:
            if line.startswith(f"{key_name}="):
                new_lines.append(f"{key_name}={new_value}\n")
                found = True
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"{key_name}={new_value}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        
        logger.info(f"✅ Chave {key_name} persistida no .env")

    async def recover_google_gemini_key(self) -> str:
        """Navega até o Google AI Studio para gerar uma nova chave."""
        if not os.getenv("GOOGLE_GEMINI_API_KEY"):
            logger.info("Ignorando recuperação de Gemini: Chave não está em uso (vazia no .env).")
            return ""

        if not self._should_attempt_heal("google_gemini"):
            logger.info("Recuperação Gemini ignorada: Cooldown de 7 dias ativo.")
            return ""

        self._record_heal_attempt("google_gemini")
        email = os.getenv("RECOVERY_EMAIL_PRIMARY")
        password = os.getenv("RECOVERY_PASSWORD")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self.browser_args)
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            stealth = Stealth()
            await stealth.apply_stealth_async(page)
            
            try:
                logger.info("Iniciando recuperação Gemini no Google AI Studio...")
                await page.goto("https://aistudio.google.com/app/apikey", wait_until="networkidle")
                
                # Lógica de Login Google (simplificada para o exemplo, em prod requer tratamento de cookies/2FA)
                if "signin" in page.url:
                    logger.info("Solicitando login no Google...")
                    await page.fill('input[type="email"]', email)
                    await page.click('#identifierNext')
                    await page.wait_for_timeout(2000)
                    await page.fill('input[type="password"]', password)
                    await page.click('#passwordNext')
                    await page.wait_for_load_state("networkidle")

                # Localizar botão de criar chave ou copiar chave existente
                # Esta parte depende da UI do Google AI Studio que muda frequentemente
                # Simulando extração:
                await page.wait_for_selector('button:has-text("Create API key")', timeout=30000)
                # ... lógica de clique e captura ...
                
                # Mock de captura para estrutura inicial
                new_key = "AIzaSy" + "..." # Aqui entraria a extração real via seletor
                
                # Se obtivermos a chave, atualizamos
                # await self.update_env_file("GOOGLE_GEMINI_API_KEY", new_key)
                # return new_key
                return ""
            except Exception as e:
                logger.error(f"Falha na recuperação Gemini: {e}")
                return ""
            finally:
                await browser.close()

    async def recover_amadeus_key(self) -> str:
        """Navega até o portal Amadeus for Developers."""
        if not config.AMADEUS_CLIENT_ID:
            return ""

        if not self._should_attempt_heal("amadeus"):
            logger.info("Recuperação Amadeus ignorada: Cooldown de 7 dias ativo.")
            return ""

        self._record_heal_attempt("amadeus")
        email = os.getenv("RECOVERY_EMAIL_PRIMARY")
        password = os.getenv("RECOVERY_PASSWORD")
        
        async with async_playwright() as p:
            # ... resto da implementação amadeus ...
            return ""

    async def recover_openai_key(self) -> str:
        """Navega até o painel da OpenAI para gerar nova chave."""
        if not os.getenv("OPENAI_API_KEY"):
            return ""

        if not self._should_attempt_heal("openai"):
            logger.info("Recuperação OpenAI ignorada: Cooldown de 7 dias ativo.")
            return ""

        self._record_heal_attempt("openai")
        email = os.getenv("RECOVERY_EMAIL_PRIMARY")
        password = os.getenv("RECOVERY_PASSWORD")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self.browser_args)
            page = await browser.new_page()
            try:
                await page.goto("https://platform.openai.com/api-keys")
                # Lógica de login e criação de chave
                return ""
            except Exception as e:
                logger.error(f"Erro OpenAI Healer: {e}")
                return ""
            finally:
                await browser.close()

    async def recover_duffel_key(self) -> str:
        """Navega até o painel da Duffel."""
        if not config.DUFFEL_API_KEY:
            return ""

        if not self._should_attempt_heal("duffel"):
            return ""

        self._record_heal_attempt("duffel")
        # ... lógica duffel ...
        return ""

    async def update_easypanel_vars(self, project: str, service: str, env_vars: dict):
        """
        Atualiza as variáveis diretamente no painel do Easypanel via automação.
        """
        email = os.getenv("RECOVERY_EMAIL_PRIMARY")
        password = os.getenv("RECOVERY_PASSWORD")
        url = "http://76.13.161.84:3000" # URL do Easypanel do usuário
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(**self.browser_args)
            page = await browser.new_page()
            try:
                await page.goto(f"{url}/login")
                # Assumindo campos de login padrão do Easypanel
                await page.fill('input[name="email"]', email)
                await page.fill('input[name="password"]', password)
                await page.click('button[type="submit"]')
                
                await page.goto(f"{url}/projects/{project}/app/{service}/env")
                
                # Lógica para editar o campo de texto de variáveis de ambiente
                content = await page.input_value('textarea')
                for k, v in env_vars.items():
                    if f"{k}=" in content:
                        content = re.sub(f"{k}=.*", f"{k}={v}", content)
                    else:
                        content += f"\n{k}={v}"
                
                await page.fill('textarea', content)
                await page.click('button:has-text("Save")')
                await page.click('button:has-text("Deploy")')
                logger.info(f"🚀 Easypanel atualizado e Redirecionado para Deploy: {service}")
            except Exception as e:
                logger.error(f"Erro ao atualizar Easypanel: {e}")
            finally:
                await browser.close()

# Instância global
healer = APIKeyHealer()
