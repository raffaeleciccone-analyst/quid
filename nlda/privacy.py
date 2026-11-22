"""L'unico messaggio che esce verso l'IA (PIANO §3). SPEC F9: colonne, tipi, testi del file SENZA CIFRE, la domanda,
la richiesta precedente. Mai importi, date, IBAN, numeri di carta. Lo stesso messaggio vale per l'IA locale. F10, C9, C11."""
import json
import re

from .categorie import CATEGORIE
from .categorie import senza_cifre as _senza_cifre

TIPI = {"M": "data", "f": "numero", "i": "numero"}
MAX_TESTI = 300


def senza_cifre(testo: str) -> str:
    """'PAGAMENTO CARTA 4532 **** 1234' → 'PAGAMENTO CARTA #### **** ####'. Ogni cifra diventa #."""
    return _senza_cifre(testo)


def _colonne_testo(df):
    return [c for c in df.columns if df[c].dtype.kind not in "fiMb"]


def anteprima(tabella) -> dict:
    """Cosa uscirà verso l'IA online, da mostrare prima della prima domanda (F10, C11)."""
    df = tabella.df
    testi = []
    for c in _colonne_testo(df):
        testi += [t for t in dict.fromkeys(df[c].map(senza_cifre)) if t not in testi]
    return {"colonne": list(df.columns), "tipi": {c: TIPI.get(df[c].dtype.kind, "testo") for c in df.columns},
            "testi": testi[:MAX_TESTI], "importi": 0}


def messaggio(tabella, domanda: str, precedente: dict | None) -> str:
    a = anteprima(tabella)
    colonne = [f"{c} ({t})" for c, t in a["tipi"].items()]
    if tabella.tipo == "conto":                       # la colonna che il programma aggiunge con le categorie (F7)
        colonne.append("categoria (una tra: " + ", ".join(CATEGORIE) + ")")
    righe = ["TIPO DI FILE: " + tabella.tipo, "COLONNE: " + ", ".join(colonne),
             "TESTI DEL FILE (le cifre sono nascoste con #):", *a["testi"]]
    if precedente:
        righe.append("RICHIESTA PRECEDENTE: " + json.dumps(precedente, ensure_ascii=False))
    righe.append("DOMANDA: " + domanda)
    return "\n".join(righe)
