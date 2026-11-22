"""Lettura dei file: C8 (file sporco), C12 (formati e codifiche), C15 (file che non sono tabelle)."""
from pathlib import Path

import pandas as pd
import pytest

from quid import leggi

FILE = Path(__file__).parent.parent / "prove" / "file"


def _leggi(nome):
    return leggi.leggi((FILE / nome).read_bytes(), nome)


def _bollette_ottobre_2026(df):
    righe = df[(df.data.dt.year == 2026) & (df.data.dt.month == 10)
               & df.descrizione.str.contains("ENEL|A2A|TIM")]
    return round(-righe.importo.sum(), 2)


# ---- C12: stessi numeri da formati e codifiche diversi ----
def test_c12_estratto_conto_riconosciuto_con_i_numeri_giusti():
    t = _leggi("conto.csv")
    assert t.tipo == "conto"
    assert list(t.df.columns) == ["data", "descrizione", "importo"]
    assert _bollette_ottobre_2026(t.df) == 187.40
    assert t.df.importo.gt(0).sum() == 23                     # 23 stipendi
    assert t.sistemato == []


def test_c12_codifica_non_utf8_da_gli_stessi_numeri():
    a, b = _leggi("conto.csv"), _leggi("conto_latin1.csv")
    pd.testing.assert_frame_equal(a.df, b.df)
    assert "BAR CAFFÈ ROMA" in set(b.df.descrizione)


def test_c12_vendite_excel_e_csv_con_punto_e_virgola_coincidono():
    x, c = _leggi("vendite.xlsx"), _leggi("vendite.csv")
    assert x.tipo == c.tipo == "vendite"
    assert list(x.df.columns)[:4] == ["data", "prodotto", "quantita", "importo"]
    pd.testing.assert_frame_equal(x.df, c.df)
    totali = x.df.groupby("prodotto").importo.sum()
    assert totali.idxmax() == "Candela profumata" and round(totali.max(), 2) == 11500.00
    assert round(x.df.importo.sum(), 2) == 26381.00


# ---- C8: il file sporco dà gli stessi numeri e dice cosa ha sistemato ----
def test_c08_file_sporco_stessi_numeri_e_dice_cosa_ha_sistemato():
    pulito, sporco = _leggi("conto.csv"), _leggi("conto_sporco.csv")
    assert sporco.tipo == "conto"
    pd.testing.assert_frame_equal(pulito.df, sporco.df)
    fatto = {s["chiave"]: s.get("n") for s in sporco.sistemato}
    assert fatto.get("righe_vuote") == 2
    assert fatto.get("righe_totale") == 1
    assert "entrate_uscite" in fatto


# ---- C15: file che non sono tabelle → messaggio chiaro, mai un errore ----
@pytest.mark.parametrize("nome", ["vuoto.csv", "immagine.png"])
def test_c15_file_non_tabella_messaggio_chiaro(nome):
    with pytest.raises(leggi.FileNonLeggibile) as e:
        _leggi(nome)
    assert e.value.chiave in {"vuoto", "formato"}


def test_c15_testo_senza_colonne_non_e_una_tabella():
    with pytest.raises(leggi.FileNonLeggibile):
        leggi.leggi("Caro Mario,\nti scrivo per dirti che domani non ci sono.\n".encode(), "lettera.csv")
