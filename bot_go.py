import os
import subprocess
import sys

from config import GRUPO_WHATSAPP, HORARIOS, URL_RESULTADO
from scraper import scrape_resultados
from print_tela import tirar_print

SORTEIO = os.environ.get("SORTEIO", "").strip().upper()
GRUPO = os.environ.get("GRUPO_NOME", "").strip() or GRUPO_WHATSAPP

ARQUIVO_PNG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tabela.png")

def _obter_resultado(sorteio):
    try:
        dados = scrape_resultados()
    except Exception as e:
        print(f"[{sorteio}] Erro ao acessar site: {e}")
        return None
    if not dados:
        return None
    resultados = dados["resultados"].get(sorteio, [])
    tem = any(r["milhar"] not in ("0000", "000") for r in resultados)
    if not tem:
        return None
    return dados

def _rodar_go(imagem=None, texto=None, legenda=None):
    env = os.environ.copy()
    env["GRUPO_NOME"] = GRUPO
    cmd = ["go", "run", "main.go"]
    if imagem:
        env["IMAGE_FILE"] = imagem
        if legenda:
            env["CAPTION"] = legenda
    if texto:
        env["MESSAGE_TEXT"] = texto
    print(f"Chamando Go: {cmd}")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)
    return r.returncode

def run(sorteio):
    horario = HORARIOS.get(sorteio, "?")
    print(f"=== SORTEIO {sorteio} ===")
    dados = _obter_resultado(sorteio)
    if dados:
        print("Resultado disponivel. Gerando print e enviando imagem...")
        caminho = tirar_print(ARQUIVO_PNG)
        legenda = f"*JOGO DO BICHO - {sorteio}*\n{dados['data']}"
        code = _rodar_go(imagem=caminho, legenda=legenda)
        sys.exit(0 if code == 0 else 1)
    print("Resultado ainda nao saiu. Enviando aviso de atraso.")
    msg = (
        f"*JOGO DO BICHO - {sorteio}*\n"
        "O resultado ainda NÃO saiu.\n"
        f"Horário previsto: {horario}"
    )
    code = _rodar_go(texto=msg)
    sys.exit(0 if code == 0 else 1)

if __name__ == "__main__":
    sorteio = os.environ.get("SORTEIO", "").strip().upper()
    if not sorteio:
        print("SORTEIO nao definido")
        sys.exit(1)
    run(sorteio)
