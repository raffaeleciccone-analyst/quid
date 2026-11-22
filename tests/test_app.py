"""Il server dietro la pagina: C16 (conversazione), C19 (inglese), C10-C11 (modo e anteprima), C15 via web.
L'IA è finta: le richieste che restituisce sono scritte a mano."""
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from nlda import privacy
from nlda.app import crea_app

FILE = Path(__file__).parent.parent / "prove" / "file"
BOLLETTE = {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
            "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 10, "anno": 2026}}


class IAFinta:
    esce_dal_pc = True

    def __init__(self):
        self.ricevuti, self.coda = [], []

    def chiedi(self, sistema, utente):
        self.ricevuti.append(utente)
        if utente.startswith("CATEGORIE:"):
            return json.dumps({privacy.senza_cifre(d): {"categoria": "bollette", "certa": True}
                               for d in ("ADDEBITO SDD ENEL ENERGIA SPA", "ADDEBITO SDD A2A ENERGIA GAS",
                                         "ADDEBITO SDD TIM SPA TELEFONO")})
        return json.dumps(self.coda.pop(0) if self.coda else {"tipo": "non_capito"})


@pytest.fixture
def web():
    ia = IAFinta()
    client = TestClient(crea_app(ia, modo="online"))
    r = client.post("/api/file", files={"file": ("conto.csv", (FILE / "conto.csv").read_bytes())})
    assert r.status_code == 200
    return client, ia


def _chiedi(client, testo, lingua="it"):
    return client.post("/api/domanda", json={"testo": testo, "lingua": lingua}).json()


# ---- C16: la conversazione ricorda e dice come ha capito; "Nuova domanda" riparte ----
def test_c16_e_a_novembre_continua_la_domanda_precedente(web):
    client, ia = web
    ia.coda = [BOLLETTE, {**BOLLETTE, "periodo": {"mese": 11, "anno": 2026}}]
    assert _chiedi(client, "Quanto ho speso in bollette a ottobre 2026?")["numero"] == 187.40
    r = _chiedi(client, "e a novembre?")
    assert r["numero"] == 190.60 and "novembre 2026" in r["ho_capito"]
    assert "RICHIESTA PRECEDENTE" in ia.ricevuti[-1] and '"mese": 10' in ia.ricevuti[-1]


def test_c16_dopo_nuova_domanda_non_ricorda(web):
    client, ia = web
    ia.coda = [BOLLETTE]
    _chiedi(client, "Quanto ho speso in bollette a ottobre 2026?")
    client.post("/api/nuova")
    r = _chiedi(client, "e a novembre?")
    assert "RICHIESTA PRECEDENTE" not in ia.ricevuti[-1] and r["esito"] == "non_capito"


def test_c06_scegliere_l_anno_risponde_senza_chiedere_all_ia(web):
    client, ia = web
    ia.coda = [{**BOLLETTE, "periodo": {"mese": 10}}]
    assert _chiedi(client, "Quanto ho speso in bollette a ottobre?")["domanda_indietro"]["anni"] == [2025, 2026]
    chiamate = len(ia.ricevuti)
    r = client.post("/api/anno", json={"anno": 2026, "lingua": "it"}).json()
    assert r["numero"] == 187.40 and len(ia.ricevuti) == chiamate


# ---- C19: in inglese lo stesso numero ----
def test_c19_domanda_in_inglese_stesso_numero(web):
    client, ia = web
    ia.coda = [BOLLETTE]
    r = _chiedi(client, "How much did I spend on bills in October 2026?", "en")
    assert r["frase"] == "In October 2026 you spent €187.40 on bills."


# ---- C10, C11: la pagina sa dove gira e cosa esce ----
def test_c10_c11_modo_e_anteprima(web):
    client, _ = web
    online = TestClient(crea_app(IAFinta(), modo="online")).get("/api/modo").json()
    locale = IAFinta()
    locale.esce_dal_pc = False                          # come Ollama
    pc = TestClient(crea_app(locale, modo="pc")).get("/api/modo").json()
    assert online["esce"] is True and pc["esce"] is False
    r = client.post("/api/file", files={"file": ("conto.csv", (FILE / "conto.csv").read_bytes())}).json()
    assert r["tipo"] == "conto" and r["righe"] == 151          # 23 mesi x 6 + 11 Amazon + 2 caffè and len(r["anteprima"]["testi"]) == 7


# ---- C15 / C14 via web: errori chiari, mai una pagina di errore ----
@pytest.mark.parametrize("nome,chiave", [("immagine.png", "formato"), ("conto_pdf_rotto.pdf", "saldi_non_tornano")])
def test_c15_file_sbagliato_errore_chiaro(nome, chiave):
    client = TestClient(crea_app(IAFinta(), modo="online"))
    r = client.post("/api/file", files={"file": (nome, (FILE / nome).read_bytes())})
    assert r.status_code == 400 and r.json()["errore"] == chiave


def test_domanda_senza_file_lo_dice():
    r = TestClient(crea_app(IAFinta(), modo="online")).post("/api/domanda", json={"testo": "ciao", "lingua": "it"})
    assert r.status_code == 400 and r.json()["errore"] == "nessun_file"


def test_ia_che_non_risponde_messaggio_chiaro_non_errore_del_server():
    class IAGiu:
        esce_dal_pc = True

        def chiedi(self, sistema, utente):
            raise OSError("HTTP Error 429: Too Many Requests")

    client = TestClient(crea_app(IAGiu(), modo="online"))
    r = client.post("/api/file", files={"file": ("conto.csv", (FILE / "conto.csv").read_bytes())})
    assert r.status_code == 200                                    # le categorie mancano: tutte incerte, niente crash
    r = client.post("/api/domanda", json={"testo": "Quanto ho speso?", "lingua": "it"})
    assert r.status_code == 503 and r.json()["errore"] == "ia_non_disponibile"
