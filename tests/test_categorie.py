"""Categorie e ambiguità: C6 (domanda indietro), C7 (righe incerte a parte). L'IA è finta e registra cosa riceve."""
import json
import re
from pathlib import Path

import pytest

from quid import calcolo, categorie, leggi, richiesta, risposta

FILE = Path(__file__).parent.parent / "prove" / "file"


class IAFinta:
    """Restituisce risposte scritte a mano e tiene ogni messaggio ricevuto (serve anche per la privacy, C9)."""
    def __init__(self, risposta):
        self.risposta, self.ricevuti = risposta, []

    def chiedi(self, sistema, utente):
        self.ricevuti.append(sistema + "\n" + utente)
        return self.risposta if isinstance(self.risposta, str) else json.dumps(self.risposta)


RISPOSTA_IA = {"ADDEBITO SDD ENEL ENERGIA SPA": {"categoria": "bollette", "certa": True},
               "ADDEBITO SDD A#A ENERGIA GAS": {"categoria": "bollette", "certa": True},   # l'IA vede A#A, non A2A
               "ADDEBITO SDD TIM SPA TELEFONO": {"categoria": "bollette", "certa": True},
               "AMAZON EU SARL": {"categoria": "bollette", "certa": False},
               re.sub(r"\d", "#", "PAGAMENTO CARTA 4532 **** **** 1234 ESSELUNGA MILANO"): {"categoria": "spesa", "certa": True},
               re.sub(r"\d", "#", "BONIFICO DA IT60X0542811101000000123456 STIPENDIO ROSSI SRL"): {"categoria": "stipendio", "certa": True}}
BOLLETTE = {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
            "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 10, "anno": 2026}}


@pytest.fixture(scope="module")
def conto():
    return leggi.leggi((FILE / "conto.csv").read_bytes(), "conto.csv")


# ---- C7: la riga incerta non entra nel numero e si vede a parte ----
def test_c07_amazon_incerta_fuori_dal_numero_e_mostrata_a_parte(conto):
    ia = IAFinta(RISPOSTA_IA)
    cat = categorie.classifica(conto.df["descrizione"], ia)
    ric = richiesta.valida(BOLLETTE, conto)
    r = risposta.componi(ric, calcolo.esegui(conto, ric, cat), conto, "it")
    assert "187,40 €" in r["frase"]
    assert [x["descrizione"] for x in r["incerte"]] == ["AMAZON EU SARL"]
    assert "AMAZON" not in r["frase"]


def test_c07_l_ia_riceve_le_descrizioni_senza_cifre_una_volta_sola(conto):
    ia = IAFinta(RISPOSTA_IA)
    cat = categorie.classifica(conto.df["descrizione"], ia)
    assert len(ia.ricevuti) == 1
    assert not any(c.isdigit() for c in ia.ricevuti[0].split("CATEGORIE:")[-1])
    assert cat["PAGAMENTO CARTA 4532 **** **** 1234 ESSELUNGA MILANO"] == ("spesa", True)


def test_c07_risposta_ia_strana_non_rompe_niente(conto):
    cat = categorie.classifica(conto.df["descrizione"], IAFinta({"AMAZON EU SARL": {"categoria": "crypto", "certa": True},
                                                                  "ENEL": "non so"}))
    assert cat["AMAZON EU SARL"] == ("altro", False)                       # categoria fuori elenco → incerta
    assert cat["ADDEBITO SDD ENEL ENERGIA SPA"] == ("altro", False)        # mancante → incerta
    assert categorie.classifica(conto.df["descrizione"], IAFinta("questo non è json"))["AMAZON EU SARL"] == ("altro", False)


def test_c07_in_inglese_la_categoria_e_tradotta(conto):
    cat = categorie.classifica(conto.df["descrizione"], IAFinta(RISPOSTA_IA))
    ric = richiesta.valida(BOLLETTE, conto)
    r = risposta.componi(ric, calcolo.esegui(conto, ric, cat), conto, "en")
    assert "on bills" in r["frase"] and "bollette" not in r["frase"] + r["ho_capito"]


# ---- C6: domanda indietro solo se il mese c'è in più anni ----
def test_c06_due_ottobre_domanda_indietro_senza_numero(conto):
    ric = richiesta.valida({**BOLLETTE, "periodo": {"mese": 10}}, conto)
    esito = calcolo.esegui(conto, ric, {})
    assert esito.domanda_indietro == {"mese": 10, "anni": [2025, 2026]} and esito.numero is None


def test_c06_un_solo_ottobre_risponde_subito(conto):
    solo_2026 = leggi.Tabella("conto", conto.df[conto.df["data"].dt.year == 2026].reset_index(drop=True))
    cat = categorie.classifica(solo_2026.df["descrizione"], IAFinta(RISPOSTA_IA))
    ric = richiesta.valida({**BOLLETTE, "periodo": {"mese": 10}}, solo_2026)
    r = risposta.componi(ric, calcolo.esegui(solo_2026, ric, cat), solo_2026, "it")
    assert r["domanda_indietro"] is None and "187,40 €" in r["frase"] and "ottobre 2026" in r["frase"]
