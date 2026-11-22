# QUID — SPEC (cosa e perché)

> Nome scelto il 22/11/2026: QUID (QUestions on your Data; "il quid" = il punto essenziale).

> Questo file dice COSA deve fare il programma, non COME. Il come sta in PIANO.md.
> Stato: **APPROVATA il 22/11/2026** (intervista dello stesso giorno), F12 compresa. Riscrive da zero il vecchio
> Natural Language Data Analyst; il vecchio resta online finché il nuovo non lo sostituisce, con il via libera dell'utente.

## 1. Problema
Chi lavora con i dati in un file (vendite, prenotazioni) ma non sa programmare vuole fare domande in
italiano e avere numeri giusti. Un modello linguistico da solo inventa numeri plausibili: qui i numeri
li deve calcolare il codice, e il modello li racconta soltanto.

## 2. Uso principale
*(risposta del 22/11: "C", una persona vera al centro, il selezionatore di conseguenza)*
- U1. **Strada principale:** una persona che lavora con i propri file (es. le prenotazioni del B&B, le
  vendite in Excel di un piccolo negozio) lo usa davvero, più volte, sui suoi dati "sporchi", e ottiene
  risposte utili e numeri di cui fidarsi.
- U2. **Di conseguenza:** un selezionatore apre la demo dal CV, usa un file di esempio, fa due domande e
  vede che i numeri sono giusti e controllati. Non ci sono funzioni fatte solo per fare figura.

## 3. Cosa fa
*(F1-F4: forma della risposta, decisa il 22/11 sul consiglio di Claude accettato dall'utente)*
- F1. Risponde a una domanda in italiano con **una frase che contiene il numero** e, se serve, come si
  compone (es. "A ottobre hai speso 187,40 € in bollette: luce 92,10 €, gas 64,30 €, telefono 31,00 €").
- F2. Mostra sempre **le righe del file da cui viene il numero**, così l'utente controlla che siano quelle giuste.
  *(22/11, bozza della pagina approvata: la frase resta corta, "come si compone" lo mostra la tabella delle righe con
  il totale; l'andamento dice "da quanto a quanto", es. "da 123,00 € a gennaio a 190,60 € a novembre")*
- F3. Mostra un **grafico solo quando ha senso** (un andamento nel tempo, un confronto fra poche voci), non a ogni risposta.
- F4. Il calcolo esatto è **nascosto dietro "mostra come l'ho calcolato"**: c'è per chi lo vuole, ma non è la prova principale.

*(F5-F8: casi strani, proposte di Claude approvate dall'utente il 22/11)*
- F5. **Dato che non c'è:** se la domanda chiede qualcosa che nel file non esiste, lo dice e dice cosa c'è
  invece. Mai una risposta costruita su un'altra colonna.
- F6. **Domanda ambigua:** se la domanda si può leggere in più modi che danno numeri diversi (es. "ottobre"
  in un file con due anni), fa **una domanda indietro** ("Ottobre 2025 o 2026?") invece di scegliere da solo.
- F7. **Categoria incerta:** risponde con le righe di cui è sicuro e mette a parte quelle incerte
  ("queste 2 righe non so se sono bollette: AMAZON 12,99 €, …"), che non entrano nel numero.
- F8. **File sporco:** righe vuote, righe di totale, importi scritti come testo ("1.234,50 €"), colonne
  entrate/uscite separate → li sistema da solo e **dice cosa ha sistemato** ("Ho ignorato 2 righe di totale
  in fondo al file").

## 3b. Da dove arrivano i dati
*(risposta del 22/11: "D, ma principalmente B e C")*
- D1. Un file qualsiasi caricato dall'utente: deve cavarsela anche con file mai visti.
- D2. **I due casi che devono funzionare sempre** (sono quelli su cui si scrivono i criteri e i file di prova):
  - **vendite di un negozio**: Excel o CSV con data, prodotto, quantità, importo. Domande tipo "qual è il
    prodotto che vende di più?", "come sono andati gli ultimi 3 mesi?";
  - **spese e conti**: estratto conto in CSV (data, descrizione, importo, a volte con segno meno o con
    colonne entrate/uscite separate). Domande tipo "quanto spendo al mese in bollette?", "dove sono finiti
    i soldi a ottobre?".
- Gli altri file (es. prenotazioni) devono funzionare, ma non hanno criteri dedicati.
- D3. **Estratti conto PDF per i test:** *(risposta del 22/11 "partiamo da esempi")* si parte da estratti di
  esempio pubblicati dalle banche e da copie finte con la stessa impaginazione (nomi e importi inventati).
  Nessun estratto conto vero dell'utente nel repository né verso un'IA online.

*(F9-F10: privacy, risposta del 22/11 "C con B per Groq")*
- F9. **Cosa vede l'IA dipende da dove gira:**
  - **IA locale (Ollama sul PC):** può vedere tutto il file, perché niente esce dal computer.
  - **IA online (Groq):** vede i nomi delle colonne, i tipi e i **testi delle descrizioni** (es. "ENEL ENERGIA",
    "ESSELUNGA"), per capire le categorie. **Non vede mai importi, date precise, IBAN, numeri di carta o
    altri numeri del file.** I calcoli li fa il programma, non l'IA.
- F10. La pagina **dice sempre cosa sta per uscire** verso l'IA online (es. "a Groq mando: nomi delle colonne
  e 42 descrizioni; nessun importo"), e si può vedere l'elenco esatto.

*(F11-F12: formati, risposta del 22/11 "serve il pdf"; il controllo dei saldi è una proposta di Claude, da confermare)*
- F11. Legge **CSV, Excel e l'estratto conto in PDF**.
- F12. **Un PDF letto male non deve diventare un numero sbagliato:** dopo aver letto l'estratto conto controlla
  che *saldo iniziale + movimenti = saldo finale* (i saldi stampati nel PDF). Se non torna, non risponde: dice
  che la lettura non è affidabile e mostra dove non torna. Se il PDF non ha i saldi, lo dice e mostra le righe
  lette perché l'utente le controlli.

*(F13: domande che seguono, risposta del 22/11 "C")*
- F13. **Ricorda la conversazione e dice come ha capito:** "e a novembre?" dopo "quanto ho speso in bollette a
  ottobre?" vuol dire "bollette, novembre". Prima di ogni risposta mostra una riga "Ho capito: bollette,
  novembre 2026", così un errore di comprensione si vede subito. Un pulsante "Nuova domanda" riparte da zero.

*(F14: limiti online, risposta del 22/11 "A")*
- F14. **Online ci sono due tetti:** uno per visitatore e uno giornaliero per tutti (valori iniziali proposti:
  20 domande a persona, 300 al giorno; da tarare sui limiti gratuiti di Groq). Finito un tetto, il messaggio
  è chiaro: "Per oggi le domande online sono finite: riprova domani, o avvia QUID sul tuo PC" con il link alle
  istruzioni. Non si incollano chiavi personali nella pagina. Sul PC non ci sono tetti.

## 4. Cosa NON fa
*(proposte di Claude approvate dall'utente il 22/11: "togli tutto come consigli")*
- Niente **"Chiedi al progetto"** (chatbot sul progetto stesso): a chi usa i propri file non serve.
- Niente **report esecutivo** in sezioni (Summary, Insights, Recommendations…): bastano le risposte alle domande.
- **Una sola interfaccia**, non due.
- **Un fornitore di IA principale gratuito (Groq) più l'IA locale (Ollama)**; altri solo se serviranno.
- Niente **unione di due file**: per vendite ed estratti conto basta un file.
- Niente **account** e niente **salvataggio** dei file fra una visita e l'altra: il file resta solo per la sessione
  (più sicuro per un estratto conto).
- **Non modifica il file**: non corregge righe e non esporta un file pulito. Legge e risponde.

## 5. Criteri di controllo
Ogni criterio diventa almeno un test automatico. "Finito" = tutti i test passano. I file di prova sono due,
scritti a mano con numeri noti: **`vendite.xlsx`** (un negozio, 2 anni) e **`conto.csv`** (un estratto conto,
2 anni: ENEL ENERGIA, A2A GAS, TIM, ESSELUNGA, AMAZON, stipendio…), più **`conto.pdf`** (lo stesso estratto
impaginato come un PDF di banca, con saldo iniziale e finale) e un esempio pubblico di banca vera.

**La risposta (F1-F4)**
- C1 (F1, F2). "Quanto ho speso in bollette a ottobre 2026?" su `conto.csv` → frase con **187,40 €** e le 3 righe
  (luce 92,10, gas 64,30, telefono 31,00). **La somma delle righe mostrate è uguale al numero della frase**: se non
  lo è, la risposta non si mostra.
- C2 (F1). "Qual è il prodotto che vende di più?" su `vendite.xlsx` → il prodotto giusto, con il numero, e le righe
  da cui viene (o il riepilogo per prodotto).
- C3 (F3). "Come sono andate le vendite mese per mese?" → c'è un grafico. "Quanto ho speso a ottobre?" (un numero
  solo) → nessun grafico.
- C4 (F4). Il calcolo usato è visibile solo aprendo "mostra come l'ho calcolato", e rifatto a mano dà lo stesso numero.

**Casi strani (F5-F8)**
- C5 (F5). "Quanto ho guadagnato di profitto?" su `conto.csv` (non c'è un profitto) → dice che il dato non c'è e
  cosa c'è (entrate, uscite); **nessun numero** nella risposta.
- C6 (F6). "Quanto ho speso a ottobre?" su un file con ottobre 2025 e ottobre 2026 → domanda indietro "Ottobre 2025
  o 2026?", nessun numero finché non si sceglie. Su un file con un solo ottobre → risponde subito.
- C7 (F7). "Quanto spendo in bollette?" con una riga "AMAZON 12,99" → AMAZON **non entra** nel numero e compare tra
  le righe incerte.
- C8 (F8). `conto_sporco.csv` (2 righe vuote, una riga "TOTALE" in fondo, importi come testo "1.234,50 €", colonne
  Entrate/Uscite separate) → stessi numeri di `conto.csv`, e il messaggio dice cosa è stato sistemato ("ignorate 2
  righe vuote e 1 riga di totale").

**Privacy (F9-F10)**
- C9 (F9). Con l'IA online, tutto quello che parte verso Groq durante una domanda su `conto.csv` viene intercettato
  nel test: contiene "ENEL ENERGIA", **non contiene nessun importo, nessuna data del file, nessun IBAN o numero di
  carta** presenti nel file.
- C10 (F9). Con l'IA locale lo stesso controllo non si applica, e la pagina dice "IA sul tuo PC: niente esce".
- C11 (F10). Prima della prima domanda online la pagina mostra cosa partirà ("nomi delle colonne e N descrizioni;
  nessun importo") e l'elenco esatto si può aprire.

**Formati e PDF (F11-F12)**
- C12 (F11). `vendite.xlsx`, `vendite.csv` con `;` e `conto.csv` in codifica non UTF-8 → letti con gli stessi numeri.
- C13 (F12). `conto.pdf` → righe uguali a `conto.csv`, e il controllo "saldo iniziale + movimenti = saldo finale" torna.
- C14 (F12). `conto_pdf_rotto.pdf` (una riga persa nella lettura) → il controllo non torna, **nessuna risposta**, e il
  messaggio dice di quanto non torna.
- C15 (F11). Un file che non è un estratto né una tabella (un PDF di testo, un'immagine, un file vuoto) → messaggio
  chiaro in italiano/inglese, mai una pagina di errore.

**Conversazione (F13)**
- C16 (F13). "Quanto ho speso in bollette a ottobre 2026?" poi "e a novembre?" → la riga "Ho capito: bollette,
  novembre 2026" e il numero di novembre. Dopo "Nuova domanda", "e a novembre?" da solo → chiede cosa si intende.

**Online e telefono (F14, vincoli)**
- C17 (F14). La 21ª domanda dello stesso visitatore, o la 301ª del giorno → messaggio dei tetti, nessuna chiamata a
  Groq. Il giorno dopo si riparte. Avviato sul PC → nessun tetto.
- C18. A 390 px di larghezza (telefono) la pagina non scorre di lato e si carica un file e si fa una domanda.
- C19. Con il pulsante EN la pagina è in inglese; "How much did I spend on bills in October 2026?" dà lo stesso
  numero di C1.

**Sicurezza del calcolo**
- C20. Qualunque cosa risponda l'IA, il programma non può leggere o scrivere file, aprire connessioni o eseguire
  comandi: una risposta dell'IA che chiede una di queste cose (es. contiene `open`, `import`, `to_csv`) viene
  rifiutata prima di fare qualsiasi calcolo. *(Come si ottiene lo decide il PIANO: potrebbe anche non esserci
  codice scritto dall'IA da eseguire.)*

## 6. Vincoli
*(risposta del 22/11: "C, e sì anche dal telefono")*
- **Lo stesso programma in due modi:** pagina web online (demo e uso veloce, con Groq e la regola di F9) e
  avvio sul PC (si apre nel browser, IA locale, niente esce dal computer). La pagina dice sempre in quale
  modo sta girando.
- **Telefono:** deve funzionare bene anche dal telefono (caricare l'estratto conto scaricato dall'app della
  banca e fare domande), non solo dal PC.
- **Lingua** *(risposta del 22/11 "B")*: italiano e inglese con il pulsante, come il sito del calcio. Le domande
  funzionano nelle due lingue; formati italiani ("1.234,50 €", date gg/mm/aaaa) restano il caso principale.
- Il vecchio NLDA resta online fino al cambio.

## 7. Domande aperte
- ~~Cosa del vecchio progetto tenere~~ Risolta il 22/11: vedi "Cosa NON fa".
- Quali banche: cercati il 22/11 estratti di esempio pubblici di banche italiane: nessuno utilizzabile (le banche
  pubblicano guide e contratti, non estratti con movimenti). Per ora si resta sul PDF finto `conto.pdf`. Più avanti, se l'utente vorrà, una prova su un suo
  PDF vero, tenuto solo sul suo PC.
- ~~F12 da confermare~~ Confermata con l'approvazione del 22/11.
- **IA locale su questo PC (prova del 22/11):** qwen2.5:3b 7/26 (non riconosce le categorie), qwen3:4b troppo lenta
  (in 28 minuti non finisce il primo passo). Groq 26/26. La modalità PC funziona ma la qualità dipende dal modello e
  dal computer: va scritto chiaramente nella pagina e nel README. Da decidere se suggerire un modello più grande.

