FROM python:3.11-slim

# Define o diretório de trabalho padrão do contêiner
WORKDIR /app

# Instala dependências nativas vitais e o wget/gnupg pro ambiente do Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Copia os requisitos e instala dependências do Python
# (Assumindo que o requirements.txt já exista no projeto)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Comando vital: Instala os binários do Chromium e as dependências nativas
# do Linux exigidas pelo Playwright para que o scraper rode em modo headless no Easypanel
RUN playwright install --with-deps chromium

# Copia o resto do código da aplicação
COPY . .

# Comando Padrão
CMD ["python", "-m", "bot.main"]
