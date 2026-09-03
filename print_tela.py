import os
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import URL_RESULTADO


def tirar_print(arquivo_saida=None, escala=3):
    if arquivo_saida is None:
        pasta = os.path.dirname(os.path.abspath(__file__))
        arquivo_saida = os.path.join(pasta, "tabela.png")

    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--hide-scrollbars")
    options.add_argument(f"--force-device-scale-factor={escala}")
    options.add_argument("--window-size=1400,1600")

    driver = webdriver.Chrome(options=options)
    driver.set_window_size(1400, 1600)

    try:
        driver.get(URL_RESULTADO)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table.twelve thead"))
        )
        time.sleep(1)

        driver.execute_script(
            """
            document.querySelectorAll(
                '.watermark, [class*="watermark"], div[style*="z-index"], .table-wrap div'
            ).forEach(function(el){ el.style.display='none'; });
            """
        )
        time.sleep(0.8)

        tabela = driver.find_element(By.CSS_SELECTOR, "table.twelve")
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", tabela
        )
        time.sleep(1)

        with open(arquivo_saida, "wb") as f:
            f.write(tabela.screenshot_as_png)

        return arquivo_saida
    finally:
        driver.quit()
