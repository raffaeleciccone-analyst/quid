"""Prova con un'IA vera: domande su conto e vendite, risposta giusta calcolata qui a parte con pandas (non con quid).
Uso:  QUID_CHIAVE_FILE=~/.chiavi/groq.txt python prove/prova_ia.py groq
      python prove/prova_ia.py ollama [modello]
Risultato in prove/ia_<fornitore>_<modello>.json. Non è un test automatico: chiama un modello vero."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from quid import categorie, domanda, ia, leggi  # noqa: E402

F = Path(__file__).parent / "file"
conto = leggi.leggi((F / "conto.csv").read_bytes(), "conto.csv")
vend = leggi.leggi((F / "vendite.xlsx").read_bytes(), "vendite.xlsx")
c, v = conto.df, vend.df
bol = c.descrizione.str.contains("ENEL|A2A|TIM")
usc = c.importo < 0
y = c.data.dt.year
m = c.data.dt.month
vy, vm = v.data.dt.year, v.data.dt.month


def s(x):
    return round(float(abs(x)), 2)


# (domanda, esito atteso, numero atteso o None, domanda precedente da cui continuare o None)
DOMANDE = [
    ("Quanto ho speso in bollette a ottobre 2026?", "ok", s(c[bol & (y == 2026) & (m == 10)].importo.sum()), None),
    ("Quanto ho speso in bollette a novembre 2026?", "ok", s(c[bol & (y == 2026) & (m == 11)].importo.sum()), None),
    ("Quanto ho speso in bollette a ottobre?", "domanda_indietro", None, None),
    ("Quanto ho speso in bollette nel 2025?", "ok", s(c[bol & (y == 2025)].importo.sum()), None),
    ("Quanto ho speso all'Esselunga nel 2026?", "ok", s(c[c.descrizione.str.contains("ESSELUNGA") & (y == 2026)].importo.sum()), None),
    ("Quanto ho incassato di stipendio nel 2025?", "ok", s(c[(c.importo > 0) & (y == 2025)].importo.sum()), None),
    ("Quante volte ho pagato TIM?", "ok", float(c.descrizione.str.contains("TIM").sum()), None),
    ("Quanto spendo in media di luce con ENEL?", "ok", s(c[c.descrizione.str.contains("ENEL")].importo.mean()), None),
    ("Qual è stata la spesa più alta a ottobre 2026?", "ok", s(c[usc & (y == 2026) & (m == 10)].importo.min()), None),
    ("Quanto ho speso in totale nel 2026?", "ok", s(c[usc & (y == 2026)].importo.sum()), None),
    ("Come sono andate le mie spese mese per mese nel 2026?", "ok", s(c[usc & (y == 2026)].importo.sum()), None),
    ("Quanto ho guadagnato di profitto?", "assente", None, None),
    ("Chi ha vinto lo scudetto?", "non_capito", None, None),
    ("e a novembre?", "ok", s(c[bol & (y == 2026) & (m == 11)].importo.sum()), "Quanto ho speso in bollette a ottobre 2026?"),
    ("In quale mese del 2026 ho speso di più in bollette?", "ok",
     s(c[bol & (y == 2026)].groupby(m).importo.sum().min()), None),
    ("How much did I spend on bills in October 2026?", "ok", s(c[bol & (y == 2026) & (m == 10)].importo.sum()), None),
    ("Qual è il prodotto che vende di più?", "ok", s(v.groupby("prodotto").importo.sum().max()), None),
    ("Quanto ho incassato in totale nel 2025?", "ok", s(v[vy == 2025].importo.sum()), None),
    ("Quante tazze ho venduto nel 2026?", "ok", s(v[v.prodotto.str.contains("Tazza") & (vy == 2026)].quantita.sum()), None),
    ("Qual è il prodotto che vende di meno?", "ok", "Cornice", None),   # in euro o in pezzi è sempre Cornice
    ("Quanto ho venduto a marzo 2026?", "ok", s(v[(vy == 2026) & (vm == 3)].importo.sum()), None),
    ("Come sono andate le vendite mese per mese?", "ok", s(v.importo.sum()), None),
    ("Quanto ho incassato con le candele a dicembre 2025?", "ok",
     s(v[v.prodotto.str.contains("Candela") & (vy == 2025) & (vm == 12)].importo.sum()), None),
    ("Qual è il prezzo medio dei quaderni?", "ok", s(v[v.prodotto == "Quaderno"].prezzo.mean()), None),
    ("Quanti quaderni ho venduto in tutto?", "ok", s(v[v.prodotto == "Quaderno"].quantita.sum()), None),
    ("Quanto ho speso in pubblicità?", "assente", None, None),
]


def main():
    fornitore = sys.argv[1] if len(sys.argv) > 1 else "groq"
    modello = sys.argv[2] if len(sys.argv) > 2 else None
    cervello = ia.Groq(modello=modello) if fornitore == "groq" else ia.Ollama(modello=modello)
    cat = categorie.classifica(c.descrizione, cervello)
    esiti, giuste = [], 0
    for testo, atteso, numero, prima in DOMANDE:
        tab = conto if DOMANDE.index((testo, atteso, numero, prima)) < 16 else vend
        lingua = "en" if testo.startswith("How") else "it"
        t0 = time.time()
        try:
            prec = domanda.rispondi(tab, prima, cervello, cat, None, lingua)["richiesta"] if prima else None
            r = domanda.rispondi(tab, testo, cervello, cat, prec, lingua)
        except Exception as e:  # un errore di rete o di quota si registra, non ferma la prova
            r = {"esito": "eccezione", "frase": str(e)[:200], "richiesta": None, "numero": None}
        ottenuto = r.get("numero")
        if isinstance(numero, str):
            ok = r["esito"] == atteso and numero in r["frase"]
        else:
            ok = r["esito"] == atteso and (numero is None or (ottenuto is not None and round(abs(ottenuto), 2) == numero))
        giuste += ok
        esiti.append({"domanda": testo, "ok": ok, "atteso": [atteso, numero], "esito": r["esito"], "numero": ottenuto,
                      "frase": r["frase"], "ho_capito": r.get("ho_capito"), "richiesta": r.get("richiesta"),
                      "secondi": round(time.time() - t0, 1)})
        print(("OK " if ok else "NO ") + testo, "→", r["frase"][:110])
    nome = f"ia_{fornitore}_{(modello or cervello.modello).replace('/', '-').replace(':', '-')}.json"
    bollette = sorted(d for d, (k, certa) in cat.items() if k == "bollette")
    (Path(__file__).parent / nome).write_text(json.dumps({"giuste": giuste, "totale": len(DOMANDE),
                                                          "categorie_bollette": bollette, "esiti": esiti},
                                                         ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n{giuste}/{len(DOMANDE)} giuste. Bollette riconosciute: {bollette}")


if __name__ == "__main__":
    main()
