"""La pagina vera in un browser vero (Chrome già installato, guidato da Playwright): C18 telefono, C19 inglese.
L'IA è finta, il server è quello vero. Se Playwright non c'è, i test si saltano (e lo dicono)."""
import json
import threading
import time
from pathlib import Path

import pytest
import uvicorn

from nlda import privacy
from nlda.app import crea_app

playwright = pytest.importorskip("playwright.sync_api", reason="Playwright non installato: pip install playwright")
FILE = Path(__file__).parent.parent / "prove" / "file"
BOLLETTE = {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
            "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 10, "anno": 2026}}


class IAFinta:
    esce_dal_pc = True

    def chiedi(self, sistema, utente):
        if utente.startswith("CATEGORIE:"):
            return json.dumps({privacy.senza_cifre(d): {"categoria": "bollette", "certa": True}
                               for d in ("ADDEBITO SDD ENEL ENERGIA SPA", "ADDEBITO SDD A2A ENERGIA GAS",
                                         "ADDEBITO SDD TIM SPA TELEFONO")})
        return json.dumps(BOLLETTE)


@pytest.fixture(scope="module")
def indirizzo():
    server = uvicorn.Server(uvicorn.Config(crea_app(IAFinta(), modo="online"), host="127.0.0.1", port=8799, log_level="error"))
    threading.Thread(target=server.run, daemon=True).start()
    while not server.started:
        time.sleep(0.05)
    yield "http://127.0.0.1:8799/"
    server.should_exit = True


@pytest.fixture(scope="module")
def browser():
    with playwright.sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        yield b
        b.close()


def _domanda(pagina, testo):
    pagina.fill("#domanda", testo)
    pagina.click("#barra button[type=submit]")
    pagina.wait_for_selector(".risposta .frase")
    return pagina.inner_text(".risposta .frase")


def test_c18_telefono_390_niente_scorrimento_di_lato(indirizzo, browser):
    pagina = browser.new_page(viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True)
    pagina.goto(indirizzo)
    pagina.set_input_files("#file", str(FILE / "conto.csv"))
    pagina.wait_for_selector("#barra:not([hidden])")
    assert "187,40 €" in _domanda(pagina, "Quanto ho speso in bollette a ottobre 2026?")
    pagina.click("details.come summary")                                  # i controlli si aprono e si chiudono
    assert pagina.is_visible("details.come code")
    # si misura con TUTTO aperto: la riga di codice lunga sta dentro "come l'ho calcolato" (era il difetto vero)
    pagina.evaluate("document.querySelectorAll('details').forEach(d => d.open = true)")
    larghezza = pagina.evaluate("document.documentElement.scrollWidth")
    assert larghezza <= 390, f"la pagina scorre di lato: {larghezza}px"
    pagina.click("details.come summary")
    assert not pagina.is_visible("details.come code")
    pagina.close()


def test_c19_pulsante_en_pagina_in_inglese_stesso_numero(indirizzo, browser):
    pagina = browser.new_page()
    pagina.goto(indirizzo)
    pagina.click("[data-lingua=en]")
    assert pagina.inner_text(".carica h1") == "Upload your file"
    pagina.set_input_files("#file", str(FILE / "conto.csv"))
    pagina.wait_for_selector("#barra:not([hidden])")
    assert pagina.get_attribute("#domanda", "placeholder") == "Ask a question about your file…"
    assert _domanda(pagina, "How much did I spend on bills in October 2026?") == "In October 2026 you spent €187.40 on bills."
    pagina.close()
