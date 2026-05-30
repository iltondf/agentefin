FROM python:3.12-slim

# tzdata: TZ correto para datas/observabilidade (America/Sao_Paulo).
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/Sao_Paulo

WORKDIR /app

# Dependências numa layer separada (aproveita cache de build).
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Código da aplicação.
COPY main.py ./
COPY financebot ./financebot

# Processo único; SEM porta de entrada (só conexões de saída: Telegram + API).
CMD ["python", "-m", "main"]
