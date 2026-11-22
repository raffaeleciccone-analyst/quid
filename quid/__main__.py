"""Avvio: `python -m quid` (sul PC, IA locale) oppure QUID_MODO=online con la chiave di Groq. Apre il browser."""
import os
import threading
import webbrowser

import uvicorn

from .app import crea_app

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", "8793"))
    os.environ.setdefault("QUID_MODO", "pc")
    if os.environ.get("QUID_APRI", "1") == "1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://127.0.0.1:{porta}")).start()
    uvicorn.run(crea_app(), host=os.environ.get("HOST", "127.0.0.1"), port=porta, log_level="warning")
