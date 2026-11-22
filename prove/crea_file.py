"""Scrive i file di prova con numeri scelti a mano (SPEC, sezione 5): le risposte giuste si conoscono prima.

Uso:  python prove/crea_file.py      → file in prove/file/
"""
from datetime import date
from pathlib import Path

import pandas as pd

CARTELLA = Path(__file__).parent / "file"

# ---- estratto conto: gennaio 2025 - novembre 2026 ----
# Bollette fissate a mano nei mesi che i criteri usano; negli altri mesi seguono una regola semplice.
BOLLETTE = {  # (anno, mese): (luce, gas, telefono)
    (2025, 10): (80.00, 50.00, 31.00),    # ottobre 2025: 161,00  (serve a C6: due ottobre)
    (2026, 10): (92.10, 64.30, 31.00),    # ottobre 2026: 187,40  (C1)
    (2026, 11): (88.40, 71.20, 31.00),    # novembre 2026: 190,60 (C16)
}
IBAN = "IT60X0542811101000000123456"
CARTA = "4532 **** **** 1234"


def movimenti():
    righe = []
    for anno in (2025, 2026):
        for mese in range(1, 13):
            if (anno, mese) > (2026, 11):
                break
            luce, gas, tel = BOLLETTE.get((anno, mese), (60 + mese, 30 + mese, 31.00))
            righe += [
                (date(anno, mese, 5), "ADDEBITO SDD ENEL ENERGIA SPA", -luce),
                (date(anno, mese, 12), "ADDEBITO SDD A2A ENERGIA GAS", -gas),
                (date(anno, mese, 20), "ADDEBITO SDD TIM SPA TELEFONO", -tel),
                (date(anno, mese, 3), f"PAGAMENTO CARTA {CARTA} ESSELUNGA MILANO", -(45.20 + mese)),
                (date(anno, mese, 17), f"PAGAMENTO CARTA {CARTA} ESSELUNGA MILANO", -(38.60 + mese)),
                (date(anno, mese, 27), f"BONIFICO DA {IBAN} STIPENDIO ROSSI SRL", 1850.00),
            ]
            if mese % 2 == 0 or (anno, mese) == (2026, 10):
                righe.append((date(anno, mese, 22), "AMAZON EU SARL", -12.99))   # incerta: bolletta? (C7)
            if mese == 8:
                righe.append((date(anno, mese, 9), "BAR CAFFÈ ROMA", -4.50))        # accento: codifica (C12)
    df = pd.DataFrame(righe, columns=["data", "descrizione", "importo"]).sort_values("data", kind="stable")
    df["importo"] = df["importo"].round(2)
    return df.reset_index(drop=True)


def euro(x):
    """1234.5 → '1.234,50'"""
    return f"{x:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def scrivi_conto(df):
    pulito = pd.DataFrame({"Data": df["data"].map(lambda d: d.strftime("%d/%m/%Y")),
                           "Descrizione": df["descrizione"], "Importo": df["importo"].map(euro)})
    pulito.to_csv(CARTELLA / "conto.csv", sep=";", index=False, encoding="utf-8")
    pulito.to_csv(CARTELLA / "conto_latin1.csv", sep=";", index=False, encoding="cp1252")   # C12

    # C8: righe vuote, riga di totale, importi con €, colonne Entrate/Uscite separate
    righe = ["Data;Descrizione;Entrate;Uscite"]
    for i, r in df.iterrows():
        entrata = f"{euro(r.importo)} €" if r.importo > 0 else ""
        uscita = f"{euro(-r.importo)} €" if r.importo < 0 else ""
        righe.append(f"{r.data.strftime('%d/%m/%Y')};{r.descrizione};{entrata};{uscita}")
        if i in (10, 100):
            righe.append(";;;")
    righe.append(f";TOTALE;{euro(df.importo[df.importo > 0].sum())} €;{euro(-df.importo[df.importo < 0].sum())} €")
    (CARTELLA / "conto_sporco.csv").write_text("\n".join(righe) + "\n", encoding="utf-8")


# ---- vendite di un negozio: 2025-2026 ----
PRODOTTI = {  # prodotto: (prezzo, pezzi al mese)
    "Candela profumata": (12.50, 40),     # il prodotto che vende di più (C2): 500,00 € al mese
    "Tazza in ceramica": (9.90, 30),      # 297,00 € al mese
    "Quaderno": (4.00, 50),               # 200,00 € al mese
    "Cornice": (15.00, 10),               # 150,00 € al mese
}


def vendite():
    righe = []
    for anno in (2025, 2026):
        for mese in range(1, 13):
            if (anno, mese) > (2026, 11):
                break
            for prodotto, (prezzo, pezzi) in PRODOTTI.items():
                for giorno, q in ((8, pezzi // 2), (22, pezzi - pezzi // 2)):
                    righe.append((date(anno, mese, giorno), prodotto, q, prezzo, round(q * prezzo, 2)))
    return pd.DataFrame(righe, columns=["data", "prodotto", "quantita", "prezzo", "importo"])


def scrivi_vendite(df):
    xl = df.rename(columns={"data": "Data", "prodotto": "Prodotto", "quantita": "Quantità",
                            "prezzo": "Prezzo", "importo": "Importo"})
    xl.to_excel(CARTELLA / "vendite.xlsx", index=False)
    csv = xl.assign(Data=xl["Data"].map(lambda d: d.strftime("%d/%m/%Y")),
                    Prezzo=xl["Prezzo"].map(euro), Importo=xl["Importo"].map(euro))
    csv.to_csv(CARTELLA / "vendite.csv", sep=";", index=False, encoding="utf-8")


def scrivi_non_tabelle():
    (CARTELLA / "vuoto.csv").write_bytes(b"")
    (CARTELLA / "immagine.png").write_bytes(bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
        "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082"))


if __name__ == "__main__":
    CARTELLA.mkdir(exist_ok=True)
    scrivi_conto(movimenti())
    scrivi_vendite(vendite())
    scrivi_non_tabelle()
    print("file scritti in", CARTELLA)
