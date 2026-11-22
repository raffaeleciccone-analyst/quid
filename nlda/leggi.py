"""CSV ed Excel → Tabella pulita, la porta d'ingresso n.1 (PIANO §2). SPEC F8, F11; criteri C8, C12, C15."""
import io
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

SEPARATORI = [";", ",", "\t", "|"]
NOMI = {  # nome standard: nomi possibili nell'intestazione (senza accenti, minuscoli)
    "data": ["data", "data operazione", "data contabile", "data valuta", "date"],
    "descrizione": ["descrizione", "causale", "operazione", "dettaglio", "description"],
    "importo": ["importo", "totale", "amount", "valore"],
    "entrate": ["entrate", "accrediti", "avere"],
    "uscite": ["uscite", "addebiti", "dare"],
    "prodotto": ["prodotto", "articolo", "product", "item"],
    "quantita": ["quantita", "qta", "pezzi", "quantity"],
}


class FileNonLeggibile(Exception):
    """Il file non è una tabella leggibile. `chiave` sceglie il messaggio (IT/EN), `dettagli` i numeri da mostrare."""
    def __init__(self, chiave, dettagli=None):
        super().__init__(chiave)
        self.chiave, self.dettagli = chiave, dettagli or {}


@dataclass
class Tabella:
    tipo: str                                   # "conto" | "vendite" | "altro"
    df: pd.DataFrame
    sistemato: list = field(default_factory=list)   # [{"chiave": "righe_vuote", "n": 2}, ...]  F8
    saldi: tuple | None = None                       # (iniziale, finale), solo dal PDF  F12


def leggi(dati: bytes, nome: str) -> Tabella:
    if not dati.strip():
        raise FileNonLeggibile("vuoto")
    if dati[:4] == b"%PDF":
        return _da_pdf(dati)
    if dati[:2] == b"PK" or nome.lower().endswith((".xlsx", ".xls")):
        grezzo = pd.read_excel(io.BytesIO(dati), dtype=object)
    elif b"\x00" in dati[:1024] or dati[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0"):
        raise FileNonLeggibile("formato")
    else:
        grezzo = _csv(dati)
    return _pulisci(grezzo)


def _da_pdf(dati):
    """F11, F12: un PDF letto male non diventa un numero sbagliato."""
    from . import pdf
    df, saldi = pdf.leggi_pdf(dati)
    if df.empty:
        raise FileNonLeggibile("formato")
    if saldi is None:
        return Tabella("conto", df, [{"chiave": "senza_saldi"}])
    non_torna = pdf.controlla_saldi(df, saldi)
    if non_torna:
        raise FileNonLeggibile("saldi_non_tornano", non_torna)
    return Tabella("conto", df, [], saldi)


def _csv(dati):
    for codifica in ("utf-8-sig", "cp1252"):
        try:
            testo = dati.decode(codifica)
            break
        except UnicodeDecodeError:
            continue
    righe = [r for r in testo.splitlines() if r.strip()][:20]
    # il separatore giusto divide l'intestazione in più colonne e lo fa uguale in tutte le righe
    sep = max(SEPARATORI, key=lambda s: (righe[0].count(s) > 0 and len({r.count(s) for r in righe}) == 1,
                                         righe[0].count(s)))
    if righe[0].count(sep) == 0:
        raise FileNonLeggibile("formato")
    return pd.read_csv(io.StringIO(testo), sep=sep, dtype=str, keep_default_na=False, skip_blank_lines=False)


def _pulisci(df):
    sistemato = []
    df = df.rename(columns=lambda c: _standard(str(c)))
    df = df.map(lambda v: v.strip() if isinstance(v, str) else v)

    vuote = df.apply(lambda r: all(v in ("", None) or pd.isna(v) for v in r), axis=1)
    if vuote.any():
        sistemato.append({"chiave": "righe_vuote", "n": int(vuote.sum())})
    df = df[~vuote]

    if "data" in df.columns:
        totali = df["data"].map(lambda v: v in ("", None) or pd.isna(v)) & df.apply(
            lambda r: any("total" in str(v).lower() for v in r), axis=1)
        if totali.any():
            sistemato.append({"chiave": "righe_totale", "n": int(totali.sum())})
        df = df[~totali]
        df["data"] = _date(df["data"])
        if df["data"].isna().mean() > 0.1:
            raise FileNonLeggibile("formato")

    for c in df.columns:
        if c not in ("data", "descrizione", "prodotto"):
            numeri = df[c].map(_numero)
            if numeri.notna().mean() >= 0.9 or (c in ("entrate", "uscite") and len(df)):
                df[c] = numeri

    if {"entrate", "uscite"} <= set(df.columns) and "importo" not in df.columns:
        df["importo"] = df["entrate"].fillna(0) - df["uscite"].fillna(0)
        df = df.drop(columns=["entrate", "uscite"])
        sistemato.append({"chiave": "entrate_uscite"})

    df = df.reset_index(drop=True)
    if {"data", "descrizione", "importo"} <= set(df.columns) and "prodotto" not in df.columns:
        df = df[["data", "descrizione", "importo"]].astype({"descrizione": str})
        return Tabella("conto", df.assign(importo=df["importo"].astype(float).round(2)), sistemato)
    if {"data", "prodotto", "importo"} <= set(df.columns):
        primi = ["data", "prodotto", "quantita", "importo"] if "quantita" in df.columns else ["data", "prodotto", "importo"]
        df = df[primi + [c for c in df.columns if c not in primi]].astype({"prodotto": str})
        if "quantita" in df.columns:
            df["quantita"] = df["quantita"].astype("int64")
        return Tabella("vendite", df.astype({c: float for c in df.columns
                                               if c not in primi[:3] and df[c].dtype.kind in "fiO"
                                               and df[c].map(lambda v: isinstance(v, (int, float))).all()}),
                       sistemato)
    if len(df.columns) < 2 or not any(df[c].dtype.kind in "fiM" for c in df.columns):
        raise FileNonLeggibile("formato")
    return Tabella("altro", df, sistemato)


def _standard(nome):
    n = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower().strip()
    return next((std for std, possibili in NOMI.items() if n in possibili), n)


def _date(serie):
    if pd.api.types.is_datetime64_any_dtype(serie):
        return pd.to_datetime(serie).astype("datetime64[ns]")
    return pd.to_datetime(serie.map(lambda v: v if not hasattr(v, "year") else v.strftime("%d/%m/%Y")),
                          dayfirst=True, errors="coerce", format="mixed").astype("datetime64[ns]")


def _numero(v):
    """'1.234,50 €' → 1234.5;  '-46,20' → -46.2;  12.5 → 12.5;  '' → None (C8, C12)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return None if pd.isna(v) else v
    s = str(v).replace("€", "").replace("EUR", "").replace(" ", "").replace(" ", "")
    if s == "":
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"-?\d{1,3}(\.\d{3})+", s):
        s = s.replace(".", "")
    try:
        x = float(s)
    except ValueError:
        return None
    return int(x) if x.is_integer() and "." not in s else x
