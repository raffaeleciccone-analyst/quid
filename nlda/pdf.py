"""Estratto conto PDF → Tabella con i saldi, poi il controllo: saldo iniziale + movimenti = saldo finale.
SPEC F11, F12; criteri C13, C14. Si leggono le parole con la loro posizione: un importo è un addebito o un accredito
a seconda della colonna sotto cui è stampato."""
import io
import re

import pandas as pd
import pdfplumber

DATA = re.compile(r"\d{2}/\d{2}/\d{4}$")
IMPORTO = re.compile(r"-?\d{1,3}(\.\d{3})*,\d{2}$")
ADDEBITI = ("addebiti", "uscite", "dare", "addebito")
ACCREDITI = ("accrediti", "entrate", "avere", "accredito")


def _numero(t):
    return float(t.replace(".", "").replace(",", "."))


def leggi_pdf(dati: bytes):
    """→ (DataFrame data/descrizione/importo, saldi (iniziale, finale) o None). Nessuna riga → DataFrame vuoto."""
    righe, iniziale, finale = [], None, None
    with pdfplumber.open(io.BytesIO(dati)) as doc:
        for pagina in doc.pages:
            parole = pagina.extract_words(keep_blank_chars=False, use_text_flow=False)
            colonne = {}           # x del bordo destro di "Addebiti" e "Accrediti", presi SOLO dalla riga d'intestazione
            for linea in _linee(parole):                          # (non da "ADDEBITO SDD ..." nelle descrizioni)
                nomi = {p["text"].lower(): p["x1"] for p in linea}
                uscita = next((nomi[n] for n in ADDEBITI if n in nomi), None)
                entrata = next((nomi[n] for n in ACCREDITI if n in nomi), None)
                if uscita and entrata:
                    colonne = {"uscita": uscita, "entrata": entrata}
                    break
            for linea in _linee(parole):
                testi = [p["text"] for p in linea]
                frase = " ".join(testi).upper()
                if "SALDO INIZIALE" in frase and IMPORTO.match(testi[-1]):
                    iniziale = _numero(testi[-1])
                elif "SALDO FINALE" in frase and IMPORTO.match(testi[-1]):
                    finale = _numero(testi[-1])
                elif DATA.match(testi[0]) and IMPORTO.match(testi[-1]) and colonne:
                    importo = linea[-1]
                    # la colonna più vicina al bordo destro del numero decide il segno
                    lato = min(colonne, key=lambda k: abs(colonne[k] - importo["x1"]))
                    valore = _numero(importo["text"])
                    descr = " ".join(t for t in testi[1:-1] if not DATA.match(t))
                    righe.append((testi[0], descr, -valore if lato == "uscita" else valore))
    df = pd.DataFrame(righe, columns=["data", "descrizione", "importo"])
    df["data"] = pd.to_datetime(df["data"], dayfirst=True, format="%d/%m/%Y").astype("datetime64[ns]")
    df["descrizione"] = df["descrizione"].astype(str)
    df["importo"] = df["importo"].astype(float).round(2)
    saldi = (iniziale, finale) if iniziale is not None and finale is not None else None
    return df, saldi


def _linee(parole, tolleranza=2):
    """Parole raggruppate per riga (stessa altezza), da sinistra a destra."""
    linee = []
    for p in sorted(parole, key=lambda p: (round(p["top"]), p["x0"])):
        if linee and abs(linee[-1][0]["top"] - p["top"]) <= tolleranza:
            linee[-1].append(p)
        else:
            linee.append([p])
    return [sorted(linea, key=lambda p: p["x0"]) for linea in linee]


def controlla_saldi(df, saldi):
    """F12: None se tornano, altrimenti i numeri di quanto non torna (da mostrare all'utente)."""
    iniziale, finale = saldi
    letti = round(df["importo"].sum(), 2)
    differenza = round(iniziale + letti - finale, 2)
    if differenza == 0:
        return None
    return {"iniziale": iniziale, "finale": finale, "letti": letti, "differenza": abs(differenza)}
