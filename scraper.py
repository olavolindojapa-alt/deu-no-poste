import requests
from bs4 import BeautifulSoup

from config import URL_RESULTADO
from bichos import BICHOS


def scrape_resultados():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(URL_RESULTADO, headers=headers, timeout=15)
    resp.raise_for_status()
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")
    table = soup.find("table")
    if not table:
        return None

    caption = table.find("caption")
    data_str = caption.get_text(strip=True) if caption else ""

    headers_row = table.find("thead")
    sorteios = []
    for th in headers_row.find_all("th"):
        text = th.get_text(strip=True)
        if text:
            sorteios.append(text)

    tbody = table.find("tbody")
    resultados = {s: [] for s in sorteios}

    for tr in tbody.find_all("tr"):
        tds = tr.find_all("td")
        numero = tds[0].get_text(strip=True)
        for i, s in enumerate(sorteios):
            td = tds[i + 1]
            title = td.get("title", "0")
            link = td.find("a")
            if link:
                milhar = link.get_text(strip=True)
            else:
                milhar = td.get_text(strip=True).split("-")[0]

            texto_completo = td.get_text(strip=True)
            partes = texto_completo.split("-")
            if len(partes) == 2:
                milhar, grupo = partes
            else:
                milhar = partes[0]
                grupo = "0"

            grupo_num = int(grupo) if grupo.isdigit() else 0
            bicho = BICHOS.get(grupo_num, "?") if grupo_num > 0 else "Aguardando"

            resultados[s].append({
                "posicao": numero,
                "milhar": milhar,
                "grupo": grupo_num,
                "bicho": bicho,
            })

    return {"data": data_str, "sorteios": sorteios, "resultados": resultados}


def formatar_mensagem(dados):
    if not dados:
        return "Nenhum resultado encontrado."

    linhas = []
    linhas.append(f"*RESULTADO DO JOGO DO BICHO*")
    linhas.append(f"*{dados['data']}*")
    linhas.append("")

    for s in dados["sorteios"]:
        resultados_s = dados["resultados"][s]
        tem_resultado = any(r["milhar"] not in ("0000", "000") for r in resultados_s)
        if not tem_resultado:
            continue

        linhas.append(f"*{s}*")
        for r in resultados_s:
            if r["milhar"] in ("0000", "000"):
                continue
            linhas.append(f"  {r['posicao']}o: *{r['milhar']}* - {r['bicho']}")
        linhas.append("")

    linhas.append("_Fonte: ojogodobicho.com_")
    return "\n".join(linhas)


if __name__ == "__main__":
    dados = scrape_resultados()
    if dados:
        print(formatar_mensagem(dados))
    else:
        print("Erro ao buscar resultados.")
