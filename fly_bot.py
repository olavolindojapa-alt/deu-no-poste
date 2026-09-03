import os
import subprocess
import sys
import time

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config import GRUPO_WHATSAPP, HORARIOS
from gerar_tabela import gerar_tabela
from scraper import scrape_resultados

GRUPO = os.environ.get("GRUPO_NOME", "").strip() or GRUPO_WHATSAPP
FUSO = ZoneInfo("America/Sao_Paulo")

ESTADO_ENVIO = "estado_fly.json"
ESTADO_PALPITE = "estado_palpite_fly.json"

DIA = ["PPT", "PTM", "PT", "PTV", "PTN", "COR"]
ALIASES = {"PTN": ["PTN", "FED"]}

MINUTOS_APOS = 10


def _agora_brt():
    return datetime.now(FUSO)


def _hoje_brt():
    return _agora_brt().date().isoformat()


def _carregar(path, padrao):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8-sig") as f:
                import json
                return json.load(f)
    except Exception as e:
        print(f"Erro ao ler {path}: {e}")
    return padrao


def _salvar(path, estado):
    try:
        import json
        with open(path, "w", encoding="utf-8") as f:
            json.dump(estado, f)
        print(f"Estado salvo em {path}")
    except Exception as e:
        print(f"Erro ao salvar {path}: {e}")


def _tem_resultado(dados, sorteio):
    for alias in ALIASES.get(sorteio, [sorteio]):
        resultados = dados["resultados"].get(alias, [])
        if any(r["milhar"] not in ("0000", "000") for r in resultados):
            return True
    return False


def _enviar_go(imagem=None, texto=None, legenda=None):
    env = os.environ.copy()
    env["GRUPO_NOME"] = GRUPO
    db_path = os.getenv("SESSION_DB", "")
    if db_path and not db_path.startswith("file:"):
        db_path = f"file:{db_path}?_pragma=foreign_keys(1)"
    if db_path:
        env["SESSION_DB"] = db_path
    if os.path.exists("bot") and os.access("bot", os.X_OK):
        cmd = ["./bot"]
    else:
        cmd = ["go", "run", "main.go"]
    if imagem:
        env["IMAGE_FILE"] = imagem
        if legenda:
            env["CAPTION"] = legenda
    if texto:
        env["MESSAGE_TEXT"] = texto
    print(f"Chamando: {' '.join(cmd)}")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        for linha in r.stderr.splitlines():
            if any(k in linha for k in ("sent successfully", "Failed", "failed", "Error")):
                print("STDERR:", linha)
    return r.returncode


def _enviar_sorteio(sorteio, dados):
    caminho = gerar_tabela()
    if not caminho:
        print(f"{sorteio}: falha ao gerar imagem.")
        return False
    legenda = f"*JOGO DO BICHO - {sorteio}*\n{dados['data']}"
    code = _enviar_go(imagem=caminho, legenda=legenda)
    return code == 0


def job_sorteio(sorteio):
    print(f"=== SORTEIO {sorteio} [{_agora_brt().strftime('%H:%M')}] ===")
    estado = _carregar(ESTADO_ENVIO, {"data": "", "enviados": []})
    hoje = _hoje_brt()
    if estado.get("data") != hoje:
        estado = {"data": hoje, "enviados": []}
    if sorteio in estado.get("enviados", []):
        print(f"{sorteio}: ja enviado hoje. Pulando.")
        return

    try:
        dados = scrape_resultados()
    except Exception as e:
        print(f"{sorteio}: erro no scraper: {e}")
        dados = None

    if dados and _tem_resultado(dados, sorteio):
        if _enviar_sorteio(sorteio, dados):
            estado.setdefault("enviados", []).append(sorteio)
            _salvar(ESTADO_ENVIO, estado)
            print(f"{sorteio}: enviado e marcado.")
        else:
            print(f"{sorteio}: falha ao enviar.")
    else:
        print(f"{sorteio}: resultado ainda nao saiu.")


def job_palpite():
    print(f"=== PALPITE [{_agora_brt().strftime('%H:%M')}] ===")
    estado = _carregar(ESTADO_PALPITE, {"data": "", "numeros": None})
    hoje = _hoje_brt()
    if estado.get("data") != hoje:
        estado = {"data": hoje, "numeros": None}
    if estado.get("numeros"):
        print("Palpite ja enviado hoje. Pulando.")
        return

    import random
    from datetime import time as dtime, timedelta as dtd

    # Palpite de 1 a 25
    nums = sorted(random.sample(range(1, 26), 2))
    numeros_texto = " e ".join(str(n) for n in nums)
    msg = (
        f"*PALPITE DO DIA* \U0001f340\n"
        f"Hoje tente os grupos:\n"
        f"\U0001f4b0 N\u00famero 1: *{nums[0]}*\n"
        f"\U0001f4b0 N\u00famero 2: *{nums[1]}*\n"
        "\n_Boa sorte no Jogo do Bicho!_ \U0001f3b4"
    )
    code = _enviar_go(texto=msg)
    if code == 0:
        estado["numeros"] = nums
        _salvar(ESTADO_PALPITE, estado)
        print("Palpite enviado e marcado.")
    else:
        print("Falha ao enviar palpite.")


def _garantir_sessao():
    db = os.getenv("SESSION_DB", "")
    if "whatsapp_session.db" not in db:
        return
    path = db.replace("file:", "").split("?_pragma")[0]
    if path and os.path.exists(path):
        return
    origem = "/app/whatsapp_session.db"
    if path and os.path.exists(origem):
        try:
            import shutil
            os.makedirs(os.path.dirname(path), exist_ok=True)
            shutil.copy(origem, path)
            print(f"Sessao copiada de {origem} para {path}")
        except Exception as e:
            print(f"Erro ao copiar sessao: {e}")


def main():
    print("=== BOT FLY.IO INICIADO, fuso:", FUSO, "===")
    _garantir_sessao()
    scheduler = BlockingScheduler(timezone=str(FUSO))

    # Palpite todos os dias as 06:00
    scheduler.add_job(job_palpite, CronTrigger(hour=6, minute=0, second=10, timezone=FUSO))

    # Resultados: cada sorteio +10min
    for sorteio, horario in HORARIOS.items():
        h, m = horario.split(":")
        minuto_envio = (int(m) + MINUTOS_APOS) % 60
        hora_envio = (int(h) + (int(m) + MINUTOS_APOS) // 60) % 24
        scheduler.add_job(
            job_sorteio,
            CronTrigger(hour=hora_envio, minute=minuto_envio, timezone=FUSO),
            args=[sorteio],
        )
        # reforco 5min depois (caso resultado nao tenha saido ainda)
        minuto_reforco = (minuto_envio + 5) % 60
        hora_reforco = (hora_envio + (minuto_envio + 5) // 60) % 24
        scheduler.add_job(
            job_sorteio,
            CronTrigger(hour=hora_reforco, minute=minuto_reforco, timezone=FUSO),
            args=[sorteio],
        )

    print("Agendamento configurado. Rodando 24h...")
    print("  Palpite: 06:00 BRT")
    for sorteio, horario in HORARIOS.items():
        print(f"  {sorteio}: {horario} -> envio ~{horario} +10min")

    scheduler.start()


if __name__ == "__main__":
    main()
