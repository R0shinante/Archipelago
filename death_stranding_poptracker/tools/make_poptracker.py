#!/usr/bin/env python3
"""Genere le pack PopTracker du monde Death Stranding (Archipelago) a partir des donnees du monde.

Usage (depuis la racine du depot, avec Archipelago dans le PYTHONPATH) :
    PYTHONPATH=/chemin/vers/Archipelago python3 tools/make_poptracker.py [dossier_de_sortie]
(dans la branche du fork : python3 death_stranding_poptracker/tools/make_poptracker.py)

Le pack est entierement derive de worlds/death_stranding (data.py, items.py, locations.py) : relancer le script apres
tout changement du monde (nouvel objet, nouvelle commande...) regenere items, lieux, carte, images et tables de correspondance
des identifiants. Rien n'est ecrit a la main dans le dossier de sortie, sauf README.md, qui est copie depuis tools/poptracker_README.md.
Pillow est requis pour les images.
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

# Le dossier tools/ contient des scripts dont les noms (headers.py...) peuvent masquer des modules importes par les autres mondes d'Archipelago.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != Path(__file__).resolve().parent]

from PIL import Image, ImageDraw, ImageFont

try:    # evite l'invite interactive « press enter to install » de ModuleUpdate (dependances d'autres mondes d'Archipelago)
    import ModuleUpdate
    ModuleUpdate.update_ran = True
except ImportError:
    pass

from worlds.death_stranding.data import (BASE_ID, EPISODE_TITLES, EPISODES, MAIN_ORDERS, OPTIONAL_ORDERS, USEFUL_ITEMS, FILLER_ITEMS, TRAP_ITEMS,
                                         EXTRA_FILLER_ITEMS, EXTRA_TRAP_ITEMS, EXTRA_FILLER2_ITEMS, EXTRA_FILLER3_ITEMS, EXTRA_FILLER4_ITEMS)
from worlds.death_stranding.items import item_name_to_id
from worlds.death_stranding.locations import (LIKES_BASE_ID, ORDER_PROGRESS_BASE_ID, STANDARD_ORDER_BASE_ID, BOT_ORDER_BASE_ID, MAX_LIKES_CHECKS,
                                              MAX_ORDER_CHECKS, MAX_STANDARD_CHECKS, MAX_BOT_CHECKS, location_table)

PACK_VERSION = "0.1.0"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

# categories -> couleur d'accent
ACCENT = {"episode": "#4f8cff", "equip": "#e0a030", "material": "#2fb59a", "supply": "#8ac24a", "trap": "#e0524a",
          "setting": "#9a6bd6", "milestone": "#35b6d9"}
TILE_BG = "#1c232d"

# (nom, abreviation) ; l'ordre des categories suit items.py
ABBR = {
    "Power Skeleton": "PS", "Speed Skeleton": "SS", "Cargo Skeleton": "CS", "Trike": "Tk", "Truck": "Tr", "Road Paver": "RP",
    "Zipline Anchor Set": "ZA", "Ladder Set": "LS", "Climbing Anchor Set": "CA", "Assault Rifle": "AR", "Hematic Grenade Pack": "HG",
    "Bola Gun": "BG", "Boot Upgrade": "BU",
    "Chiral Crystals": "CC", "Metals": "Me", "Ceramics": "Ce", "Resins": "Re", "Chemicals": "Ch", "Special Alloys": "SA",
    "Blood Bag": "BB", "Energy Drink": "ED", "Repair Spray": "RS", "Cryptobiote Pack": "Cr", "D-Cryptobiote Pack": "Dc",
    "Sandalweed Bundle": "Sw", "Likes Pack": "♥",
    "Injury Trap": "Inj", "Fatigue Trap": "Fat", "Boot Wear Trap": "BW", "Rust Trap": "Rst", "Pickpocket Trap": "Pkp",
}
MATERIALS = ("Chiral Crystals", "Metals", "Ceramics", "Resins", "Chemicals", "Special Alloys")


def slug(name: str) -> str:
    return "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_")


def font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def fit_font(draw: ImageDraw.ImageDraw, text: str, max_w: int, start: int) -> ImageFont.FreeTypeFont:
    size = start
    while size > 8:
        f = font(size)
        if draw.textlength(text, font=f) <= max_w:
            return f
        size -= 1
    return font(8)


def tile(path: Path, text: str, accent: str, sub: str | None = None, size: int = 64) -> None:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((1, 1, size - 2, size - 2), radius=10, fill=TILE_BG, outline=accent, width=3)
    d.rounded_rectangle((8, size - 11, size - 9, size - 7), radius=2, fill=accent)       # barre d'accent
    if sub:
        d.text((size / 2, 12), sub, font=font(11), fill="#9fb0c4", anchor="mm")
        f = fit_font(d, text, size - 14, 30)
        d.text((size / 2, size / 2 + 3), text, font=f, fill="#ffffff", anchor="mm")
    else:
        f = fit_font(d, text, size - 14, 28)
        d.text((size / 2, size / 2 - 2), text, font=f, fill="#ffffff", anchor="mm")
    img.save(path)


def chest_icons(img_dir: Path) -> None:
    for name, col, mark in (("chest_unopened", "#c58b2a", None), ("chest_opened", "#3fae5a", "✓")):
        img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((3, 6, 28, 27), radius=4, fill="#1c232d", outline=col, width=2)
        d.line((3, 14, 28, 14), fill=col, width=2)
        d.line((16, 6, 16, 27), fill=col, width=2)
        if mark:
            d.text((16, 17), mark, font=font(16), fill=col, anchor="mm")
        img.save(img_dir / f"{name}.png")


def build_items(root: Path) -> tuple[list[dict], dict[int, list[str]]]:
    """-> (items.json, ITEM_MAPPING {id: [code, type]})"""
    img_dir = root / "images" / "items"
    img_dir.mkdir(parents=True, exist_ok=True)
    items: list[dict] = []
    mapping: dict[int, list[str]] = {}

    def add_toggle(name: str, code: str, accent: str, text: str, sub: str | None = None) -> None:
        tile(img_dir / f"{code}.png", text, accent, sub)
        items.append({"name": name, "type": "toggle", "img": f"images/items/{code}.png", "codes": code, "disabled_img_mods": "@disabled"})

    def add_counter(name: str, code: str, accent: str, text: str, max_q: int) -> None:
        tile(img_dir / f"{code}.png", text, accent)
        items.append({"name": name, "type": "consumable", "img": f"images/items/{code}.png", "codes": code, "min_quantity": 0, "max_quantity": max_q,
                      "increment": 1, "decrement": 1, "initial_quantity": 0, "overlay_font_size": 12, "disabled_img_mods": "@disabled"})

    # 1. acces d'episode (progression)
    for ep in sorted(EPISODES):
        if ep == 0:
            continue
        name = f"Episode {ep} Access"
        code = f"ep{ep}"
        add_toggle(f"{name} ({EPISODE_TITLES[ep].split(' - ', 1)[1]})", code, ACCENT["episode"], str(ep), "EP")
        mapping[item_name_to_id[name]] = [code, "toggle"]

    # 2. equipement (utile)
    for name, qty in USEFUL_ITEMS.items():
        code = slug(name)
        if qty == 1:
            add_toggle(name, code, ACCENT["equip"], ABBR[name])
            mapping[item_name_to_id[name]] = [code, "toggle"]
        else:
            add_counter(f"{name} (x{qty} in the pool)", code, ACCENT["equip"], ABBR[name], qty)
            mapping[item_name_to_id[name]] = [code, "consumable"]

    # 3. materiaux et fournitures (remplissage, comptes illimites)
    fillers = [*FILLER_ITEMS, *EXTRA_FILLER_ITEMS, *EXTRA_FILLER2_ITEMS, *EXTRA_FILLER3_ITEMS, *EXTRA_FILLER4_ITEMS]
    for name in fillers:
        code = slug(name)
        add_counter(name, code, ACCENT["material"] if name in MATERIALS else ACCENT["supply"], ABBR[name], 999)
        mapping[item_name_to_id[name]] = [code, "consumable"]

    # 4. pieges
    for name in [*TRAP_ITEMS, *EXTRA_TRAP_ITEMS]:
        code = slug(name)
        add_counter(name, code, ACCENT["trap"], ABBR[name], 999)
        mapping[item_name_to_id[name]] = [code, "consumable"]

    # 5. reglages / compteurs (pilotes par le script d'autotracking ou a la main)
    tile(img_dir / "goal14.png", "14", ACCENT["setting"], "GOAL")
    tile(img_dir / "goal12.png", "12", ACCENT["setting"], "GOAL")
    items.append({"name": "Goal", "type": "progressive", "allow_disabled": False, "loop": True, "initial_stage_idx": 0, "stages": [
        {"name": "Goal: finish Episode 14", "img": "images/items/goal14.png", "codes": "goal14"},
        {"name": "Goal: finish Episode 12", "img": "images/items/goal12.png", "codes": "goal12", "inherit_codes": False}]})
    tile(img_dir / "freemode.png", "ALL", ACCENT["setting"], "FREE")
    items.append({"name": "Free mode: show every order as reachable (the game is never locked)", "type": "toggle", "img": "images/items/freemode.png",
                  "codes": "freemode", "disabled_img_mods": "@disabled"})
    for code, name, text, sub in (("ms_main", "Main orders checked", "70", "ORD"), ("ms_likes", "Likes milestones", "♥", "MILE"),
                                  ("ms_order", "Order progress milestones", "OP", "MILE"), ("ms_standard", "Standard order milestones", "SO", "MILE"),
                                  ("ms_bot", "Bot order milestones", "BO", "MILE")):
        tile(img_dir / f"{code}.png", text, ACCENT["milestone"], sub)
        items.append({"name": name, "type": "toggle", "img": f"images/items/{code}.png", "codes": code, "disabled_img_mods": "@disabled",
                      "initial_active_state": code == "ms_main"})
    tile(img_dir / "resync.png", "\u21ba", ACCENT["setting"], "SYNC")      # bouton Lua (scripts/init.lua) : annule les cases cochees a la main
    return items, mapping


def order_label(no: int) -> str:
    return f"{no}*" if no in OPTIONAL_ORDERS else str(no)


def clean(name: str) -> str:
    return name.replace(":", " -")


def build_map(root: Path) -> dict[str, tuple[int, int]]:
    """Dessine la 'carte' (grille de commandes par episode) ; renvoie {cle: (x, y)} pour chaque case (centre du carre)."""
    CELL_W, CELL_H, HEAD_H, GAP, MARGIN, MAXC = 58, 72, 26, 18, 14, 14
    SQUARE_Y = 24         # centre du carre a partir du haut de la case
    # blocs : (titre, [(cle, etiquette, optionnel)])
    blocks: list[tuple[str, list[tuple[str, str, bool]]]] = []
    for ep in sorted(EPISODES):
        title = EPISODE_TITLES[ep].replace(" - ", " · ")
        cells = [(f"o{no}", order_label(no), no in OPTIONAL_ORDERS) for no, _, e in sorted(MAIN_ORDERS) if e == ep]
        blocks.append((title, cells))
    blocks.append(("Goal", [("victory", "★", False)]))
    # decoupe les blocs trop larges en lignes equilibrees
    units: list[tuple[str, list[list[tuple[str, str, bool]]]]] = []
    for title, cells in blocks:
        lines = math.ceil(len(cells) / MAXC)
        per = math.ceil(len(cells) / lines)
        units.append((title, [cells[i:i + per] for i in range(0, len(cells), per)]))
    # rangement glouton, de gauche a droite, dans des rangees de MAXC colonnes (largeurs en pixels : un bloc est au moins aussi large que son titre)
    measure = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    maxw = MAXC * CELL_W

    def unit_w(u) -> int:
        return max(max(len(line) for line in u[1]) * CELL_W, int(measure.textlength(u[0], font=font(14))) + 8)

    rows: list[list[tuple[str, list[list[tuple[str, str, bool]]]]]] = [[]]
    used = 0
    for u in units:
        w = unit_w(u)
        if rows[-1] and used + w > maxw:
            rows.append([])
            used = 0
        rows[-1].append(u)
        used += w + GAP
    width = MARGIN * 2 + maxw
    height = MARGIN * 2 + sum(HEAD_H + max(len(u[1]) for u in r) * CELL_H + 10 for r in rows) + 26
    img = Image.new("RGB", (width, height), "#0f1319")
    d = ImageDraw.Draw(img)
    pos: dict[str, tuple[int, int]] = {}
    y = MARGIN
    for r in rows:
        x = MARGIN
        for title, lines in r:
            d.text((x + 2, y + HEAD_H - 8), title, font=font(14), fill="#9fb0c4", anchor="ls")
            for li, line in enumerate(lines):
                for ci, (key, label, opt) in enumerate(line):
                    cx0, cy0 = x + ci * CELL_W, y + HEAD_H + li * CELL_H
                    d.rounded_rectangle((cx0 + 2, cy0, cx0 + CELL_W - 3, cy0 + CELL_H - 6), radius=7, fill="#171d26", outline="#232c38")
                    d.text((cx0 + CELL_W / 2, cy0 + 56), label, font=font(14), fill="#f0b24a" if opt else "#d5deea", anchor="mm")
                    pos[key] = (int(cx0 + CELL_W / 2), int(cy0 + SQUARE_Y))
            x += unit_w((title, lines)) + GAP
        y += HEAD_H + max(len(u[1]) for u in r) * CELL_H + 10
    d.text((MARGIN + 2, height - MARGIN - 4), "* = optional order (never holds a progression item)   ★ = victory   right click: mark checked / unchecked by hand",
           font=font(12, False), fill="#7f8fa3", anchor="ls")
    (root / "images" / "maps").mkdir(parents=True, exist_ok=True)
    img.save(root / "images" / "maps" / "orders.png")
    return pos


def lua_str(s: str) -> str:
    assert s.isascii() and "\\" not in s and '"' not in s, s
    return f'"{s}"'


def main() -> None:
    here = Path(__file__).resolve().parent
    # depot autonome : <racine>/tools + <racine>/poptracker ; branche du fork : death_stranding_poptracker/tools + death_stranding_poptracker/pack
    default = here.parent / ("pack" if (here.parent / "pack").is_dir() else "poptracker")
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    if out.exists():
        shutil.rmtree(out)
    (out / "images").mkdir(parents=True)
    (out / "scripts").mkdir()
    (out / "items").mkdir()
    (out / "locations").mkdir()
    (out / "maps").mkdir()
    (out / "layouts").mkdir()

    items, item_map = build_items(out)
    chest_icons(out / "images")
    pos = build_map(out)

    # --- manifest
    (out / "manifest.json").write_text(json.dumps({
        "name": "Death Stranding (Archipelago)", "game_name": "Death Stranding", "package_uid": "death_stranding_archipelago_tracker",
        "package_version": PACK_VERSION, "platform": "pc", "author": "Roshinante", "min_poptracker_version": "0.26.0",
        "variants": {"orders_map": {"display_name": "Orders map", "flags": ["ap"]}}}, indent=2), encoding="utf-8")

    # --- items
    (out / "items" / "items.json").write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- lieux
    all_eps = " ".join(f"ep{i}" for i in range(1, 15))

    def ep_rule(ep: int) -> str:
        return ",".join(f"ep{i}" for i in range(1, ep + 1))

    locations = []
    loc_map: dict[int, str] = {}
    for no, name, ep in sorted(MAIN_ORDERS):
        loc_name = f"Order {no} - {clean(name)}"
        opt = no in OPTIONAL_ORDERS
        sec = "Order check (optional)" if opt else "Order check"
        loc = {"name": loc_name, "short_name": f"Order {no}", "chest_unopened_img": "images/chest_unopened.png", "chest_opened_img": "images/chest_opened.png",
               "map_locations": [{"map": "orders", "x": pos[f"o{no}"][0], "y": pos[f"o{no}"][1]}], "sections": [{"name": sec, "item_count": 1}]}
        if ep > 0:
            loc["access_rules"] = ["freemode", ep_rule(ep)]
        locations.append(loc)
        loc_map[BASE_ID + no] = f"@{loc_name}/{sec}"
    last_ep = max(EPISODES)
    locations.append({"name": "Victory (finish the goal episode)", "short_name": "Victory", "chest_unopened_img": "images/chest_unopened.png",
                      "chest_opened_img": "images/chest_opened.png", "access_rules": ["freemode", ep_rule(last_ep), f"goal12,{ep_rule(12)}"],
                      "map_locations": [{"map": "orders", "x": pos["victory"][0], "y": pos["victory"][1]}], "sections": [{"name": "Goal", "item_count": 1}]})
    (out / "locations" / "locations.json").write_text(json.dumps(locations, indent=2, ensure_ascii=False), encoding="utf-8")

    # --- carte
    (out / "maps" / "maps.json").write_text(json.dumps([{"name": "orders", "img": "images/maps/orders.png", "location_size": 34,
                                                          "location_border_thickness": 2}], indent=2), encoding="utf-8")

    # --- mise en page
    def grid(rows, size=44):
        return {"type": "itemgrid", "item_size": f"{size},{size}", "item_margin": "2,2", "h_alignment": "left", "rows": rows}

    def chunk(codes: list[str], n: int) -> list[list[str]]:
        return [codes[i:i + n] for i in range(0, len(codes), n)]

    ep_codes = [f"ep{i}" for i in range(1, 15)]
    equip = [slug(n) for n in USEFUL_ITEMS]
    fill = [slug(n) for n in [*FILLER_ITEMS, *EXTRA_FILLER_ITEMS, *EXTRA_FILLER2_ITEMS, *EXTRA_FILLER3_ITEMS, *EXTRA_FILLER4_ITEMS]]
    traps = [slug(n) for n in [*TRAP_ITEMS, *EXTRA_TRAP_ITEMS]]
    left = {"type": "array", "orientation": "vertical", "content": [
        {"type": "group", "header": "Episode access", "content": grid(chunk(ep_codes, 7))},
        {"type": "group", "header": "Equipment", "content": grid(chunk(equip, 7))},
        {"type": "group", "header": "Materials & supplies (received)", "content": grid(chunk(fill, 7))},
        {"type": "group", "header": "Traps (received)", "content": grid(chunk(traps, 7))},
        {"type": "group", "header": "Progress", "content": grid([["goal14", "freemode", "ms_main", "ms_likes", "ms_order", "ms_standard", "ms_bot", "resync"]])}]}
    right = {"type": "dock", "content": [{"type": "recentpins", "dock": "bottom", "style": "wrapped", "max_height": 170},
                                         {"type": "map", "maps": ["orders"]}]}
    layouts = {"tracker_default": {"type": "container", "background": "#0b0f14", "content": {"type": "array", "orientation": "horizontal", "content": [left, right]}},
               "tracker_broadcast": {"type": "container", "background": "#00000000", "content": {"type": "array", "orientation": "vertical", "content": [
                   {"type": "group", "header": "Episode access", "content": grid(chunk(ep_codes, 7))},
                   {"type": "group", "header": "Equipment", "content": grid(chunk(equip, 7))},
                   {"type": "group", "header": "Progress", "content": grid([["goal14", "ms_main", "ms_likes", "ms_order", "ms_standard", "ms_bot"]])}]}}}
    (out / "layouts" / "tracker.json").write_text(json.dumps(layouts, indent=2), encoding="utf-8")

    # --- scripts : table des identifiants (generee) + init + autotracking
    lines = ["-- GENERE par tools/make_poptracker.py : ne pas modifier a la main.", "ITEM_MAPPING = {"]
    for iid, (code, typ) in sorted(item_map.items()):
        lines.append(f"  [{iid}] = {{{lua_str(code)}, {lua_str(typ)}}},")
    lines += ["}", "", "LOCATION_MAPPING = {"]
    for lid, path in sorted(loc_map.items()):
        lines.append(f"  [{lid}] = {lua_str(path)},")
    lines += ["}", "", f"VICTORY_PATH = {lua_str('@Victory (finish the goal episode)/Goal')}", "", "-- episode de chaque commande principale (pour le total selon l'objectif)", "ORDER_EPISODE = {"]
    for no, _, ep in sorted(MAIN_ORDERS):
        lines.append(f"  [{BASE_ID + no}] = {ep},")
    lines += ["}", "", "-- paliers optionnels : base d'identifiant, maximum, option de slot_data qui donne le nombre de checks, code de l'objet compteur",
              "MILESTONES = {",
              f"  {{base = {LIKES_BASE_ID}, max = {MAX_LIKES_CHECKS}, option = \"likes_checks\", code = \"ms_likes\"}},",
              f"  {{base = {ORDER_PROGRESS_BASE_ID}, max = {MAX_ORDER_CHECKS}, option = \"order_checks\", code = \"ms_order\"}},",
              f"  {{base = {STANDARD_ORDER_BASE_ID}, max = {MAX_STANDARD_CHECKS}, option = \"standard_checks\", code = \"ms_standard\"}},",
              f"  {{base = {BOT_ORDER_BASE_ID}, max = {MAX_BOT_CHECKS}, option = \"bot_checks\", code = \"ms_bot\"}},",
              "}", ""]
    (out / "scripts" / "mapping.lua").write_text("\n".join(lines), encoding="utf-8")
    src_lua = here / "poptracker_lua"
    for fn in ("init.lua", "autotracking.lua"):
        shutil.copy(src_lua / fn, out / "scripts" / fn)
    readme = here / "poptracker_README.md"
    if readme.exists():
        shutil.copy(readme, out / "README.md")
    print(f"Pack genere dans {out} : {len(items)} objets, {len(locations)} lieux, {len(item_map)} objets AP, {len(loc_map)} lieux AP")


if __name__ == "__main__":
    main()
