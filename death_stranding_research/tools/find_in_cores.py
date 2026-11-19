#!/usr/bin/env python3
"""Cherche dans des fichiers du jeu EXTRAITS (par exemple des .core exportes avec Decima Workshop ou Decima-Explorer) :
  - des cles de compteurs (GUID de 16 octets) : a quels fichiers elles appartiennent, avec les chaines de texte voisines (souvent le nom) ;
  - ou du texte (nom de commande, par exemple) en UTF-8 et en UTF-16.
Lecture seule. Ne touche ni au jeu ni a vos sauvegardes.

Usage :
  python find_in_cores.py <dossier extrait> --counters DeathStranding_counters.json   (fichier ecrit par /ds_counters save)
  python find_in_cores.py <dossier extrait> --keys 9ee4840710a64876bb96c59f5920df0b,26adb4dfac794d7dbc80aa23969c7652
  python find_in_cores.py <dossier extrait> --text "Smart Drug Delivery"
Options : --ext .core,.bin,.json (extensions a lire, defaut : toutes) ; --max-mb 400 (taille maximale par fichier).
Une cle est cherchee dans l'ordre des octets de la memoire du jeu ET dans l'ordre « GUID Microsoft » (3 premiers champs inverses).
Les resultats sont des PISTES a verifier (une meme suite d'octets peut apparaitre par hasard, tres peu probable sur 16 octets).
"""
import argparse, json, os, re, sys


def key_patterns(hexkey: str):
    b = bytes.fromhex(hexkey)
    mixed = b[3::-1] + b[5:3:-1] + b[7:5:-1] + b[8:]
    return {b: "ordre memoire", mixed: "ordre GUID"}


def strings_near(data: bytes, pos: int, span: int = 300, minlen: int = 5):
    lo, hi = max(0, pos - span), min(len(data), pos + 16 + span)
    out = []
    for m in re.finditer(rb"[ -~]{%d,}" % minlen, data[lo:hi]):
        out.append(m.group().decode("ascii"))
    for m in re.finditer(rb"(?:[ -~]\x00){%d,}" % minlen, data[lo:hi]):
        out.append(m.group().decode("utf-16-le", "ignore"))
    return out[:8]


def iter_files(root, exts, max_mb):
    for d, _, fs in os.walk(root):
        for f in fs:
            if exts and os.path.splitext(f)[1].lower() not in exts:
                continue
            p = os.path.join(d, f)
            try:
                if os.path.getsize(p) <= max_mb << 20:
                    yield p
            except OSError:
                pass


def search_keys(root, keys, exts, max_mb):
    pats = {}
    for k in keys:
        for pat, how in key_patterns(k).items():
            pats[pat] = (k, how)
    rx = re.compile(b"|".join(re.escape(p) for p in pats), re.S)
    found = 0
    for p in iter_files(root, exts, max_mb):
        try:
            data = open(p, "rb").read()
        except OSError:
            continue
        for m in rx.finditer(data):
            k, how = pats[m.group()]
            found += 1
            print(f"{k}  {os.path.relpath(p, root)} @ {m.start():#x} ({how})")
            for s in strings_near(data, m.start()):
                print(f"      {s[:100]}")
    print(f"\n{found} occurrence(s).")


def search_text(root, text, exts, max_mb):
    pats = [text.encode("utf-8"), text.encode("utf-16-le")]
    rx = re.compile(b"|".join(re.escape(p) for p in pats), re.S | re.I)
    found = 0
    for p in iter_files(root, exts, max_mb):
        try:
            data = open(p, "rb").read()
        except OSError:
            continue
        for m in rx.finditer(data):
            found += 1
            print(f"{os.path.relpath(p, root)} @ {m.start():#x}")
            for s in strings_near(data, m.start(), span=120):
                print(f"      {s[:100]}")
            if found >= 200:
                print("... (200 premieres occurrences)")
                return
    print(f"\n{found} occurrence(s).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folder")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--counters"); g.add_argument("--keys"); g.add_argument("--text")
    ap.add_argument("--ext", default=""); ap.add_argument("--max-mb", type=int, default=400)
    a = ap.parse_args()
    exts = {e if e.startswith(".") else "." + e for e in a.ext.lower().split(",") if e}
    if not os.path.isdir(a.folder):
        sys.exit(f"Dossier introuvable : {a.folder}")
    if a.text:
        search_text(a.folder, a.text, exts, a.max_mb)
        return
    if a.counters:
        keys = list(json.load(open(a.counters, encoding="utf-8")).get("counters", {}))
    else:
        keys = [k.strip().lower() for k in a.keys.split(",") if k.strip()]
    keys = [k for k in keys if re.fullmatch(r"[0-9a-f]{32}", k)]
    if not keys:
        sys.exit("Aucune cle valide (32 caracteres hexadecimaux).")
    print(f"{len(keys)} cle(s) cherchee(s) dans {a.folder}")
    search_keys(a.folder, keys, exts, a.max_mb)


if __name__ == "__main__":
    main()
