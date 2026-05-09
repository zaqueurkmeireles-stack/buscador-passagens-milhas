FROM python:3.11-slim

# Define o diretório de trabalho padrão do contêiner
WORKDIR /app

# Instala dependências nativas vitais e o wget/gnupg pro ambiente do Playwright
# Usamos --no-install-recommends para evitar pacotes desnecessários que gastam RAM
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copia os requisitos e instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Comando vital: Instala os binários do Chromium e as dependências nativas
# Apenas Chromium para economizar RAM e disco
RUN playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

# Copia o resto do código da aplicação
COPY . .

# Comando Padrão
CMD ["python", "-m", "bot.main"]
