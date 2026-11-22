"""Descrizioni → categoria, certa o incerta, chiedendolo all'IA una volta per file. SPEC F7, C7.
L'IA vede solo le descrizioni diverse, senza cifre (F9). Le categorie sono un elenco fisso, con il nome IT/EN."""
import json

import re


def senza_cifre(testo):  # come privacy.senza_cifre (qui per non importare privacy, che importa questo file)
    return re.sub(r"\d", "#", str(testo))

CATEGORIE = {
    "bollette": ("bollette", "bills"), "spesa": ("spesa", "groceries"), "acquisti_online": ("acquisti online", "online shopping"),
    "ristoranti_bar": ("ristoranti e bar", "restaurants and bars"), "trasporti": ("trasporti", "transport"),
    "casa": ("casa e affitto", "home and rent"), "salute": ("salute", "health"), "svago": ("svago", "leisure"),
    "tasse": ("tasse", "taxes"), "stipendio": ("stipendio", "salary"), "bonifici": ("bonifici", "transfers"),
    "altro": ("altro", "other"),
}
SISTEMA = ("Classifichi movimenti bancari italiani. Per ogni descrizione rispondi con una categoria di questo elenco: "
           + ", ".join(CATEGORIE) + ". Metti certa=false se non sei sicuro (es. AMAZON potrebbe essere molte cose). "
           'Rispondi SOLO con un oggetto JSON: {"descrizione": {"categoria": "...", "certa": true}}.')


def nome(chiave, lingua):
    """Il nome da mostrare: 'bollette' → 'bills' in inglese."""
    return CATEGORIE.get(chiave, (chiave, chiave))[0 if lingua == "it" else 1]


def classifica(descrizioni, ia) -> dict:
    """{descrizione originale: (categoria, certa)}. Ciò che l'IA sbaglia o non dice diventa ('altro', incerta)."""
    originali = list(dict.fromkeys(str(d) for d in descrizioni))
    mascherate = {o: senza_cifre(o) for o in originali}
    elenco = sorted(set(mascherate.values()))
    try:
        risposta = json.loads(ia.chiedi(SISTEMA, "CATEGORIE:\n" + "\n".join(elenco)))
    except (ValueError, TypeError):
        risposta = {}
    risposta = risposta if isinstance(risposta, dict) else {}

    def voce(m):
        v = risposta.get(m)
        if not isinstance(v, dict) or v.get("categoria") not in CATEGORIE:
            return ("altro", False)
        return (v["categoria"], v.get("certa") is True)
    return {o: voce(mascherate[o]) for o in originali}
