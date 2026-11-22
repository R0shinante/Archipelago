"""Lecture des titres de points de controle de Death Stranding (utilitaires purs, sans dependance a Archipelago).

Le jeu ecrit, a chaque point de controle, un titre de la forme :   Commande terminee : n° 59 « Livraison de bombe antimatiere : Paleontologue » - 18:48:18
Le client le lit directement dans la memoire du jeu ; ce module sait dire si un titre signifie « commande terminee » et de quelle commande il s'agit.
"""
from __future__ import annotations

import re
import typing
import unicodedata

# Mots (sans accents, en minuscules) qui, dans l'etat du titre, signifient « terminee ». Valides en francais seulement ; les autres langues sont des
# suppositions (fragments de « commande terminee » / « order completed »), a confirmer avec /ds_titles. Un fragment suffit.
DEFAULT_COMPLETED_WORDS = (
    "termin",                                   # fr terminee ; it terminato ; tr/sv...
    "complet",                                  # en completed ; es completado ; it completato
    "abgeschlossen",                            # de
    "completad", "conclu", "finaliz",           # es / pt (concluido) / es-pt (finalizado)
    "voltooid", "afgerond",                     # nl
    "ukonczon", "zakonczon", "wykonan",         # pl
    "vypln", "dokonc", "splnen",                # cs
    "tamamland",                                # tr
    "slutfor", "avslutad",                      # sv
    "выполнен", "завершен", "завершён",         # ru
    "完了", "達成", "完成", "已完成",              # ja / zh
    "완료",                                      # ko
)
# Un etat qui contient un de ces fragments n'est PAS une fin de commande (« incomplete », « non terminee »...).
NEGATIVE_WORDS = ("incompl", "inconclu", "unvollst", "non termin", "not complet", "unfinish", "uncomplet", "nicht abgeschlossen", "no complet", "no termin",
                  "niewykon", "nieukoncz", "nedokonc", "незаверш", "невыполн", "未完", "未達", "미완")

# « Commande terminee : nº 59 « nom » - 18:48:18 »  ->  etat, numero, reste. Deux-points pleine chasse et prefixes de numero (n°, nº, no., nr., N.º, №, #) acceptes.
TITLE_RE = re.compile(
    r"^\s*(?P<state>[^:\uff1a]*?)\s*[:\uff1a]\s*(?:n(?:\.?\s?[\u00ba\u00b0]|o|r|um)\.?|\u2116|#)\s*(?P<num>\d{1,4})\b(?P<rest>.*)$", re.IGNORECASE)
QUOTES = " \xa0«»\"\u201c\u201d\u201e\u300c\u300d\u300e\u300f"


def fold(text: str) -> str:
    """Minuscules sans accents."""
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")).casefold()   # NFC : recompose le hangul


def parse_title(title: str, words: typing.Iterable[str] = DEFAULT_COMPLETED_WORDS
                ) -> typing.Optional[typing.Tuple[bool, int, str]]:
    """(terminee ?, numero de commande, nom) ou None si le titre n'est pas de ce type."""
    m = TITLE_RE.match(title)
    if not m:
        return None
    state = fold(m.group("state"))
    completed = any(w in state for w in words) and not any(n in state for n in NEGATIVE_WORDS)
    name = m.group("rest").strip()
    name = re.sub(r"\s*[-\u2013\u2014]\s*\d{1,2}:\d{2}(:\d{2})?\s*$", "", name).strip(QUOTES)
    return completed, int(m.group("num")), name
