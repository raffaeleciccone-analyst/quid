"""Cosa può uscire verso l'IA: testi senza cifre. SPEC F9 ("mai importi, date, IBAN, numeri di carta").
La fase 4 aggiunge qui il messaggio completo per la domanda; per ora le categorie."""
import re


def senza_cifre(testo: str) -> str:
    """'PAGAMENTO CARTA 4532 **** 1234' → 'PAGAMENTO CARTA #### **** ####'. Ogni cifra diventa #."""
    return re.sub(r"\d", "#", str(testo))
