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
- se la domanda nomina un tipo di spesa o entrata (bollette, spesa, stipendio, ristoranti...) filtra su "categoria",
  NON su "descrizione"; filtra su "descrizione" solo quando la domanda nomina un negozio o un'azienda (es. Esselunga, ENEL)
- "uguale" su una colonna di testo cerca quel testo dentro la colonna (es. il nome di un prodotto o di un negozio)
- profitto, utile, margine, guadagno netto, costi di pubblicità e simili NON sono entrate né uscite: se non c'è una
  colonna con quel significato rispondi {"tipo": "assente", "cosa": "..."}
- periodo: metti l'anno solo se la domanda lo dice o se c'è nella RICHIESTA PRECEDENTE; ometti periodo se non c'è
- "il prodotto che vende di più / di meno": operazione massimo / minimo, misura importo (in euro, a meno che la
  domanda dica pezzi o quantità), raggruppa prodotto
- in "uguale" copia il nome come appare tra i TESTI DEL FILE (es. "Candela profumata", non "candele")
- nelle vendite "quanto ho venduto / incassato / fatturato" è in euro (misura importo); misura quantita solo se la
  domanda dice pezzi, quantità o "quanti/quante"
- "mese per mese", "andamento": raggruppa "mese"
- se c'è una RICHIESTA PRECEDENTE e la domanda la continua ("e a novembre?"), restituisci la richiesta completa aggiornata
- ometti i campi che non servono
Esempi:
"Quanto ho speso in bollette a marzo 2025?" → {"tipo": "calcolo", "operazione": "somma", "misura": "importo",
 "segno": "uscite", "filtri": [{"colonna": "categoria", "uguale": "bollette"}], "periodo": {"mese": 3, "anno": 2025}}
"Qual è il prodotto che vende di più?" → {"tipo": "calcolo", "operazione": "massimo", "misura": "importo",
 "raggruppa": "prodotto"}
"Quanti pezzi di Quaderno ho venduto?" → {"tipo": "calcolo", "operazione": "somma", "misura": "quantita",
 "filtri": [{"colonna": "prodotto", "uguale": "Quaderno"}]}"""


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
    esito = calcolo.esegui(tabella, ric, categorie)
    try:
        r = risposta.componi(ric, esito, tabella, lingua)
    except calcolo.CalcoloNonTorna:
        return _messaggio("errore", lingua)
    r["esito"] = ("domanda_indietro" if esito.domanda_indietro else "non_trovato" if esito.non_trovato
                  else "nessuna_riga" if esito.nessuna_riga
                  else ric.tipo if ric.tipo != "calcolo" else "ok")
    r["richiesta"] = ric.model_dump(exclude_none=True)
    return r


def _messaggio(esito, lingua):
    return {"esito": esito, "frase": risposta.F[lingua][esito], "numero": None, "numero_testo": None, "ho_capito": "", "righe": [], "incerte": [],
            "grafico": None, "come": None, "domanda_indietro": None, "richiesta": None}
