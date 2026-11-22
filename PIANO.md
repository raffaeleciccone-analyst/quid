# NLDA (riscrittura) — PIANO (come)

> Il COSA sta in SPEC.md. Qui c'è il COME.
> Ogni scelta tecnica cita la frase della spec che la giustifica.
> Se una scelta qui contraddice la spec, vince la spec: si corregge il piano.
> Stato: **APPROVATO il 22/11/2026**. Regola "ponytail": il codice più piccolo che fa il lavoro.

## 1. Architettura

```
 file (CSV / Excel / PDF)
        │  leggi.py, pdf.py          F8, F11, F12
        ▼
 TABELLA PULITA  ◄── porta d'ingresso n.1 (§2)   + "cosa ho sistemato" (F8)
        │
 domanda ──► ia.py ──► RICHIESTA (JSON) ◄── porta d'ingresso n.2 (§2)
             ▲            │  richiesta.py: si accetta solo se rispetta lo schema   C20
             │            ▼
   privacy.py: l'IA vede solo  calcolo.py: esegue la richiesta con pandas →
   colonne, tipi e descrizioni  numero + righe da cui viene (somma = numero)   C1
   senza cifre            F9    │
                                ▼
                         risposta.py: frase, "Ho capito: …", grafico sì/no   F1, F3, F13
                                │
                         app.py (FastAPI) + web/ (una pagina, IT/EN)   F14, vincoli
```

**La scelta più importante: l'IA non scrive codice.** Nel vecchio NLDA l'IA scriveva codice pandas che il
programma eseguiva, e metà del progetto era la sandbox per renderlo sicuro. Qui l'IA risponde solo con una
**richiesta** in JSON (cosa calcolare, su quale colonna, con quali filtri), che il programma controlla contro uno
schema fisso e poi esegue con regole sue. Non c'è codice dell'IA da eseguire, quindi non può leggere file né aprire
connessioni per costruzione. Motivo: C20 (e la nota "potrebbe anche non esserci codice scritto dall'IA").

**L'IA non scrive neanche i numeri.** La frase della risposta la compone il programma da modelli di frase IT/EN, con
i numeri calcolati. L'IA traduce la domanda in richiesta e riconosce le categorie, nient'altro. Motivo: F1 e il
problema della spec ("un modello da solo inventa numeri plausibili").

## 2. Porte d'ingresso

**Porta n.1, la tabella pulita.** Ogni lettore (CSV, Excel, PDF) produce la stessa cosa:

```python
Tabella(
  tipo="conto",            # "conto" | "vendite" | "altro"
  df=DataFrame,            # conto: data, descrizione, importo (uscite negative)
                           # vendite: data, prodotto, quantita, importo
                           # altro: le colonne originali, con tipo riconosciuto
  sistemato=["ignorate 2 righe vuote", "ignorata 1 riga di totale"],   # F8
  saldi=(saldo_iniziale, saldo_finale) | None,                         # F12, solo PDF
)
```
Così il PDF (la parte più fragile) è un solo file da scrivere: tutto il resto lavora già con CSV ed Excel. Motivo: F11.

**Porta n.2, la richiesta.** Quello che l'IA deve restituire, e niente altro:

```json
{"tipo": "calcolo",
 "operazione": "somma",            // somma | conteggio | media | massimo | minimo | elenco
 "misura": "importo",
 "filtri": [{"colonna": "categoria", "uguale": "bollette"}],
 "periodo": {"mese": 10, "anno": 2026},       // anno null = non detto
 "raggruppa": null,                 // null | "mese" | nome di colonna
 "segno": "uscite"}                 // conto: uscite | entrate | tutti
```
oppure `{"tipo": "assente", "cosa": "profitto"}` (F5) oppure `{"tipo": "non_capito"}`.
Si valida con pydantic: un campo in più, una colonna inesistente, un'operazione fuori elenco → rifiutata (C20, C5).

## 3. Scelte e motivi

- **Ambiguità decisa dal programma, non dall'IA.** Se il periodo ha il mese ma non l'anno e nel file ci sono più
  anni con quel mese → domanda indietro "Ottobre 2025 o 2026?". È una regola, quindi si testa sempre uguale. F6, C6.
- **Categorie (F7).** Le descrizioni diverse del file (senza cifre) vanno all'IA una volta per file: per ognuna
  risponde categoria e "certa/incerta". Le incerte non entrano nel numero e si mostrano a parte. La risposta
  dell'IA si tiene per la sessione. F7, C7.
- **Privacy (F9).** `privacy.py` costruisce l'unico messaggio che parte verso l'IA: nomi delle colonne, tipi,
  descrizioni con **ogni cifra sostituita da `#`** ("PAGAMENTO POS ##/## ESSELUNGA"), la domanda, la richiesta
  precedente. Lo stesso messaggio vale anche per l'IA locale: la spec dice che lì *può* vedere tutto, non che deve;
  un solo percorso è meno codice e più privacy. La pagina mostra proprio quel messaggio (F10, C11). C9 si prova
  intercettando il messaggio nel test.
- **Somma = numero (C1).** `calcolo.py` restituisce le righe usate e il numero; prima di rispondere si ricontrolla
  che la somma delle righe dia il numero. Se no, errore e nessuna risposta.
- **Grafico (F3).** Regola: `raggruppa` per mese → linea; `raggruppa` per voce con 2-12 voci → barre; altrimenti
  niente. Disegnato in SVG nella pagina, senza librerie.
- **"Mostra come l'ho calcolato" (F4).** La richiesta scritta in parole ("somma di importo, uscite, categoria
  bollette, ottobre 2026") più l'equivalente pandas di una riga, per chi lo vuole.
- **Conversazione (F13).** All'IA vanno la domanda nuova e la richiesta precedente; restituisce la richiesta
  completa. "Ho capito: …" la scrive il programma dalla richiesta. "Nuova domanda" cancella la precedente.
- **PDF (F11, F12).** `pdfplumber`: si leggono le righe con data, descrizione, importo e i saldi stampati; poi
  saldo iniziale + somma movimenti deve dare il saldo finale al centesimo, altrimenti nessuna risposta.
- **IA (vincoli).** Due fornitori, ognuno nel suo formato: Groq (Chat Completions, risposta in JSON) e Ollama
  (`/api/chat`, `format: json`). La chiave Groq sta in un file fuori dal repository, letto da variabile d'ambiente.
- **Un'interfaccia sola, senza React.** FastAPI serve una pagina HTML + JavaScript + CSS, con `testi.json` IT/EN
  come il sito del calcio. Vincoli (telefono, lingua), "Cosa NON fa" (una sola interfaccia).
- **Sessione in memoria.** Il file letto sta in memoria, legato a un identificativo di sessione, e scade dopo un'ora
  senza uso; non si scrive mai su disco. "Cosa NON fa" (niente salvataggio).
- **Tetti online (F14).** Contatori in memoria: per visitatore (cookie di sessione) e per giorno. Sul PC
  (`NLDA_MODO=pc`) i tetti non si applicano. Se il server si riavvia i contatori ripartono: accettabile e scritto.
- **Online e PC (vincoli).** Lo stesso programma: online su Render con Groq; sul PC `python -m nlda` apre il browser
  e usa Ollama. La pagina dice in quale modo gira.

## 4. Struttura del codice

```
nlda/
  leggi.py        CSV ed Excel → Tabella: codifica, separatore, importi "1.234,50 €", righe vuote e di totale,
                  entrate/uscite separate, riconoscimento conto/vendite/altro            F8, F11
  pdf.py          estratto conto PDF → Tabella con i saldi; controllo dei saldi           F11, F12
  richiesta.py    schema della richiesta e validazione                                    C20, F5
  calcolo.py      esegue la richiesta: numero + righe; regola di ambiguità; ricontrollo   F1, F2, F6, C1
  categorie.py    descrizioni → categoria certa/incerta (via IA)                          F7
  privacy.py      l'unico messaggio verso l'IA, senza cifre                               F9, F10
  ia.py           Groq e Ollama                                                           vincoli
  risposta.py     frasi IT/EN, "Ho capito", grafico sì/no, "come l'ho calcolato"          F1, F3, F4, F13
  app.py          FastAPI: carica file, domanda, nuova domanda, anteprima privacy, tetti   F10, F13, F14
  __main__.py     avvio sul PC
web/              index.html, app.js, stile.css, testi.json                               vincoli, C18, C19
prove/crea_file.py  scrive i file di prova con numeri noti (conto.csv, conto_sporco.csv, conto.pdf,
                    conto_pdf_rotto.pdf, vendite.xlsx, vendite.csv)
tests/            un file per gruppo di criteri; l'IA nei test è finta (risposte scritte a mano)
```

## 5. Test

`python -m pytest`. Un test per criterio, con il criterio nel nome (`test_c01_somma_righe_uguale_al_numero`).
- I file di prova li genera `prove/crea_file.py` con numeri scelti a mano: le risposte giuste si conoscono prima.
- L'IA nei test è un finto fornitore che restituisce richieste scritte a mano e **registra ogni messaggio ricevuto**
  (serve a C9).
- C18 (telefono) e C19 (inglese) con Playwright, pagina vera a 390 px.
- Una prova separata, non nei test automatici, con Groq e Ollama veri su un elenco di domande, come per l'assistente
  del calcio: risultato salvato in `prove/`.
- Il PDF di banca vero pubblico (D3): si cerca nella fase PDF; se nessuna banca ne pubblica uno utilizzabile, si
  resta sul PDF finto e lo si scrive nelle domande aperte.

## 6. Da fare (fasi)
- [x] 0. File di prova con numeri noti (`prove/crea_file.py`).
- [x] 1. Lettura CSV/Excel e file sporco (C8, C12, C15).
- [x] 2. Richiesta, calcolo e frasi con IA finta (C1-C5, C20).
- [x] 3. Ambiguità e categorie (C6, C7).
- [x] 4. Privacy e IA vere (C9-C11) + prova su domande vere: Groq 26/26 (`prove/ia_groq_*.json`).
  Scelte nuove: le spese si calcolano come importi positivi ("la spesa più alta" = massimo); se dopo i filtri non resta
  nessuna riga o un testo non si trova, niente numero ("Nel file non ci sono righe per: …"), mai uno "0,00 €";
  "candele" trova "Candela" (radice della parola); Groq riprova da solo quando dice 429; istruzioni con esempi.
- [x] 5. PDF e saldi (C13, C14). Le colonne Addebiti/Accrediti si leggono dalla riga d'intestazione (non dalle
  descrizioni "ADDEBITO SDD …": era il primo errore, scoperto proprio dal controllo dei saldi). Nessun estratto pubblico
  di banca vera utilizzabile: si prova sul PDF finto; il PDF vero dell'utente resta una prova facoltativa sul suo PC.
- [x] 6. Pagina: conversazione, IT/EN, telefono (C16, C18, C19). Bozza approvata il 22/11. Difetti trovati provandola:
  il verde evidenziava l'anno invece dell'importo (ora il server manda `numero_testo`); sul telefono la riga di codice
  di "come l'ho calcolato" allargava la pagina a 1.086 px (griglia `minmax(0, 1fr)`). Il primo test C18 misurava a
  riquadri chiusi e NON se ne accorgeva: ora misura con tutto aperto, e la prova di rottura lo fa fallire.
  Avvio: `NLDA_MODO=online NLDA_CHIAVE_FILE=… python -m nlda` (porta 8793) oppure `python -m nlda` sul PC (Ollama).
- [ ] 7. Tetti e pubblicazione (C17); poi, col via libera, il cambio con il vecchio NLDA.
