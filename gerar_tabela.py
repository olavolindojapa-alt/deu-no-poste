import os
import sys

from PIL import Image, ImageDraw, ImageFont

from scraper import scrape_resultados


def _fonte(tamanho, bold=False):
    nome = "arialbd.ttf" if bold else "arial.ttf"
    for caminho in [
        "C:\\Windows\\Fonts\\" + nome,
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
        else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        try:
            return ImageFont.truetype(caminho, tamanho)
        except Exception:
            continue
    return ImageFont.load_default()


VERDE = (34, 139, 34)
BRANCO = (255, 255, 255)
CINZA = (245, 245, 245)
PRETO = (30, 30, 30)
DOURADO = (218, 165, 32)


def gerar_tabela(arquivo_saida=None):
    if arquivo_saida is None:
        arquivo_saida = "tabela.png"

    dados = scrape_resultados()
    if not dados:
        return None

    data_str = dados["data"]
    sorteios = dados["sorteios"]

    # Posicoes em ordem
    posicoes = set()
    for s in sorteios:
        for r in dados["resultados"].get(s, []):
            posicoes.add(r["posicao"])
    posicoes = sorted(posicoes, key=lambda x: int(x))

    tam_fonte_titulo = 30
    tam_fonte_data = 22
    tam_fonte_cab = 24
    tam_fonte_linha = 22
    pad = 12
    larg_col_pos = 70
    larg_col_dados = 180

    titulo_f = _fonte(tam_fonte_titulo, bold=True)
    data_f = _fonte(tam_fonte_data)
    cab_f = _fonte(tam_fonte_cab, bold=True)
    linha_f = _fonte(tam_fonte_linha)

    alt_titulo = titulo_f.getbbox("Ag")[3] + pad * 2
    alt_data = data_f.getbbox("Ag")[3] + pad
    alt_cab = cab_f.getbbox("Ag")[3] + pad * 2
    alt_linha = linha_f.getbbox("Ag")[3] + pad * 2

    larg_total = larg_col_pos + larg_col_dados * len(sorteios) + pad * 2
    altura_total = alt_titulo + alt_data + alt_cab + alt_linha * len(posicoes) + pad

    img = Image.new("RGB", (larg_total, altura_total), BRANCO)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, larg_total, alt_titulo + alt_data], fill=VERDE)
    draw.text((pad, pad), "JOGO DO BICHO - RESULTADOS", font=titulo_f, fill=DOURADO)
    draw.text((pad, alt_titulo), data_str, font=data_f, fill=BRANCO)

    y = alt_titulo + alt_data
    x_pos = pad
    draw.rectangle([x_pos, y, x_pos + larg_col_pos, y + alt_cab], fill=(60, 60, 60))
    draw.text((x_pos + 10, y + pad), "Pos", font=cab_f, fill=BRANCO)
    for i, s in enumerate(sorteios):
        x_dado = x_pos + larg_col_pos + i * larg_col_dados
        draw.rectangle([x_dado, y, x_dado + larg_col_dados, y + alt_cab], fill=(60, 60, 60))
        draw.text((x_dado + 10, y + pad), s, font=cab_f, fill=BRANCO)

    y += alt_cab
    for idx, pos in enumerate(posicoes):
        cor_fundo = CINZA if idx % 2 == 1 else BRANCO
        y_linha = y + idx * alt_linha

        draw.rectangle([0, y_linha, larg_total, y_linha + alt_linha], fill=cor_fundo)
        draw.text((x_pos + 10, y_linha + pad), str(pos), font=linha_f, fill=PRETO)

        for i, s in enumerate(sorteios):
            x_dado = x_pos + larg_col_pos + i * larg_col_dados
            res_s = dados["resultados"].get(s, [])
            r = next((x for x in res_s if x["posicao"] == pos), None)
            texto = "--"
            if r and r["milhar"] not in ("0000", "000"):
                texto = r["milhar"]
            draw.text((x_dado + 10, y_linha + pad), texto, font=linha_f, fill=PRETO)

    y_borda = alt_titulo + alt_data
    for i in range(len(sorteios) + 1):
        x = pad + larg_col_pos + (i - 1) * larg_col_dados if i > 0 else pad
        draw.line([x, y_borda, x, altura_total], fill=(0, 0, 0), width=1)

    img.save(arquivo_saida)
    return arquivo_saida


if __name__ == "__main__":
    caminho = gerar_tabela()
    if caminho:
        print(f"Tabela gerada: {caminho}")
    else:
        print("Falha ao gerar tabela.")
        sys.exit(1)
