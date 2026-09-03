FROM golang:1.26 AS gostage
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -o /bot main.go && \
    CGO_ENABLED=0 go build -o /logintool login.go

FROM python:3.11-slim
WORKDIR /app

# Instalar dependencias de sistema (fontes para Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Copiar binarios Go
COPY --from=gostage /bot /app/bot
COPY --from=gostage /logintool /app/logintool

# Python
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Codigo do bot (sem secrets)
COPY config.py /app/
COPY bichos.py /app/
COPY scraper.py /app/
COPY gerar_tabela.py /app/
COPY fly_bot.py /app/
COPY login.go /app/
COPY main.go /app/

# Volume persistente da sessao
RUN mkdir -p /data

ENV BOT_FUSO=America/Sao_Paulo
ENV GRUPO_NOME=Resultado jogo do bicho
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV SESSION_DB=/data/whatsapp_session.db

CMD ["python", "-u", "fly_bot.py"]
