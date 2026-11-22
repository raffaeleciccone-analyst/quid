# NLDA — domande ai tuoi dati

**Carichi l'estratto conto o le vendite del negozio e chiedi in italiano: "quanto ho speso in bollette a ottobre?".
Ricevi il numero, le righe da cui viene e la riga "Ho capito", così vedi subito se la domanda è stata capita bene.**

L'IA non calcola niente: traduce la domanda in una richiesta (cosa sommare, con quali filtri) e il programma fa il
conto. La frase della risposta la scrive il programma, non l'IA, quindi i numeri non possono essere inventati.

**Strumenti:** Python (pandas, FastAPI, pdfplumber), una pagina HTML/JavaScript, Groq online oppure Ollama sul PC.

## Cosa fa

- Legge **CSV, Excel e l'estratto conto in PDF**. Sistema da solo righe vuote, righe di totale, importi scritti come
  testo ("1.234,50 €") e colonne Entrate/Uscite separate, e **dice cosa ha sistemato**.
- Risponde con **una frase corta, le righe da cui viene il numero e il loro totale**: se le righe non danno il numero,
  la risposta non si mostra.
- Riconosce le **categorie** (bollette, spesa, stipendio…). Le righe incerte, come un pagamento ad Amazon, non entrano
  nel numero e si vedono a parte.
- Se la domanda è ambigua chiede: **"Quale ottobre: 2025 o 2026?"**. Se il dato non c'è lo dice ("nel file non c'è
  «profitto»"), e se non resta nessuna riga non risponde con uno zero.
- Ricorda la conversazione ("e a novembre?") e mostra sempre come l'ha capita.
- Pagina in italiano e in inglese, pensata anche per il telefono.

## La privacy

Con l'IA online (Groq) partono **solo i nomi delle colonne e le descrizioni con ogni cifra sostituita da #**
("PAGAMENTO CARTA #### ESSELUNGA"): mai importi, date, IBAN o numeri di carta. La pagina mostra l'elenco esatto di cosa
parte. Un test intercetta tutto ciò che esce e fallisce se trova anche una sola cifra del file. Il file resta in
memoria solo per la visita, non viene mai salvato.

## I risultati della prova

26 domande vere su un estratto conto e su un file di vendite, con le risposte giuste calcolate a parte:

| IA | Risposte giuste |
|---|---|
| Groq, `openai/gpt-oss-120b` (online, gratuito) | **26 su 26** (rifatta lo stesso giorno: 20 su 20, le ultime 6 bloccate dal limite giornaliero gratuito di Groq) |
| Ollama, `qwen2.5:3b` (sul PC) | 7 su 26: non riconosce le categorie |

Gli errori dell'IA sono sempre stati di comprensione, mai di calcolo, e la riga "Ho capito" li rende visibili.

**Limiti, detti chiaramente:**
- Sul PC serve un modello più grande e un computer adatto: con un modello piccolo le categorie sbagliano.
- Il PDF è provato su un estratto finto impaginato come quello di una banca: nessuna banca pubblica estratti di
  esempio con movimenti. Ogni banca impagina a modo suo; per questo, se il saldo iniziale più i movimenti letti non
  fa il saldo finale, NLDA non risponde.
- Online ci sono due tetti: 20 domande a persona e 300 al giorno in tutto, perché il piano gratuito di Groq ha un
  limite giornaliero. Se Groq non risponde, la pagina lo dice e suggerisce di riprovare o di usarlo sul PC.

## Avviarlo

```
pip install -r requirements.txt
python -m nlda                                   # sul PC, con Ollama: si apre il browser
NLDA_MODO=online NLDA_CHIAVE_FILE=percorso/chiave_groq.txt python -m nlda   # con Groq
```

La chiave di Groq sta in un file fuori dal progetto (oppure nella variabile `GROQ_API_KEY`), mai nel codice.

## Come è stato costruito

Prima la specifica: [SPEC.md](SPEC.md) dice cosa deve fare il programma e come si controlla ogni regola,
[PIANO.md](PIANO.md) dice come è fatto e perché. Ogni regola ha un test con il suo nome (`tests/`), e i file di
prova hanno numeri scelti a mano (`prove/crea_file.py`), così le risposte giuste si conoscono prima.

```
pip install -r requirements-dev.txt
python prove/crea_file.py        # rigenera i file di prova
python -m pytest                 # i test (quelli della pagina usano il Chrome installato)
python prove/prova_ia.py groq    # la prova con l'IA vera (serve la chiave)
```

Uso l'IA come strumento per scrivere codice; domanda, metodo e verifica dei numeri sono miei.
