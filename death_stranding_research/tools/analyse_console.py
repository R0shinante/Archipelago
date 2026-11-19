#!/usr/bin/env python3
"""Analyse une console du client Death Stranding lancee avec `/ds_counters watch on` (lecture seule, hors apworld).

Usage : python3 analyse_console.py console1.txt [console2.txt ...] [--window 10]

Pour chaque hausse du compteur `total` (fin de commande, livraison de bot, marchandise perdue...), affiche tout ce qui change dans la fenetre voulue
(par defaut 10 s) : cles creees, sauts, drapeaux, likes, puis les titres detectes en memoire et les paliers de bot / de likes / standard.
Avec plusieurs consoles, termine par les cles qui accompagnent TOUTES les hausses d'une meme categorie (empreinte commune, a confirmer a la main).
"""
import re, sys, collections

HDR = re.compile(r"\[(\d\d):(\d\d):(\d\d)\] (\d+) compteur")
CHG = re.compile(r"^\S+:Client:\s{2}([0-9a-f]{32}) : (absent|\-?\d+) -> (disparu|\-?\d+)(?: \(([+-]\d+)\))?(?:\s+\[(\w+)\])?")
EVT = re.compile(r"^\S+:Client:(Commande terminee detectee.*|Palier .*|Check retenu.*|Check libere.*|Livraison de bot.*)$")
TOTAL = "27c0565a443d4b649320c5fa189789f5"


def parse(path):
    events, notes, cur, t = [], [], None, 0
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.rstrip("\n")
        m = HDR.search(line)
        if m:
            t = int(m[1]) * 3600 + int(m[2]) * 60 + int(m[3])
            cur = {"t": t, "changes": []}
            events.append(cur)
            continue
        m = CHG.match(line)
        if m and cur is not None:
            a = None if m[2] == "absent" else int(m[2])
            b = None if m[3] == "disparu" else int(m[3])
            cur["changes"].append((m[1], a, b, m[5]))
            continue
        cur = None if not line.startswith(("INFO:Client:  ",)) else cur
        m = EVT.match(line)
        if m:
            notes.append((t, m[1]))          # heure du dernier releve vu : approximative
    return events, notes


def fmt(t):
    return f"{t // 3600:02d}:{t % 3600 // 60:02d}:{t % 60:02d}"


def describe(c):
    k, a, b, name = c
    if a is None:
        what = f"cree -> {b}"
    elif b is None:
        what = "disparu"
    else:
        what = f"{a} -> {b} ({b - a:+d})"
    return f"{k[:8]}… {what}" + (f" [{name}]" if name else "")


def main(argv):
    window = 10
    if "--window" in argv:
        i = argv.index("--window"); window = int(argv[i + 1]); del argv[i:i + 2]
    files = argv[1:]
    if not files:
        print(__doc__); return 1
    per_file = []
    for f in files:
        events, notes = parse(f)
        print(f"=== {f} : {len(events)} releves, {len(notes)} evenements du client")
        rises = []
        for i, e in enumerate(events):
            up = [c for c in e["changes"] if c[0] == TOTAL and c[1] is not None and c[2] is not None and c[2] > c[1]]
            if not up:
                continue
            near = [c for ev in events if abs(ev["t"] - e["t"]) <= window for c in ev["changes"] if c[0] != TOTAL]
            rises.append((e["t"], up[0], near))
            print(f"\n[{fmt(e['t'])}] total {up[0][1]} -> {up[0][2]}")
            created = [c for c in near if c[1] is None]
            others = [c for c in near if c[1] is not None]
            print("  cles creees :", ", ".join(describe(c) for c in created) or "aucune")
            print("  autres      :", ", ".join(describe(c) for c in others) or "aucun")
        per_file.append(rises)
        print("\n-- evenements du client (heure = dernier releve vu) --")
        for t, n in notes:
            print(f"  ~{fmt(t)} {n[:150]}")
    if len(per_file) > 1:
        total_rises = [r for f in per_file for r in f]
        cnt = collections.Counter(c[0] for _, _, near in total_rises for c in {c[0]: c for c in near}.values())
        print(f"\n=== cles presentes dans la fenetre de plusieurs hausses du total (sur {len(total_rises)}) ===")
        for k, n in cnt.most_common(15):
            print(f"  {k[:8]}… : {n} hausse(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
