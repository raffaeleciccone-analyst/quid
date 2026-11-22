"""Richiesta, calcolo e risposta con l'IA finta: C1-C5 e C20.
Le richieste qui sotto sono quelle che l'IA dovrebbe restituire: scritte a mano, come farebbe un finto fornitore."""
from pathlib import Path

import pytest

from nlda import calcolo, leggi, richiesta, risposta

FILE = Path(__file__).parent.parent / "prove" / "file"
# la risposta dell'IA sulle categorie (fase 3), scritta a mano: AMAZON è incerta
CATEGORIE = {"ADDEBITO SDD ENEL ENERGIA SPA": ("bollette", True), "ADDEBITO SDD A2A ENERGIA GAS": ("bollette", True),
             "ADDEBITO SDD TIM SPA TELEFONO": ("bollette", True), "AMAZON EU SARL": ("bollette", False)}
BOLLETTE_OTTOBRE_2026 = {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
                         "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 10, "anno": 2026}}


@pytest.fixture(scope="module")
def conto():
    return leggi.leggi((FILE / "conto.csv").read_bytes(), "conto.csv")


@pytest.fixture(scope="module")
def vendite():
    return leggi.leggi((FILE / "vendite.xlsx").read_bytes(), "vendite.xlsx")


def _rispondi(tabella, r, lingua="it"):
    ric = richiesta.valida(r, tabella)
    return risposta.componi(ric, calcolo.esegui(tabella, ric, CATEGORIE), tabella, lingua)


# ---- C1: frase con il numero e righe la cui somma è il numero ----
def test_c01_bollette_ottobre_frase_numero_e_righe(conto):
    r = _rispondi(conto, BOLLETTE_OTTOBRE_2026)
    assert r["frase"] == "A ottobre 2026 hai speso 187,40 € in bollette."     # corta: il dettaglio è nelle righe
    assert sorted(x["importo"] for x in r["righe"]) == [31.00, 64.30, 92.10]
    assert len(r["righe"]) == 3
    assert round(sum(x["importo"] for x in r["righe"]), 2) == 187.40        # le spese si mostrano positive


def test_c01_se_righe_e_numero_non_tornano_niente_risposta(conto, monkeypatch):
    ric = richiesta.valida(BOLLETTE_OTTOBRE_2026, conto)
    esito = calcolo.esegui(conto, ric, CATEGORIE)
    esito.numero += 0.01                                   # un calcolo sbagliato
    with pytest.raises(calcolo.CalcoloNonTorna):
        risposta.componi(ric, esito, conto, "it")


# ---- C2: il prodotto che vende di più ----
def test_c02_prodotto_che_vende_di_piu(vendite):
    r = _rispondi(vendite, {"tipo": "calcolo", "operazione": "massimo", "misura": "importo", "raggruppa": "prodotto"})
    assert "Candela profumata" in r["frase"] and "11.500,00 €" in r["frase"]
    assert any(x.get("prodotto") == "Candela profumata" for x in r["righe"])


# ---- C3: grafico solo quando ha senso ----
def test_c03_grafico_per_andamento_mensile_non_per_un_numero(conto, vendite):
    andamento = _rispondi(vendite, {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "raggruppa": "mese"})
    assert andamento["grafico"] == "linea"
    un_numero = _rispondi(conto, {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "segno": "uscite",
                                  "periodo": {"mese": 10, "anno": 2026}})
    assert un_numero["grafico"] is None


# ---- C4: il calcolo è nascosto ma rifatto a mano dà lo stesso numero ----
def test_c04_come_l_ho_calcolato_rifatto_a_mano(conto):
    r = _rispondi(conto, BOLLETTE_OTTOBRE_2026)
    assert "bollette" in r["come"]["parole"] and "ottobre 2026" in r["come"]["parole"]
    df = calcolo.con_categorie(conto.df, CATEGORIE)
    assert round(abs(eval(r["come"]["pandas"], {"df": df})), 2) == 187.40     # solo nel test: rifaccio il conto


# ---- C5: dato che non c'è → nessun numero ----
def test_c05_dato_assente_lo_dice_senza_numeri(conto):
    r = _rispondi(conto, {"tipo": "assente", "cosa": "profitto"})
    assert "profitto" in r["frase"] and "importo" in r["frase"]
    assert not any(c.isdigit() for c in r["frase"]) and r["righe"] == []


def test_c05_colonna_inventata_rifiutata(conto):
    with pytest.raises(richiesta.RichiestaRifiutata):
        richiesta.valida({"tipo": "calcolo", "operazione": "somma", "misura": "profitto"}, conto)


# ---- C20: niente comandi, niente campi fuori schema ----
@pytest.mark.parametrize("cattiva", [
    {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "filtri": [{"colonna": "descrizione", "uguale": "open('/etc/passwd')"}]},
    {"tipo": "calcolo", "operazione": "somma", "misura": "__class__"},
    {"tipo": "calcolo", "operazione": "exec", "misura": "importo"},
    {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "codice": "import os"},
    {"tipo": "calcolo", "operazione": "somma", "misura": "importo", "filtri": [{"colonna": "descrizione", "uguale": "x').to_csv('a"}]},
])
def test_c20_richiesta_pericolosa_rifiutata_prima_di_calcolare(conto, cattiva):
    with pytest.raises(richiesta.RichiestaRifiutata):
        richiesta.valida(cattiva, conto)


def test_c20_anche_come_testo_json(conto):
    assert richiesta.valida('{"tipo": "calcolo", "operazione": "somma", "misura": "importo"}', conto).operazione == "somma"
    with pytest.raises(richiesta.RichiestaRifiutata):
        richiesta.valida("print(open('x').read())", conto)


def test_c16_ho_capito_e_frasi_leggibili_per_ogni_operazione(conto, vendite):
    """Ogni operazione ha la sua riga "Ho capito" in parole, senza segnaposto rimasti ({...})."""
    for op in ("somma", "conteggio", "media", "massimo", "minimo", "elenco"):
        for lingua in ("it", "en"):
            for extra in ({}, {"raggruppa": "prodotto"}):
                if op == "elenco" and extra:
                    continue
                r = _rispondi(vendite, {"tipo": "calcolo", "operazione": op, "misura": "importo", **extra}, lingua)
                assert "{" not in r["frase"] + r["ho_capito"] and r["ho_capito"], (op, lingua, extra, r)
    q = _rispondi(conto, {**BOLLETTE_OTTOBRE_2026, "periodo": {"mese": 10}})
    assert q["frase"] == "Quale ottobre: 2025 o 2026?"


def test_c01_la_spesa_piu_alta_e_il_massimo_delle_uscite(conto):
    r = _rispondi(conto, {"tipo": "calcolo", "operazione": "massimo", "misura": "importo", "segno": "uscite",
                          "periodo": {"mese": 10, "anno": 2026}})
    assert "92,10 €" in r["frase"] and r["righe"][0]["descrizione"] == "ADDEBITO SDD ENEL ENERGIA SPA"


# ---- F5: un testo che non si trova non diventa uno "0,00 €" ----
def test_c05_plurale_trova_lo_stesso_prodotto(vendite):
    r = _rispondi(vendite, {"tipo": "calcolo", "operazione": "somma", "misura": "importo",
                            "filtri": [{"colonna": "prodotto", "uguale": "candele"}], "periodo": {"mese": 12, "anno": 2025}})
    assert "500,00 €" in r["frase"]


def test_c05_testo_non_trovato_lo_dice_senza_zero(vendite):
    r = _rispondi(vendite, {"tipo": "calcolo", "operazione": "somma", "misura": "importo",
                            "filtri": [{"colonna": "prodotto", "uguale": "biciclette"}]})
    assert "biciclette" in r["frase"] and not any(c.isdigit() for c in r["frase"]) and r["numero"] is None


@pytest.mark.parametrize("r", [
    {**BOLLETTE_OTTOBRE_2026, "periodo": {"mese": 10, "anno": 2023}},                       # anno che non c'è
    {**BOLLETTE_OTTOBRE_2026, "filtri": [{"colonna": "categoria", "uguale": "salute"}]},     # categoria senza righe
    {"tipo": "calcolo", "operazione": "media", "misura": "importo", "periodo": {"anno": 2023}},
    {"tipo": "calcolo", "operazione": "massimo", "misura": "importo", "raggruppa": "mese", "periodo": {"anno": 2023}},
])
def test_c05_nessuna_riga_niente_zero(conto, r):
    x = _rispondi(conto, r)
    assert x["numero"] is None and "0,00" not in x["frase"] and "None" not in x["frase"], x["frase"]
    assert x["frase"].startswith("Nel file non ci sono righe per:")


def test_c03_andamento_dice_da_quanto_a_quanto(conto):
    r = _rispondi(conto, {**BOLLETTE_OTTOBRE_2026, "periodo": {"anno": 2026}, "raggruppa": "mese"})
    assert r["frase"] == "Nel 2026 hai speso 1.557,00 € in bollette, da 123,00 € a gennaio a 190,60 € a novembre."
    assert r["grafico"] == "linea"


def test_c01_il_numero_da_evidenziare_e_quello_della_frase(conto):
    r = _rispondi(conto, BOLLETTE_OTTOBRE_2026)
    assert r["numero_testo"] == "187,40 €" and r["numero_testo"] in r["frase"]
    assert _rispondi(conto, BOLLETTE_OTTOBRE_2026, "en")["numero_testo"] == "€187.40"
