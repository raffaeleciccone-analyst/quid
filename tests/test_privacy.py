"""Privacy e percorso domanda → risposta: C9, C10, C11 (e C20 dal lato IA). L'IA è finta e registra tutto ciò che riceve."""
import json
import re
from pathlib import Path

import pytest

from nlda import categorie, domanda, ia, leggi, privacy

FILE = Path(__file__).parent.parent / "prove" / "file"
C1 = "Quanto ho speso in bollette a ottobre 2026?"
RICHIESTA_C1 = {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
                "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 10, "anno": 2026}}


class IAFinta:
    esce_dal_pc = True

    def __init__(self, *risposte):
        self.risposte, self.ricevuti = list(risposte), []

    def chiedi(self, sistema, utente):
        self.ricevuti.append(sistema + "\n" + utente)
        r = self.risposte.pop(0) if self.risposte else {}
        return r if isinstance(r, str) else json.dumps(r)


def _categorie_finte(conto):
    voci = {privacy.senza_cifre(d): {"categoria": "bollette", "certa": True}
            for d in conto.df.descrizione.unique() if re.search("ENEL|A2A|TIM", d)}
    return voci


@pytest.fixture(scope="module")
def conto():
    return leggi.leggi((FILE / "conto.csv").read_bytes(), "conto.csv")


def _cose_del_file_che_non_devono_uscire(conto):
    vietate = {"0542811101000000123456", "IT60X", "4532", "1234"}                  # IBAN e carta
    for x in conto.df.importo.abs().unique():
        vietate |= {f"{x:.2f}", f"{x:.2f}".replace(".", ","), f"{x:,.2f}".replace(",", "")}
    for d in conto.df.data.unique():
        d = d if hasattr(d, "strftime") else __import__("pandas").Timestamp(d)
        vietate |= {d.strftime("%d/%m/%Y"), d.strftime("%Y-%m-%d"), d.strftime("%d/%m")}
    return vietate


# ---- C9: verso l'IA online non esce nessun importo, data, IBAN o numero di carta ----
def test_c09_nulla_di_privato_esce_verso_l_ia(conto):
    finta = IAFinta(_categorie_finte(conto), RICHIESTA_C1)
    cat = categorie.classifica(conto.df.descrizione, finta)
    r = domanda.rispondi(conto, C1, finta, cat, None, "it")
    assert "187,40 €" in r["frase"]
    uscito = "\n".join(finta.ricevuti)
    assert "ENEL ENERGIA" in uscito
    trovate = [v for v in _cose_del_file_che_non_devono_uscire(conto) if v in uscito]
    assert trovate == [], trovate


def test_c09_anche_la_domanda_che_segue_non_porta_dati_del_file(conto):
    finta = IAFinta(_categorie_finte(conto), RICHIESTA_C1, {**RICHIESTA_C1, "periodo": {"mese": 11, "anno": 2026}})
    cat = categorie.classifica(conto.df.descrizione, finta)
    primo = domanda.rispondi(conto, C1, finta, cat, None, "it")
    domanda.rispondi(conto, "e a novembre?", finta, cat, primo["richiesta"], "it")
    uscito = "\n".join(finta.ricevuti)
    assert [v for v in _cose_del_file_che_non_devono_uscire(conto) if v in uscito] == []


# ---- C10: l'IA locale non fa uscire niente dal computer ----
def test_c10_ollama_non_esce_dal_pc_groq_si():
    assert ia.Ollama().esce_dal_pc is False
    assert ia.Groq(chiave="finta").esce_dal_pc is True


# ---- C11: l'anteprima mostra esattamente cosa esce ----
def test_c11_anteprima_uguale_a_cio_che_esce(conto):
    a = privacy.anteprima(conto)
    assert a["colonne"] == ["data", "descrizione", "importo"]
    assert a["importi"] == 0 and len(a["testi"]) == conto.df.descrizione.map(privacy.senza_cifre).nunique()
    finta = IAFinta(RICHIESTA_C1)
    domanda.rispondi(conto, C1, finta, {}, None, "it")
    for testo in a["testi"]:
        assert testo in finta.ricevuti[0]
    assert not any(c.isdigit() for t in a["testi"] for c in t)


# ---- il percorso regge le risposte sbagliate dell'IA ----
@pytest.mark.parametrize("risposta_ia,chiave", [
    ("non ho capito, scusa", "non_capito"),
    ({"tipo": "calcolo", "operazione": "somma", "misura": "importo", "codice": "import os"}, "rifiutata"),
    ({"tipo": "calcolo", "operazione": "somma", "misura": "fatturato"}, "rifiutata"),
])
def test_c20_risposta_ia_sbagliata_diventa_un_messaggio(conto, risposta_ia, chiave):
    r = domanda.rispondi(conto, C1, IAFinta(risposta_ia, risposta_ia), {}, None, "it")
    assert r["esito"] == chiave and r["righe"] == [] and not any(c.isdigit() for c in r["frase"])
