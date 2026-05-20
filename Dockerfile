# Usa uma imagem Python otimizada
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Instala dependências de sistema essenciais para o banco de dados e navegadores
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instala todas as bibliotecas Python necessárias de uma vez só
# Isso elimina a dependência do arquivo requirements.txt externo
RUN pip install --no-cache-dir \
    aiogram \
    celery \
    redis \
    supabase \
    langgraph \
    amadeus \
    google-generativeai==0.8.4 \
    playwright \
    playwright-stealth \
    python-dotenv \
    asyncpg \
    psycopg2-binary \
    requests

# Instala os binários do Chromium e suas dependências de sistema
RUN playwright install chromium && playwright install-deps chromium

# Copia o código da aplicação para o contêiner
COPY . .

# Comando para iniciar o bot
CMD ["python", "-m", "bot.main"]