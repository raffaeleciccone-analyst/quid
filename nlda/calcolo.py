"""Esegue una richiesta già validata: numero + righe da cui viene. SPEC F1, F2, F6, F7; criteri C1, C6, C7.
Nessun codice dall'IA: solo operazioni fisse di pandas scelte dai campi della richiesta."""
from dataclasses import dataclass, field

import pandas as pd


class CalcoloNonTorna(Exception):
    """La somma delle righe mostrate non dà il numero della frase (C1): niente risposta."""


@dataclass
class Esito:
    numero: float | None = None
    righe: pd.DataFrame = field(default_factory=pd.DataFrame)
    gruppi: pd.Series | None = None
    etichetta: str | None = None                       # la voce scelta da massimo/minimo per gruppi
    incerte: pd.DataFrame = field(default_factory=pd.DataFrame)   # F7: non entrano nel numero
    periodo: tuple | None = None                       # (mese, anno) usati davvero
    domanda_indietro: dict | None = None               # F6: {"mese": 10, "anni": [2025, 2026]}


def con_categorie(df, categorie):
    """categorie = {descrizione: (categoria, certa)} → colonne 'categoria' (certe) e 'categoria_incerta'."""
    if "descrizione" not in df.columns:
        return df.copy()
    voce = df["descrizione"].map(lambda d: categorie.get(d, (None, True)))
    return df.assign(categoria=voce.map(lambda v: v[0] if v[1] else None),
                     categoria_incerta=voce.map(lambda v: None if v[1] else v[0]))


def esegui(tabella, ric, categorie=None) -> Esito:
    d = con_categorie(tabella.df, categorie or {})
    esito = Esito()

    mese, anno = (ric.periodo.mese, ric.periodo.anno) if ric.periodo else (None, None)
    if mese and not anno:                                                    # F6: quale ottobre?
        anni = sorted(int(a) for a in d.loc[d["data"].dt.month == mese, "data"].dt.year.unique())
        if len(anni) > 1:
            return Esito(domanda_indietro={"mese": mese, "anni": anni})
        anno = anni[0] if anni else None
    if anno:
        d = d[d["data"].dt.year == anno]
    if mese:
        d = d[d["data"].dt.month == mese]
    esito.periodo = (mese, anno) if (mese or anno) else None

    if tabella.tipo == "conto" and ric.segno in ("uscite", "entrate"):
        d = d[d["importo"] < 0] if ric.segno == "uscite" else d[d["importo"] > 0]

    for f in ric.filtri:
        if f.colonna == "categoria":
            esito.incerte = d[d["categoria_incerta"] == f.uguale]
            d = d[d["categoria"] == f.uguale]
        else:
            d = d[d[f.colonna].astype(str).str.contains(f.uguale, case=False, regex=False)]

    m = ric.misura
    if ric.raggruppa:
        chiave = d["data"].dt.to_period("M").astype(str) if ric.raggruppa == "mese" else d[ric.raggruppa]
        g = d.groupby(chiave)[m].sum().round(2) if ric.operazione != "conteggio" else d.groupby(chiave).size()
        esito.gruppi = g
        if ric.operazione in ("massimo", "minimo") and len(g):
            esito.etichetta = str(g.idxmax() if ric.operazione == "massimo" else g.idxmin())
            esito.numero = float(g[esito.etichetta])
        else:
            esito.numero = float(round(g.sum(), 2))
        esito.righe = g.rename(m or "conteggio").reset_index().rename(columns={"data": "mese"})
        return esito

    esito.righe = d.drop(columns=["categoria", "categoria_incerta"], errors="ignore")
    if ric.operazione == "somma":
        esito.numero = float(round(d[m].sum(), 2))
    elif ric.operazione == "conteggio":
        esito.numero = float(len(d))
    elif ric.operazione == "media" and len(d):
        esito.numero = float(round(d[m].mean(), 2))
    elif ric.operazione in ("massimo", "minimo") and len(d):
        i = d[m].idxmax() if ric.operazione == "massimo" else d[m].idxmin()
        esito.righe, esito.numero = esito.righe.loc[[i]], float(d.loc[i, m])
    return esito


def controlla(ric, esito):
    """C1: il numero deve venire dalle righe mostrate."""
    if esito.numero is None or ric.operazione not in ("somma", "massimo", "minimo"):
        return
    if esito.gruppi is not None:
        atteso = esito.gruppi[esito.etichetta] if esito.etichetta else esito.gruppi.sum()
    else:
        atteso = esito.righe[ric.misura].sum() if ric.operazione == "somma" else esito.righe[ric.misura].iloc[0]
    if round(float(atteso), 2) != round(esito.numero, 2):
        raise CalcoloNonTorna(f"righe {atteso} contro numero {esito.numero}")
