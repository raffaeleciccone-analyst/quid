"""C17: online ci sono due tetti (per visitatore e per giorno); finiti, niente chiamate all'IA; il giorno dopo si riparte;
sul PC nessun tetto. Tetti piccoli nei test (3 a persona, 5 al giorno) per non fare centinaia di domande."""
import json
from datetime import date
from pathlib import Path

from fastapi.testclient import TestClient

from nlda.app import crea_app

FILE = Path(__file__).parent.parent / "prove" / "file"
SOMMA = {"tipo": "calcolo", "operazione": "somma", "misura": "importo"}


class IAContata:
    esce_dal_pc = True

    def __init__(self):
        self.chiamate = 0

    def chiedi(self, sistema, utente):
        self.chiamate += 1
        return json.dumps({} if utente.startswith("CATEGORIE:") else SOMMA)


class Orologio:
    def __init__(self):
        self.giorno = date(2026, 11, 22)

    def __call__(self):
        return self.giorno


def _cliente(app, ip):
    c = TestClient(app, client=(ip, 50000))
    c.post("/api/file", files={"file": ("vendite.csv", (FILE / "vendite.csv").read_bytes())})
    return c


def _chiedi(c):
    return c.post("/api/domanda", json={"testo": "totale?", "lingua": "it"})


def test_c17_tetto_per_visitatore_poi_niente_ia():
    ia = IAContata()
    app = crea_app(ia, modo="online", tetti=(3, 100), oggi=Orologio())
    c = _cliente(app, "1.1.1.1")
    assert [_chiedi(c).status_code for _ in range(3)] == [200, 200, 200]
    prima = ia.chiamate
    r = _chiedi(c)
    assert r.status_code == 429 and r.json()["errore"] == "tetto_persona" and ia.chiamate == prima
    assert _chiedi(_cliente(app, "2.2.2.2")).status_code == 200            # un altro visitatore può ancora


def test_c17_tetto_giornaliero_per_tutti_e_il_giorno_dopo_si_riparte():
    ia, orologio = IAContata(), Orologio()
    app = crea_app(ia, modo="online", tetti=(100, 5), oggi=orologio)
    visitatori = [_cliente(app, f"10.0.0.{i}") for i in range(6)]
    risposte = [_chiedi(v).status_code for v in visitatori]
    assert risposte == [200] * 5 + [429]
    assert _chiedi(visitatori[0]).json()["errore"] == "tetto_giorno"
    orologio.giorno = date(2026, 11, 23)
    assert _chiedi(visitatori[5]).status_code == 200


def test_c17_sul_pc_nessun_tetto():
    ia = IAContata()
    ia.esce_dal_pc = False
    app = crea_app(ia, modo="pc", tetti=(1, 1), oggi=Orologio())
    c = _cliente(app, "1.1.1.1")
    assert [_chiedi(c).status_code for _ in range(4)] == [200] * 4
