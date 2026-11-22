"""Estratto conto PDF: C13 (stesse righe del CSV, saldi che tornano), C14 (riga persa → niente risposta), C15."""
from pathlib import Path

import pandas as pd
import pytest

from quid import leggi

FILE = Path(__file__).parent.parent / "prove" / "file"


def _leggi(nome):
    return leggi.leggi((FILE / nome).read_bytes(), nome)


def test_c13_pdf_stesse_righe_del_csv_e_saldi_che_tornano():
    pdf, csv = _leggi("conto.pdf"), _leggi("conto.csv")
    assert pdf.tipo == "conto"
    pd.testing.assert_frame_equal(pdf.df, csv.df)
    iniziale, finale = pdf.saldi
    assert iniziale == 5000.00 and round(iniziale + pdf.df.importo.sum(), 2) == finale


def test_c14_pdf_con_una_riga_persa_non_si_usa_e_dice_di_quanto():
    with pytest.raises(leggi.FileNonLeggibile) as e:
        _leggi("conto_pdf_rotto.pdf")
    assert e.value.chiave == "saldi_non_tornano"
    assert e.value.dettagli["differenza"] == 64.30          # la riga persa: gas A2A di ottobre 2026, 64,30 €
    assert set(e.value.dettagli) >= {"iniziale", "finale", "letti", "differenza"}


def test_c14_pdf_senza_saldi_si_legge_ma_lo_dice():
    t = _leggi("conto_senza_saldi.pdf")
    assert t.saldi is None and {"chiave": "senza_saldi"} in t.sistemato
    pd.testing.assert_frame_equal(t.df, _leggi("conto.csv").df)


def test_c15_pdf_che_non_e_un_estratto():
    with pytest.raises(leggi.FileNonLeggibile) as e:
        _leggi("lettera.pdf")
    assert e.value.chiave == "formato"
