# ---------- ESTAGIO GO: compila os binarios a partir do codigo-fonte ----------
FROM golang:1.26 AS builder

WORKDIR /src

# go.mod/go.sum primeiro para aproveitar cache de dependencias
COPY go.mod go.sum ./
RUN go mod download

# copia o codigo-fonte e compila os dois binarios separadamente
COPY main.go ./
COPY login.go ./
RUN go build -o /out/bot main.go
RUN go build -o /out/logintool login.go

# ---------- IMAGEM FINAL PYTHON ----------
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# binarios compilados no estagio Go
COPY --from=builder /out/bot /app/bot
COPY --from=builder /out/logintool /app/logintool
RUN chmod +x /app/bot /app/logintool

COPY requirements.txt /app/
RUN pip install --no-cache-dir --timeout 120 -r requirements.txt

COPY config.py /app/
COPY bichos.py /app/
COPY scraper.py /app/
COPY gerar_tabela.py /app/
COPY fly_bot.py /app/

RUN mkdir -p /data

ENV BOT_FUSO=America/Sao_Paulo
ENV GRUPO_NOME="Resultado jogo do bicho"
ENV PYTHONIOENCODING=utf-8
ENV PYTHONUNBUFFERED=1
ENV SESSION_DB=/data/whatsapp_session.db

CMD ["python", "-u", "fly_bot.py"]
