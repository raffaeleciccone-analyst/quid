"""Due fornitori di IA, ognuno nel suo formato (SPEC, Cosa NON fa: "Groq più l'IA locale").
Entrambi hanno lo stesso metodo: chiedi(sistema, utente) → testo (JSON). Nessuna libreria in più: urllib."""
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path


def _post(url, corpo, intestazioni, attesa):
    req = urllib.request.Request(url, json.dumps(corpo).encode(), {"content-type": "application/json",
                                                                   "user-agent": "nlda/1.0", **intestazioni})
    with urllib.request.urlopen(req, timeout=attesa) as r:
        return json.loads(r.read())


class Groq:
    """Online. Formato Chat Completions di Groq, risposta forzata in JSON."""
    esce_dal_pc = True
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, chiave=None, modello=None):
        file = os.environ.get("NLDA_CHIAVE_FILE")
        self.chiave = chiave or os.environ.get("GROQ_API_KEY") or (Path(file).read_text().strip() if file else None)
        self.modello = modello or os.environ.get("NLDA_MODELLO", "openai/gpt-oss-120b")

    def chiedi(self, sistema, utente):
        corpo = {"model": self.modello, "temperature": 0, "response_format": {"type": "json_object"},
                 "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": utente}]}
        for tentativo in range(4):
            try:
                r = _post(self.URL, corpo, {"authorization": f"Bearer {self.chiave}"}, 60)
                return r["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as e:     # 429: il piano gratuito ha un tetto al minuto, si aspetta e si riprova
                if e.code != 429 or tentativo == 3:
                    raise
                time.sleep(min(float(e.headers.get("retry-after") or 5), 30))


class Ollama:
    """Sul PC: niente esce dal computer (C10). Formato /api/chat di Ollama, format json."""
    esce_dal_pc = False

    def __init__(self, modello=None, url=None):
        self.modello = modello or os.environ.get("NLDA_MODELLO", "qwen2.5:3b")
        self.url = url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

    def chiedi(self, sistema, utente):
        r = _post(self.url + "/api/chat", {"model": self.modello, "stream": False, "format": "json",
                                           "options": {"temperature": 0, "num_ctx": 8192},
                                           "messages": [{"role": "system", "content": sistema},
                                                        {"role": "user", "content": utente}]}, {}, 300)
        return r["message"]["content"]
