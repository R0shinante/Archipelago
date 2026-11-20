"""Surveillance des sauvegardes de Death Stranding : detecte les commandes terminees.

Principe
--------
A chaque checkpoint, le jeu ecrit un fichier checkpoint.dat chiffre. Une fois dechiffre, son en-tete texte contient
un titre de la forme :   Commande terminee : n° 59 « Livraison de bombe antimatiere : Paleontologue » - 18:48:18
On copie le fichier dans un dossier temporaire, on le dechiffre avec l'outil en ligne de commande
DeathStrandingSaveDataResigner (option -m d), puis on lit ce titre. Le numero est celui de la commande du jeu.

Ce module ne depend pas d'Archipelago : il est testable seul.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
import typing
import unicodedata
from pathlib import Path
from urllib.parse import unquote

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


def read_header(data: bytes) -> typing.Optional[typing.Dict[str, str]]:
    """Lit l'en-tete texte d'une sauvegarde DECHIFFREE. Renvoie None si ce n'en est pas une.

    Format : 3 champs de 8 octets (tailles ASCII), puis 3 sections ; la 1re est un texte « [Slot] Cle = valeur ».
    """
    try:
        sizes = [int(data[i:i + 8].split(b"\0")[0]) for i in (0, 8, 16)]
    except ValueError:
        return None
    if min(sizes) < 0 or 24 + sum(sizes) != len(data):
        return None
    text = unquote(data[24:24 + sizes[0]].decode("utf-8", "replace")).replace("\r", "")
    fields: typing.Dict[str, str] = {}
    cur: typing.Optional[str] = None
    for line in text.split("\n"):
        if "=" in line and not line.startswith(" "):
            key, value = line.split("=", 1)
            cur = key.strip()
            fields[cur] = " ".join(value.split())
        elif line.strip() and cur:
            fields[cur] += " | " + line.strip()
    return fields if "Title" in fields else None


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


class ResignerCli:
    """Dechiffre un checkpoint.dat avec l'outil en ligne de commande (copie temporaire : l'original n'est jamais touche)."""

    def __init__(self, exe: typing.Union[str, os.PathLike]):
        self.exe = Path(exe)
        self.log: typing.List[str] = []

    def decrypt(self, src: Path) -> typing.Optional[bytes]:
        self.log = []
        if not self.exe.is_file():
            self.log.append(f"outil introuvable : {self.exe}")
            return None
        tmp = Path(tempfile.mkdtemp(prefix="dsap_"))
        try:
            root = tmp / src.parent.parent.name          # l'outil peut deduire l'identifiant du nom du dossier
            slot = root / src.parent.name
            slot.mkdir(parents=True)
            shutil.copy2(src, slot / src.name)
            started = time.time() - 1.0
            cmd = [str(self.exe), "-m", "d", "-p", str(root)]
            kw: typing.Dict[str, typing.Any] = {}
            if os.name == "nt":
                kw["creationflags"] = 0x08000000        # CREATE_NO_WINDOW
            res = subprocess.run(cmd, cwd=str(self.exe.parent), capture_output=True, text=True,
                                 timeout=60, stdin=subprocess.DEVNULL, **kw)
            self.log.append(f"commande : {' '.join(cmd)}")
            self.log.append(f"code retour : {res.returncode}")
            tail = (res.stdout + res.stderr).strip()
            found = self._find_output(tmp, started)
            if found is None:
                if tail:
                    self.log.append("sortie : " + tail[-300:].replace("\n", " / "))
                self.log.append("aucun fichier dechiffre trouve (cherche dans _OUTPUT a cote de l'outil, dans le dossier courant "
                                "et dans le dossier temporaire)")
                return None
            path, data = found
            self.log.append(f"fichier dechiffre : {path}")
            try:
                if not path.is_relative_to(tmp):
                    path.unlink()                        # on ne supprime que le fichier produit par cet appel
                    for parent in path.parents:          # puis les dossiers devenus vides, jusqu'a _OUTPUT
                        if parent.name == "_OUTPUT":
                            break
                        parent.rmdir()
            except OSError:
                pass                                     # dossier non vide : on le laisse
            return data
        except (OSError, subprocess.SubprocessError) as e:
            self.log.append(f"erreur : {e}")
            return None
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _find_output(self, tmp: Path, started: float) -> typing.Optional[typing.Tuple[Path, bytes]]:
        roots: typing.List[Path] = [tmp]
        for base in (self.exe.parent, Path.cwd()):
            out = base / "_OUTPUT"
            if out.is_dir() and out not in roots:
                roots.append(out)
        best: typing.Optional[typing.Tuple[float, Path, bytes]] = None
        for root in roots:
            for p in root.rglob("*"):
                try:
                    if not p.is_file():
                        continue
                    st = p.stat()
                    if st.st_mtime < started or st.st_size < 100:
                        continue
                    data = p.read_bytes()
                except OSError:
                    continue
                if read_header(data) is not None and (best is None or st.st_mtime > best[0]):
                    best = (st.st_mtime, p, data)
        return (best[1], best[2]) if best else None


def autodetect_root() -> typing.Optional[Path]:
    """Dossier des sauvegardes de la version Director's Cut (le plus recemment modifie)."""
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return None
    parent = Path(base) / "KojimaProductions" / "DeathStrandingDC"
    if not parent.is_dir():
        return None
    candidates = [d for d in parent.iterdir() if d.is_dir() and any(d.glob("*/checkpoint.dat"))]
    if not candidates:
        return None
    return max(candidates, key=lambda d: max(f.stat().st_mtime for f in d.glob("*/checkpoint.dat")))


class SaveWatcher:
    """Surveille les checkpoint.dat et renvoie les numeros de commandes qui viennent d'etre terminees."""

    SETTLE = 1.0        # on attend 1 s apres la derniere ecriture du fichier
    RETRY = 5.0         # delai avant de reessayer un fichier dont le dechiffrement a echoue

    def __init__(self, root: typing.Optional[typing.Union[str, os.PathLike]], decryptor: typing.Any,
                 words: typing.Iterable[str] = DEFAULT_COMPLETED_WORDS):
        self.root = Path(root) if root else None
        self.decryptor = decryptor            # objet avec .decrypt(Path) -> bytes | None, et .log
        self.words = tuple(words)
        self.completed: typing.Set[int] = set()
        self.last_title = ""
        self.failures = 0
        self._seen: typing.Dict[Path, typing.Tuple[float, int]] = {}
        self._failed_at: typing.Dict[Path, float] = {}
        self._baselined = False

    # -- etat --------------------------------------------------------------
    def files(self) -> typing.List[Path]:
        return sorted(self.root.rglob("checkpoint.dat")) if self.root and self.root.is_dir() else []

    def ready(self) -> bool:
        return bool(self.root and self.root.is_dir() and self.decryptor is not None)

    @staticmethod
    def _stamp(p: Path) -> typing.Tuple[float, int]:
        st = p.stat()
        return (st.st_mtime, st.st_size)

    # -- traitement ---------------------------------------------------------
    def process(self, path: Path) -> typing.Optional[typing.Optional[int]]:
        """Dechiffre + lit le titre. None = echec ; sinon le numero de commande terminee (ou -1 si rien a signaler)."""
        data = self.decryptor.decrypt(path)
        if data is None:
            return None
        header = read_header(data)
        if header is None:
            return None
        self.last_title = header.get("Title", "")
        parsed = parse_title(self.last_title, self.words)
        if parsed and parsed[0]:
            return parsed[1]
        return -1

    def baseline(self) -> None:
        """Memorise l'etat actuel sans rien traiter : seules les modifications futures comptent."""
        for p in self.files():
            try:
                self._seen[p] = self._stamp(p)
            except OSError:
                pass
        self._baselined = True

    def poll(self) -> typing.List[int]:
        """A appeler regulierement. Renvoie les numeros de commandes nouvellement terminees."""
        if not self.ready():
            return []
        if not self._baselined:
            self.baseline()
            return []
        new: typing.List[int] = []
        now = time.time()
        for p in self.files():
            try:
                stamp = self._stamp(p)
            except OSError:
                continue
            if self._seen.get(p) == stamp or now - stamp[0] < self.SETTLE:
                continue
            if now - self._failed_at.get(p, 0.0) < self.RETRY:
                continue
            result = self.process(p)
            if result is None:
                self.failures += 1
                self._failed_at[p] = now
                continue
            self._seen[p] = stamp
            self._failed_at.pop(p, None)
            if result >= 0 and result not in self.completed:
                self.completed.add(result)
                new.append(result)
        return new

    def catch_up(self) -> typing.List[int]:
        """Traite TOUS les checkpoints presents (y compris anciens). Renvoie les commandes terminees trouvees."""
        found: typing.List[int] = []
        for p in self.files():
            result = self.process(p)
            if result is not None and result >= 0 and result not in self.completed:
                self.completed.add(result)
                found.append(result)
            try:
                self._seen[p] = self._stamp(p)
            except OSError:
                pass
        self._baselined = True
        return found
