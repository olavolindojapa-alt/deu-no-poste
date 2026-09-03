import json
import os
import sys
import time

from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

from config import GRUPO_WHATSAPP, HORARIOS
from bot_go import ARQUIVO_PNG, _obter_resultado, _rodar_go
from print_tela import tirar_print

GRUPO = os.environ.get("GRUPO_NOME", "").strip() or GRUPO_WHATSAPP
ESTADO_FILE = "estado_envios.json"
FUSO = ZoneInfo("America/Sao_Paulo")

DIA = ["PPT", "PTM", "PT", "PTV", "PTN", "COR"]

ALIASES = {
    "PTN": ["PTN", "FED"],
}

MINUTOS_APRES_ENVIO = 10
# Janela maxima para tentar enviar um sorteio (evita reenvio em horas espalhadas
# caso o estado nao seja salvo a tempo). Cada sorteio so e tentado a partir de
# +10min do horario previsto ate o fim do dia (folga grande tolera atraso do
# GitHub Actions e atraso real da publicacao do resultado).
JANELA_MAX_MIN = 6 * 60


def _tem_resultado(dados, sorteio):
    for alias in ALIASES.get(sorteio, [sorteio]):
        resultados = dados["resultados"].get(alias, [])
        if any(r["milhar"] not in ("0000", "000") for r in resultados):
            return True
    return False


def _agora_brt():
    return datetime.now(FUSO)


def _hoje_brt():
    return _agora_brt().date().isoformat()


def _hora_min(sorteio):
    h, m = HORARIOS[sorteio].split(":")
    return int(h), int(m)


def _pode_enviar(sorteio):
    agora = _agora_brt()
    h, m = _hora_min(sorteio)
    hora_prevista = agora.replace(hour=h, minute=m, second=0, microsecond=0)
    inicio = hora_prevista + timedelta(minutes=MINUTOS_APRES_ENVIO)
    # Nao deixar a janela cruzar a meia-noite (cada sorteio so no seu dia)
    meia_noite = agora.replace(hour=23, minute=59, second=59, microsecond=0)
    fim = hora_prevista + timedelta(minutes=JANELA_MAX_MIN)
    if fim > meia_noite:
        fim = meia_noite
    if agora < inicio:
        print(f"{sorteio}: horario previsto {HORARIOS[sorteio]}, margem ate {inicio.strftime('%H:%M')}. Aguardando.")
        return False
    if agora > fim:
        print(f"{sorteio}: janela de envio de {HORARIOS[sorteio]} ja passou (depois de {fim.strftime('%H:%M')}). Pulando.")
        return False
    print(f"{sorteio}: dentro da janela de envio ({inicio.strftime('%H:%M')}-{fim.strftime('%H:%M')}).")
    return True


def _carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"Nao consegui ler estado: {e}")
    return {"data": "", "enviados": []}


def _salvar_estado(estado):
    try:
        with open(ESTADO_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"Nao consegui salvar estado: {e}")


def rodar_todos():
    agora = _agora_brt()
    print(f"=== ACOMPANHANTE {agora.strftime('%d/%m %H:%M')} BRT ===")
    hoje = _hoje_brt()
    estado = _carregar_estado()

    if estado.get("data") != hoje:
        print(f"Novo dia ({hoje}). Resetando envios.")
        estado = {"data": hoje, "enviados": []}

    falhas = []
    for sorteio in DIA:
        if sorteio in estado.get("enviados", []):
            print(f"{sorteio}: ja enviado hoje. Pulando.")
            continue

        if not _pode_enviar(sorteio):
            continue

        print(f"--- {sorteio} ---")
        dados = _obter_resultado(sorteio)
        if dados and not _tem_resultado(dados, sorteio):
            dados = None
        if dados:
            print(f"Resultado disponivel para {sorteio}. Enviando imagem...")
            caminho = tirar_print(ARQUIVO_PNG)
            legenda = f"*JOGO DO BICHO - {sorteio}*\n{dados['data']}"
            code = _rodar_go(imagem=caminho, legenda=legenda)
            if code == 0:
                estado.setdefault("enviados", []).append(sorteio)
                _salvar_estado(estado)
                print(f"{sorteio}: imagem enviada com sucesso e marcada como enviada.")
            else:
                falhas.append(sorteio)
        else:
            print(f"{sorteio}: resultado ainda nao saiu.")
        time.sleep(2)

    if falhas:
        print(f"Falhas ao enviar: {falhas}")
        sys.exit(1)
    print("Acompanhante concluido.")


if __name__ == "__main__":
    rodar_todos()