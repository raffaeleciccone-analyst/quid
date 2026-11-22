"""La risposta la scrive il programma, non l'IA: frase con il numero, righe, "Ho capito", grafico sì/no,
"come l'ho calcolato". SPEC F1-F5, F13; criteri C1-C5."""
from . import calcolo

MESI = {"it": ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
               "ottobre", "novembre", "dicembre"],
        "en": ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
               "November", "December"]}
F = {
    "it": {"speso": "{quando} hai speso {n}{cosa}", "incassato": "{quando} hai incassato {n}{cosa}",
           "totale": "{quando} il totale di {misura} è {n}{cosa}", "conteggio": "{quando} ci sono {n} righe{cosa}",
           "media": "{quando} la media di {misura} è {n}{cosa}", "in": " in {}",
           "massimo_gruppo": "{Gruppo} con {misura} più alto: {etichetta}, {n}",
           "minimo_gruppo": "{Gruppo} con {misura} più basso: {etichetta}, {n}",
           "massimo": "Il valore più alto di {misura} è {n}", "minimo": "Il valore più basso di {misura} è {n}",
           "andamento": "{quando}, {misura} per {gruppo}: in tutto {n}", "elenco": "Ecco le righe che corrispondono",
           "quando_mese": "A {mese} {anno}", "quando_anno": "Nel {anno}", "quando_tutto": "In tutto il file",
           "assente": "Nel file non c'è «{cosa}». Ci sono queste colonne: {colonne}.",
           "non_capito": "Non ho capito la domanda. Prova a dirla in un altro modo.",
           "quale_anno": "Quale {mese}: {anni}?", "o": " o ",
           "uscite": "uscite", "entrate": "entrate", "di": "di",
           "op": {"somma": "somma", "conteggio": "conteggio", "media": "media", "massimo": "massimo", "minimo": "minimo", "elenco": "elenco"}},
    "en": {"speso": "{quando} you spent {n}{cosa}", "incassato": "{quando} you received {n}{cosa}",
           "totale": "{quando} the total of {misura} is {n}{cosa}", "conteggio": "{quando} there are {n} rows{cosa}",
           "media": "{quando} the average of {misura} is {n}{cosa}", "in": " on {}",
           "massimo_gruppo": "{Gruppo} with the highest {misura}: {etichetta}, {n}",
           "minimo_gruppo": "{Gruppo} with the lowest {misura}: {etichetta}, {n}",
           "massimo": "The highest {misura} is {n}", "minimo": "The lowest {misura} is {n}",
           "andamento": "{quando}, {misura} by {gruppo}: {n} in total", "elenco": "Here are the matching rows",
           "quando_mese": "In {mese} {anno}", "quando_anno": "In {anno}", "quando_tutto": "Across the whole file",
           "assente": "The file has no «{cosa}». These are its columns: {colonne}.",
           "non_capito": "I didn't understand the question. Try asking it another way.",
           "quale_anno": "Which {mese}: {anni}?", "o": " or ",
           "uscite": "expenses", "entrate": "income", "di": "of",
           "op": {"somma": "sum", "conteggio": "count", "media": "average", "massimo": "highest", "minimo": "lowest", "elenco": "list"}},
}
SOLDI = {"importo", "prezzo", "entrate", "uscite"}


def numero(x, lingua, soldi=True):
    if not soldi:
        return f"{x:,.0f}".replace(",", "." if lingua == "it" else ",") if float(x).is_integer() else f"{x:,.2f}"
    s = f"{abs(x):,.2f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".") + " €" if lingua == "it" else "€" + s


def componi(ric, esito, tabella, lingua="it"):
    t = F[lingua]
    vuota = {"frase": "", "ho_capito": "", "righe": [], "incerte": [], "grafico": None, "come": None,
             "domanda_indietro": None}
    if ric.tipo == "assente":
        return vuota | {"frase": t["assente"].format(cosa=ric.cosa or "?", colonne=", ".join(tabella.df.columns))}
    if ric.tipo == "non_capito":
        return vuota | {"frase": t["non_capito"]}
    if esito.domanda_indietro:
        q = esito.domanda_indietro
        return vuota | {"frase": t["quale_anno"].format(mese=MESI[lingua][q["mese"] - 1],
                                                        anni=t["o"].join(str(a) for a in q["anni"])),
                        "domanda_indietro": q}

    calcolo.controlla(ric, esito)                                          # C1: se non torna, niente risposta
    soldi = ric.misura in SOLDI
    n = numero(esito.numero, lingua, soldi) if esito.numero is not None else ""
    quando = _quando(esito.periodo, lingua)
    categoria = next((f.uguale for f in ric.filtri if f.colonna == "categoria"), None)
    cosa = t["in"].format(categoria) if categoria else ""

    if ric.raggruppa and ric.operazione in ("massimo", "minimo"):
        frase = t[ric.operazione + "_gruppo"].format(Gruppo=ric.raggruppa.capitalize(), misura=ric.misura,
                                                     etichetta=esito.etichetta, n=n)
    elif ric.raggruppa:
        frase = t["andamento"].format(quando=quando, misura=ric.misura or "", gruppo=ric.raggruppa, n=n)
    elif ric.operazione == "somma" and tabella.tipo == "conto" and ric.segno in ("uscite", "entrate"):
        frase = t["speso" if ric.segno == "uscite" else "incassato"].format(quando=quando, n=n, cosa=cosa)
    elif ric.operazione == "somma":
        frase = t["totale"].format(quando=quando, misura=ric.misura, n=n, cosa=cosa)
    elif ric.operazione == "conteggio":
        frase = t["conteggio"].format(quando=quando, n=numero(esito.numero, lingua, False), cosa=cosa)
    elif ric.operazione in ("media", "massimo", "minimo"):
        frase = t[ric.operazione].format(quando=quando, misura=ric.misura, n=n, cosa=cosa)
    else:
        frase = t["elenco"]
    if ric.operazione == "somma" and not ric.raggruppa and 0 < len(esito.righe) <= 5 and "descrizione" in esito.righe:
        frase += ": " + ", ".join(f"{r.descrizione} {numero(r[ric.misura], lingua, soldi)}"
                                  for _, r in esito.righe.iterrows())
    parole = _parole(ric, esito, lingua)
    return {"frase": frase + ".", "ho_capito": parole, "righe": _record(esito.righe), "incerte": _record(esito.incerte),
            "grafico": _grafico(ric, esito), "come": {"parole": parole, "pandas": _pandas(ric, esito)},
            "domanda_indietro": None}


def _quando(periodo, lingua):
    t = F[lingua]
    if not periodo:
        return t["quando_tutto"]
    mese, anno = periodo
    if mese:
        return t["quando_mese"].format(mese=MESI[lingua][mese - 1], anno=anno or "")
    return t["quando_anno"].format(anno=anno)


def _parole(ric, esito, lingua):
    """La richiesta in parole: è la riga "Ho capito" (F13) e la prima parte di "come l'ho calcolato" (F4)."""
    t = F[lingua]
    op = t["op"][ric.operazione]
    pezzi = [f"{op} {t['di']} {ric.misura}" if ric.misura else op]
    if ric.segno in ("uscite", "entrate"):
        pezzi.append(t[ric.segno])
    pezzi += [f.uguale for f in ric.filtri]
    if esito.periodo:
        mese, anno = esito.periodo
        pezzi.append(" ".join(str(x) for x in (MESI[lingua][mese - 1] if mese else None, anno) if x))
    if ric.raggruppa:
        pezzi.append(f"per {ric.raggruppa}" if lingua == "it" else f"by {ric.raggruppa}")
    return ", ".join(pezzi)


def _pandas(ric, esito):
    """Una riga di pandas equivalente, per chi vuole rifare il conto (F4). Si mostra, non si esegue."""
    cond = [f"(df['{f.colonna}'] == {f.uguale!r})" if f.colonna == "categoria"
            else f"(df['{f.colonna}'].astype(str).str.contains({f.uguale!r}, case=False))" for f in ric.filtri]
    if esito.periodo:
        mese, anno = esito.periodo
        cond += [f"(df['data'].dt.year == {anno})"] if anno else []
        cond += [f"(df['data'].dt.month == {mese})"] if mese else []
    if ric.segno == "uscite":
        cond.append("(df['importo'] < 0)")
    elif ric.segno == "entrate":
        cond.append("(df['importo'] > 0)")
    base = f"df[{' & '.join(cond)}]" if cond else "df"
    op = {"somma": "sum", "conteggio": "count", "media": "mean", "massimo": "max", "minimo": "min"}.get(ric.operazione)
    if ric.raggruppa:
        chiave = "df['data'].dt.to_period('M')" if ric.raggruppa == "mese" else f"'{ric.raggruppa}'"
        return f"{base}.groupby({chiave})['{ric.misura}'].sum()" + (f".{op[:3]}()" if op in ("max", "min") else "")
    return f"{base}['{ric.misura}'].{op}()" if op and ric.misura else base


def _grafico(ric, esito):
    """F3: linea per l'andamento mese per mese, barre per un confronto fra 2-12 voci, altrimenti niente."""
    if ric.raggruppa == "mese" and esito.gruppi is not None and len(esito.gruppi) > 1:
        return "linea"
    if ric.raggruppa and esito.gruppi is not None and 2 <= len(esito.gruppi) <= 12:
        return "barre"
    return None


def _record(df):
    if df is None or df.empty:
        return []
    df = df.drop(columns=["categoria", "categoria_incerta"], errors="ignore")
    if "data" in df.columns:
        df = df.assign(data=df["data"].dt.strftime("%Y-%m-%d"))
    return df.to_dict("records")
