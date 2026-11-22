"""Il percorso di una domanda: messaggio (senza dati privati) → IA → richiesta validata → calcolo → risposta.
Se l'IA risponde male si riprova una volta; un rifiuto di sicurezza non si riprova. SPEC F1-F6, F9, F13; C20."""
import json

from . import calcolo, privacy, risposta
from .categorie import CATEGORIE
from .richiesta import RichiestaRifiutata, valida

SISTEMA = """Traduci una domanda sui dati di un file in una RICHIESTA JSON. Non calcolare niente: i numeri li calcola il programma.
Rispondi SOLO con un oggetto JSON in uno di questi formati:
{"tipo": "calcolo", "operazione": "...", "misura": "...", "filtri": [{"colonna": "...", "uguale": "..."}],
 "periodo": {"mese": M, "anno": A}, "raggruppa": "...", "segno": "..."}
{"tipo": "assente", "cosa": "..."}     se il file non contiene il dato chiesto (es. il profitto in un estratto conto)
{"tipo": "non_capito"}                 se la domanda non riguarda il file
Regole:
- operazione: somma | conteggio | media | massimo | minimo | elenco
- misura, colonna e raggruppa: SOLO nomi tra le COLONNE date, oppure "categoria" (estratto conto) e "mese" per raggruppa
- negli estratti conto le uscite sono importi negativi: per "quanto ho speso" usa segno "uscite", per "quanto ho
  incassato/ricevuto" segno "entrate"; categoria è una di: """ + ", ".join(CATEGORIE) + """
- "uguale" su una colonna di testo cerca quel testo dentro la colonna (es. il nome di un prodotto o di un negozio)
- periodo: metti l'anno solo se la domanda lo dice o se c'è nella RICHIESTA PRECEDENTE; ometti periodo se non c'è
- "il prodotto che vende di più": operazione massimo, misura importo, raggruppa prodotto
- "mese per mese", "andamento": raggruppa "mese"
- se c'è una RICHIESTA PRECEDENTE e la domanda la continua ("e a novembre?"), restituisci la richiesta completa aggiornata
- ometti i campi che non servono"""


def rispondi(tabella, testo, ia, categorie, precedente, lingua="it") -> dict:
    utente = privacy.messaggio(tabella, testo, precedente)
    ric = None
    for _ in range(2):
        grezza = ia.chiedi(SISTEMA, utente)
        try:
            dati = json.loads(grezza)
            ric = valida(dati, tabella)
            break
        except ValueError:
            esito = "non_capito"
        except RichiestaRifiutata as e:
            esito = "rifiutata"
            if e.chiave == "sicurezza":
                break
    if ric is None:
        return _messaggio(esito, lingua)
    try:
        r = risposta.componi(ric, calcolo.esegui(tabella, ric, categorie), tabella, lingua)
    except calcolo.CalcoloNonTorna:
        return _messaggio("errore", lingua)
    r["esito"] = ("domanda_indietro" if r["domanda_indietro"] else ric.tipo if ric.tipo != "calcolo" else "ok")
    r["richiesta"] = ric.model_dump(exclude_none=True)
    return r


def _messaggio(esito, lingua):
    return {"esito": esito, "frase": risposta.F[lingua][esito], "ho_capito": "", "righe": [], "incerte": [],
            "grafico": None, "come": None, "domanda_indietro": None, "richiesta": None}
