#!/usr/bin/env python3
"""Releve, pour CHAQUE sauvegarde (checkpoint.dat) d'un dossier, le titre et toute la table de compteurs nommes du jeu.

Hors ligne, en lecture seule : les checkpoints sont copies dans un dossier temporaire, dechiffres avec l'outil
DeathStrandingSaveDataResigner (version en ligne de commande, deja utilise par /ds_resigner), decompresses (Oodle Kraken, pip install pyooz) ;
vos fichiers ne sont jamais modifies. Aucun identifiant Steam ni chemin n'est ecrit dans les resultats.

Usage (PowerShell) :
    pip install pyooz
    python scan_saves.py --exe C:\\Games\\death-stranding-savedata-resigner-cli.exe --root "C:\\Users\\<vous>\\AppData\\Local\\KojimaProductions\\DeathStrandingDC\\<id steam>" --out releves_saves [--userid <id steam>]
  (--root peut etre omis si le dossier le plus recent de %LOCALAPPDATA%\\KojimaProductions\\DeathStrandingDC convient ; ajoutez --root plusieurs fois pour plusieurs dossiers)
Resultat : un fichier JSON par sauvegarde + resume.csv (a envoyer, c'est petit).
"""
import argparse, csv, json, os, re, shutil, struct, subprocess, sys, tempfile, time, typing, unicodedata
from pathlib import Path
from urllib.parse import unquote
from datetime import datetime

USERID = None      # renseigne par --userid

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
            root = tmp / (USERID or src.parent.parent.name)          # l'outil deduit l'identifiant Steam du nom du dossier : --userid permet de le forcer
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




def autodetect_roots():
    base = os.environ.get("LOCALAPPDATA")
    if not base:
        return []
    parent = Path(base) / "KojimaProductions" / "DeathStrandingDC"
    if not parent.is_dir():
        return []
    return sorted((d for d in parent.iterdir() if d.is_dir() and any(d.glob("*/checkpoint.dat"))), key=lambda d: max(f.stat().st_mtime for f in d.glob("*/checkpoint.dat")), reverse=True)[:1]


def decompress_section3(data: bytes) -> bytes:
    """Section 3 d'un checkpoint dechiffre : flux Oodle Kraken en blocs de 256 Kio (methode de tools/save_counters.py)."""
    import ooz
    n1, n2, n3 = [int(data[i:i + 8].split(b"\0")[0]) for i in (0, 8, 16)]
    s3 = data[24 + n1 + n2:]
    ln = int.from_bytes(s3[8:12], "little")
    comp = s3[12 + ln:]
    p = 0
    n = 0
    while p < len(comp) and (comp[p] & 0xF) == 0xC:
        ck = comp[p + 1] >> 7
        v = (comp[p + 2] << 16) | (comp[p + 3] << 8) | comp[p + 4]
        sz = v & 0x3FFFF
        p = p + 6 if sz == 0x3FFFF else p + 2 + (6 if ck else 3) + sz + 1
        n += 1
    return ooz.decompress(comp[:p], n * 262144)


# Les cles de la table sont toutes des UUID (version 3 ou 4, variante RFC) ; enregistrements de 20 octets : cle (16) + valeur int32.
def _key_ok(raw: bytes, o: int) -> bool:
    return o >= 0 and o + 20 <= len(raw) and (raw[o + 6] >> 4) in (3, 4) and (raw[o + 8] >> 6) == 2 and any(raw[o:o + 16])


SEEDS = [bytes.fromhex(k) for k in (
    "02738f312da146bfaf6d91b7c20fb3a7", "6e843d6f88684d8783ee69b59e7acea4", "8da0f66b48ae475691e01b504c6492fa", "55a57fecddfb4eb18c6f2f279cf5bc74",
    "c580f8515a614102a48057932b0a8ad4", "9ee4840710a64876bb96c59f5920df0b", "f56d051070b541a7a0d1d19c6561c98d")]


def find_table(raw: bytes) -> typing.Dict[str, int]:
    """Table de compteurs nommes : on part d'une cle connue et on etend par pas de 20 octets tant que l'enregistrement a une cle d'UUID."""
    best: typing.Dict[str, int] = {}
    starts = []
    for s in SEEDS:
        p = raw.find(s)
        while p >= 0:
            starts.append(p)
            p = raw.find(s, p + 1)
    if not starts:      # repli : plus longue suite d'enregistrements valides
        pat = re.compile(rb".{6}[\x30-\x3f\x40-\x4f].[\x80-\xbf]", re.S)
        starts = [m.start() for m in pat.finditer(raw)][:200000]
    for p in starts:
        lo = p
        while _key_ok(raw, lo - 20):
            lo -= 20
        hi = p
        while _key_ok(raw, hi + 20):
            hi += 20
        n = (hi - lo) // 20 + 1
        if n > len(best) and n >= 6:
            best = {raw[o:o + 16].hex(): struct.unpack_from("<i", raw, o + 16)[0] for o in range(lo, hi + 1, 20)}
    return best


def main() -> int:
    print("scan_saves.py : demarrage (Python " + sys.version.split()[0] + ")", flush=True)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", required=True, help="outil DeathStrandingSaveDataResigner en ligne de commande")
    ap.add_argument("--root", action="append", help="dossier des sauvegardes (celui qui contient les sous-dossiers checkpoint...)")
    ap.add_argument("--out", default="releves_saves")
    ap.add_argument("--userid", help="identifiant Steam (nom du dossier numerique) avec lequel les sauvegardes ont ete creees ; utile si le dossier a ete renomme ou copie")
    a = ap.parse_args()
    global USERID
    USERID = a.userid
    raw_roots = a.root or []
    for r in raw_roots:
        if '" --' in r or " --" in r:
            print("ATTENTION : l'argument --root contient la suite de la commande (" + r[:60] + "...). Sous Windows, un antislash juste avant le guillemet fermant "
                  "(\"dossier\\\") 'mange' le guillemet : retirez l'antislash final.")
    roots = [Path(r.strip().strip('"')) for r in raw_roots] or autodetect_roots()
    for r in roots:
        n = len(list(r.glob("*/checkpoint.dat"))) if r.is_dir() else -1
        print(f"Dossier des sauvegardes : {r} -> " + ("INTROUVABLE" if n < 0 else f"{n} checkpoint(s) trouve(s) (attendu : des sous-dossiers autosave*/manualsave*/quicksave* contenant checkpoint.dat)"), flush=True)
    if not roots:
        print("Dossier des sauvegardes introuvable : utilisez --root")
        return 2
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dec = ResignerCli(a.exe)
    rows = []
    idx = 0
    for root in roots:
        for f in sorted(root.glob("*/checkpoint.dat"), key=lambda p: p.stat().st_mtime):
            idx += 1
            tag = f"save{idx:03d}"
            data = dec.decrypt(f)
            if data is None:
                print(tag, "ECHEC du dechiffrement :", " / ".join(dec.log[-3:]), flush=True)
                continue
            hdr = read_header(data) or {}
            title = hdr.get("Title", "")
            pt = parse_title(title)
            try:
                table = find_table(decompress_section3(data))
            except Exception as e:      # noqa
                print(tag, "ECHEC de la decompression :", e)
                continue
            mt = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            rec = {"id": tag, "modifie": mt, "titre": title, "commande": pt[1] if pt else None, "terminee": pt[0] if pt else None, "compteurs": table}
            (out / f"{tag}.json").write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")
            rows.append([tag, mt, title, rec["commande"], rec["terminee"], len(table), "total" if any(k.startswith("27c0565a") for k in table) else ""])
            print(tag, mt, "|", title, "|", len(table), "compteurs", flush=True)
    with open(out / "resume.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["id", "modifie", "titre", "commande", "terminee", "nb_compteurs", "total_present"])
        w.writerows(rows)
    print(f"\n{len(rows)} sauvegarde(s) relevee(s) dans {out.resolve()} : envoyez ce dossier (zip).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
