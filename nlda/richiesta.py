"""La richiesta: l'unica cosa che l'IA può restituire (PIANO §2, porta n.2). Si accetta solo se rispetta lo schema.
L'IA non scrive codice: qui non c'è niente da eseguire, solo campi da controllare. SPEC C20, C5."""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

PERICOLOSO = re.compile(r"__|\bopen\s*\(|\bimport\b|\beval\b|\bexec\b|\.to_\w+|\bos\.|subprocess")


class RichiestaRifiutata(Exception):
    def __init__(self, chiave):
        super().__init__(chiave)
        self.chiave = chiave


class Rigido(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Filtro(Rigido):
    colonna: str
    uguale: str

    @field_validator("colonna", "uguale")
    @classmethod
    def _sicuro(cls, v):
        if PERICOLOSO.search(v):
            raise ValueError("sicurezza")
        return v


class Periodo(Rigido):
    mese: int | None = Field(None, ge=1, le=12)
    anno: int | None = Field(None, ge=1900, le=2100)


class Richiesta(Rigido):
    tipo: Literal["calcolo", "assente", "non_capito"]
    operazione: Literal["somma", "conteggio", "media", "massimo", "minimo", "elenco"] | None = None
    misura: str | None = None
    filtri: list[Filtro] = []
    periodo: Periodo | None = None
    raggruppa: str | None = None
    segno: Literal["uscite", "entrate", "tutti"] | None = None
    cosa: str | None = Field(None, max_length=60)


def valida(r, tabella) -> Richiesta:
    """dict o testo JSON → Richiesta, oppure RichiestaRifiutata. Le colonne devono esistere nella tabella (C5)."""
    try:
        ric = Richiesta.model_validate(json.loads(r) if isinstance(r, str) else r)
    except (ValidationError, ValueError, TypeError) as e:
        raise RichiestaRifiutata("sicurezza" if "sicurezza" in str(e) else "schema") from None
    if ric.cosa and PERICOLOSO.search(ric.cosa):
        raise RichiestaRifiutata("sicurezza")
    colonne = set(tabella.df.columns) | {"categoria"}
    nomi = [ric.misura, ric.raggruppa] + [f.colonna for f in ric.filtri]
    if ric.tipo == "calcolo":
        if ric.operazione is None:
            raise RichiestaRifiutata("schema")
        for n in nomi:
            if n is not None and n not in colonne | {"mese"}:
                raise RichiestaRifiutata("sicurezza" if PERICOLOSO.search(n) else "colonna")
    return ric
