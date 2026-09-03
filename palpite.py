import json
import os
import random
import sys

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from config import GRUPO_WHATSAPP
from bot_go import _rodar_go

GRUPO = os.environ.get("GRUPO_NOME", "").strip() or GRUPO_WHATSAPP
ESTADO_FILE = "estado_palpite.json"
FUSO = ZoneInfo("America/Sao_Paulo")

MIN = 1
MAX = 25

# Horario (BRT) do palpite: 06:00
HORA_PALPITE = 6
MINUTO_PALPITE = 0
# Janela de tentativa: das 06:00 ate 07:00 (tolerancia ao atraso do GitHub)
JANELA_FIM_HORA = 7
JANELA_FIM_MINUTO = 0


def gerar_palpite():
    return sorted(random.sample(range(MIN, MAX + 1), 2))


def _agora_brt():
    return datetime.now(FUSO)


def _hoje_brt():
    return _agora_brt().date().isoformat()


def _carregar_estado():
    if os.path.exists(ESTADO_FILE):
        try:
            with open(ESTADO_FILE, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            print(f"Nao consegui ler estado do palpite: {e}")
    return {"data": "", "numeros": None}


def _salvar_estado(estado):
    try:
        with open(ESTADO_FILE, "w", encoding="utf-8") as f:
            json.dump(estado, f)
    except Exception as e:
        print(f"Nao consegui salvar estado do palpite: {e}")


def _na_janela(agora):
    if agora.hour < HORA_PALPITE:
        return False
    if agora.hour > JANELA_FIM_HORA:
        return False
    if agora.hour == JANELA_FIM_HORA and agora.minute >= JANELA_FIM_MINUTO:
        return False
    return True


def _montar_mensagem(nums):
    return (
        "*PALPITE DO DIA* \U0001f340\n"
        f"Hoje tente os grupos:\n"
        f"\U0001f4b0 N\u00famero 1: *{nums[0]}*\n"
        f"\U0001f4b0 N\u00famero 2: *{nums[1]}*\n"
        "\n_Boa sorte no Jogo do Bicho!_ \U0001f3b4"
    )


def rodar_palpite():
    agora = _agora_brt()
    hoje = _hoje_brt()
    print(f"=== PALPITE {agora.strftime('%d/%m %H:%M')} BRT ===")

    if not _na_janela(agora):
        print(
            f"Palpite fora da janela de envio "
            f"({HORA_PALPITE}:{MINUTO_PALPITE:02d}-{JANELA_FIM_HORA}:{JANELA_FIM_MINUTO:02d} BRT)."
        )
        return

    estado = _carregar_estado()

    if estado.get("data") != hoje:
        print(f"Novo dia ({hoje}). Resetando palpite do dia.")
        estado = {"data": hoje, "numeros": None}

    if estado.get("numeros"):
        print("Palpite ja enviado hoje. Pulando.")
        return

    nums = gerar_palpite()
    print(f"=== PALPITE DO DIA ({hoje}) === Palpites gerados: {nums}")
    msg = _montar_mensagem(nums)
    code = _rodar_go(texto=msg)
    if code == 0:
        estado["numeros"] = nums
        _salvar_estado(estado)
        print("Palpite enviado com sucesso e marcado como enviado.")
    else:
        print("Falha ao enviar palpite.")
        sys.exit(1)


if __name__ == "__main__":
    rodar_palpite()
