FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

COPY bot /app/bot
COPY logintool /app/logintool
RUN chmod +x /app/bot /app/logintool

COPY requirements.txt /app/
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY config.py /app/
COPY bichos.py /app/
COPY scraper.py /app/
COPY gerar_tabela.py /app/
COPY fly_bot.py /app/
COPY whatsapp_session.db /app/whatsapp_session.db

RUN mkdir -p /data

ENV BOT_FUSO=America/Sao_Paulo
ENV GRUPO_NOME="Resultado jogo do bicho"
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV SESSION_DB=/data/whatsapp_session.db

CMD ["python", "-u", "fly_bot.py"]
