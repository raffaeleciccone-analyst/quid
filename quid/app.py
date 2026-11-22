"""Il server: carica il file, risponde alle domande, ricorda la conversazione. SPEC F10, F13, vincoli; C10-C16, C19.
Il file letto resta in memoria per la sessione (un'ora senza uso) e non va mai su disco ("Cosa NON fa")."""
import os
import time
import uuid
from datetime import date
from pathlib import Path

from fastapi import FastAPI, Request, Response, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import calcolo, categorie, domanda, leggi, privacy, risposta
from .richiesta import valida

WEB = Path(__file__).parent.parent / "web"
SCADENZA = 3600
MAX_BYTE = 10 * 1024 * 1024


def crea_app(ia=None, modo=None, tetti=None, oggi=date.today):
    """tetti = (domande per visitatore al giorno, domande al giorno per tutti): solo online (F14, C17)."""
    modo = modo or os.environ.get("QUID_MODO", "online")
    tetti = tetti or (int(os.environ.get("QUID_TETTO_PERSONA", 20)), int(os.environ.get("QUID_TETTO_GIORNO", 300)))
    conteggi = {"giorno": None, "tutti": 0, "persone": {}}
    if ia is None:
        from . import ia as fornitori
        ia = fornitori.Ollama() if modo == "pc" else fornitori.Groq()
    app = FastAPI(docs_url=None, redoc_url=None)
    sessioni = {}

    def sessione(request, response):
        for k in [k for k, s in sessioni.items() if time.time() - s["uso"] > SCADENZA]:
            del sessioni[k]
        sid = request.cookies.get("quid")
        if sid not in sessioni:
            sid = uuid.uuid4().hex
            sessioni[sid] = {"tabella": None, "categorie": {}, "precedente": None}
            response.set_cookie("quid", sid, httponly=True, samesite="lax")
        sessioni[sid]["uso"] = time.time()
        return sessioni[sid]

    def errore(chiave, dettagli=None, codice=400):
        return JSONResponse({"errore": chiave, "dettagli": dettagli or {}}, codice)

    def tetto(request):
        """C17: None se si può chiamare l'IA (e la conta), altrimenti il nome del tetto raggiunto. Sul PC niente tetti."""
        if not ia.esce_dal_pc:
            return None
        if conteggi["giorno"] != oggi():
            conteggi.update(giorno=oggi(), tutti=0, persone={})
        chi = (request.headers.get("x-forwarded-for", "").split(",")[0].strip()
               or (request.client.host if request.client else "?"))
        if conteggi["tutti"] >= tetti[1]:
            return "tetto_giorno"
        if conteggi["persone"].get(chi, 0) >= tetti[0]:
            return "tetto_persona"
        conteggi["tutti"] += 1
        conteggi["persone"][chi] = conteggi["persone"].get(chi, 0) + 1
        return None

    @app.get("/api/modo")
    def modo_attuale():
        return {"modo": modo, "esce": bool(ia.esce_dal_pc)}

    @app.post("/api/file")
    async def carica(file: UploadFile, request: Request, response: Response):
        s = sessione(request, response)
        dati = await file.read(MAX_BYTE + 1)
        if len(dati) > MAX_BYTE:
            return errore("troppo_grande")
        try:
            t = leggi.leggi(dati, file.filename or "")
        except leggi.FileNonLeggibile as e:
            return errore(e.chiave, e.dettagli)
        s.update(tabella=t, precedente=None,
                 categorie=categorie.classifica(t.df["descrizione"], ia) if t.tipo == "conto" else {})
        return {"nome": file.filename, "tipo": t.tipo, "righe": len(t.df), "sistemato": t.sistemato,
                "saldi": t.saldi, "anteprima": privacy.anteprima(t)}

    @app.post("/api/domanda")
    async def chiedi(request: Request, response: Response):
        s, corpo = sessione(request, response), await request.json()
        if s["tabella"] is None:
            return errore("nessun_file")
        testo, lingua = str(corpo.get("testo", ""))[:500], _lingua(corpo)
        limite = tetto(request)
        if limite:
            return errore(limite, {"tetti": list(tetti)}, 429)
        try:
            r = domanda.rispondi(s["tabella"], testo, ia, s["categorie"], s["precedente"], lingua)
        except OSError:                                 # rete giù o limite gratuito di Groq esaurito
            return errore("ia_non_disponibile", codice=503)
        if r["richiesta"]:
            s["precedente"] = r["richiesta"]
        return r

    @app.post("/api/anno")
    async def anno(request: Request, response: Response):
        """F6: la scelta "2025 o 2026?" completa la richiesta precedente, senza richiamare l'IA."""
        s, corpo = sessione(request, response), await request.json()
        if s["tabella"] is None or not s["precedente"]:
            return errore("nessun_file")
        dati = {**s["precedente"], "periodo": {**(s["precedente"].get("periodo") or {}), "anno": int(corpo["anno"])}}
        ric = valida(dati, s["tabella"])
        r = risposta.componi(ric, calcolo.esegui(s["tabella"], ric, s["categorie"]), s["tabella"], _lingua(corpo))
        s["precedente"] = ric.model_dump(exclude_none=True)
        return r | {"esito": "ok", "richiesta": s["precedente"]}

    @app.post("/api/nuova")
    def nuova(request: Request, response: Response):
        sessione(request, response)["precedente"] = None
        return {"ok": True}

    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app


def _lingua(corpo):
    return "en" if corpo.get("lingua") == "en" else "it"
