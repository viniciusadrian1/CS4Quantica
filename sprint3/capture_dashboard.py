"""Captura telas do dashboard para o relatório (Playwright headless).

Pré-requisito: API (porta 8000) e Streamlit (porta 8501) no ar.
Gera: relatorio/dashboard_alerta.png
"""

from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8501"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1600, "height": 1400})
        page.goto(URL, wait_until="networkidle")
        page.wait_for_timeout(4000)

        # Aponta o replay para o início do cluster de sobrecorrente (linhas 231-245)
        spin = page.get_by_test_id("stNumberInputField")
        spin.fill("228")
        spin.press("Enter")
        page.wait_for_timeout(2500)
        page.get_by_text("↺ Reset").click()
        page.wait_for_timeout(2500)

        # Roda o replay pelo trecho anômalo e pausa no meio do cluster
        page.get_by_text("▶ Iniciar").click()
        page.wait_for_timeout(11000)
        page.get_by_text("⏸ Pausar").click()
        page.wait_for_timeout(3500)

        page.screenshot(path="relatorio/dashboard_alerta.png", full_page=False)
        browser.close()
    print("OK: relatorio/dashboard_alerta.png")


if __name__ == "__main__":
    main()
