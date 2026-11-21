"""Verifie le pack PopTracker (dossier poptracker/) : JSON valides, correspondance exacte avec le monde (objets et lieux), logique d'acces
des commandes, puis rejoue scripts/mapping.lua + autotracking.lua dans un faux PopTracker (lupa) pour controler la reception d'objets,
les lieux coches, les compteurs et la remise a zero a la reconnexion. Necessite : pip install lupa
Usage : PYTHONPATH=<Archipelago> python3 tests/test_poptracker.py (depot autonome) ou python3 death_stranding_poptracker/tests/test_poptracker.py (fork)"""
import json
import sys
from pathlib import Path

try:
    import ModuleUpdate
    ModuleUpdate.update_ran = True
except ImportError:
    pass
from lupa import LuaRuntime

from worlds.death_stranding.data import BASE_ID, MAIN_ORDERS, ORDER_EPISODE, OPTIONAL_ORDERS
from worlds.death_stranding.items import item_name_to_id
from worlds.death_stranding.locations import location_table

ROOT = Path(__file__).resolve().parent.parent
PACK = ROOT / ("pack" if (ROOT / "pack").is_dir() else "poptracker")
J = lambda p: json.loads((PACK / p).read_text(encoding="utf-8"))


def test_json_and_files():
    man = J("manifest.json")
    assert "ap" in man["variants"]["orders_map"]["flags"] and man["package_uid"]
    items, locs, maps, lay = J("items/items.json"), J("locations/locations.json"), J("maps/maps.json"), J("layouts/tracker.json")
    codes = set()
    for it in items:
        assert it["name"] and it["type"] in ("toggle", "consumable", "progressive")
        for st in it.get("stages", [it]):
            assert (PACK / st["img"]).is_file(), st["img"]
            codes.add(st["codes"])
    codes.add("resync")                                # code fourni par l'objet Lua cree dans scripts/init.lua
    assert (PACK / maps[0]["img"]).is_file() and (PACK / "images/items/resync.png").is_file()
    assert any("resync" in row for g in lay["tracker_default"]["content"]["content"][0]["content"] for row in g["content"].get("rows", []))
    assert "tracker_default" in lay and "tracker_broadcast" in lay

    def walk(n):                                   # tous les codes cites par une grille existent
        if isinstance(n, dict):
            if n.get("type") == "itemgrid":
                for row in n["rows"]:
                    for c in row:
                        assert c in codes, c
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(lay)
    # les regles d'acces ne citent que des codes connus
    for l in locs:
        for rule in l.get("access_rules", []):
            for c in rule.split(","):
                assert c in codes, (l["name"], c)
        assert (PACK / l["chest_unopened_img"]).is_file()
        for m in l["map_locations"]:
            assert 0 <= m["x"] < 900 and m["y"] > 0
    return items, locs


def test_world_correspondence(items, locs):
    assert len(locs) == len(MAIN_ORDERS) + 1                      # + Victoire
    names = {l["name"] for l in locs}
    assert len(names) == len(locs)
    # chaque commande est presente une fois, avec la bonne regle d'episode
    by_no = {}
    for l in locs:
        if l["short_name"].startswith("Order "):
            by_no[int(l["short_name"].split()[1])] = l
    assert set(by_no) == {no for no, _, _ in MAIN_ORDERS}
    for no, _, ep in MAIN_ORDERS:
        rules = by_no[no].get("access_rules")
        if ep == 0:
            assert rules is None
        else:
            assert rules == ["freemode", ",".join(f"ep{i}" for i in range(1, ep + 1))], (no, rules)
        assert ("optional" in by_no[no]["sections"][0]["name"]) == (no in OPTIONAL_ORDERS)
    vic = [l for l in locs if l["short_name"] == "Victory"][0]
    assert vic["access_rules"][1].endswith("ep14") and vic["access_rules"][2].startswith("goal12,") and vic["access_rules"][2].endswith("ep12")


def make_runtime():
    lua = LuaRuntime(unpack_returned_tuples=True)
    lua.execute("""
    FAKE = {}
    local Item = {}; Item.__index = Item
    function Item:SetOverlay(t) self.overlay = t end
    local Sec = {}
    Sec.__index = Sec
    function new_obj(code, kind) local o = setmetatable({code = code, kind = kind, Active = false, AcquiredCount = 0, CurrentStage = 0, ChestCount = 1, AvailableChestCount = 1}, kind == "sec" and Sec or Item); FAKE[code] = o; return o end
    Tracker = {}
    function Tracker:FindObjectForCode(c) return FAKE[c] end
    local handlers = {}
    Archipelago = {}
    function Archipelago:AddClearHandler(n, f) handlers.clear = f end
    function Archipelago:AddItemHandler(n, f) handlers.item = f end
    function Archipelago:AddLocationHandler(n, f) handlers.loc = f end
    function fire(kind, ...) return handlers[kind](...) end
    ScriptHost = {LoadScript = function() end, CreateLuaItem = function() LUAITEM = {}; return LUAITEM end}
    ImageReference = {FromPackRelativePath = function(_, p) return p end}
    function Tracker:AddItems() end
    function Tracker:AddMaps() end
    function Tracker:AddLocations() end
    function Tracker:AddLayouts() end
    """)
    lua.execute((PACK / "scripts" / "mapping.lua").read_text(encoding="utf-8"))
    lua.execute("""
    for _, v in pairs(ITEM_MAPPING) do new_obj(v[1], v[2]) end
    for _, p in pairs(LOCATION_MAPPING) do new_obj(p, "sec") end
    new_obj("goal14", "goal"); for _, m in ipairs(MILESTONES) do new_obj(m.code, "ms") end; new_obj("ms_main", "ms")
    """)
    lua.execute("new_obj(VICTORY_PATH, 'sec')")
    lua.execute((PACK / "scripts" / "init.lua").read_text(encoding="utf-8"))          # PopVersion absent : n'appelle pas l'autotracking
    lua.execute((PACK / "scripts" / "autotracking.lua").read_text(encoding="utf-8"))
    return lua


def test_autotracking():
    lua = make_runtime()
    # tables d'identifiants = celles du monde
    im = {int(k): list(v.values()) for k, v in lua.eval("ITEM_MAPPING").items()}
    assert set(im) == set(item_name_to_id.values()), set(item_name_to_id.values()) ^ set(im)
    lm = {int(k): v for k, v in lua.eval("LOCATION_MAPPING").items()}
    assert set(lm) == {code for code, _ in location_table.values()}
    g = lua.globals()
    obj = lambda c: lua.eval(f"FAKE['{c}']")
    # connexion : objectif 12, 3 paliers de likes, 2 de commandes standard
    slot = lua.table_from({"goal_episode": 12, "likes_checks": 3, "standard_checks": 2})
    g.fire("clear", slot)
    assert obj("goal14").CurrentStage == 1
    assert obj("ms_likes").overlay == "0/3" and obj("ms_likes").Active is True
    assert obj("ms_bot").Active is False and obj("ms_bot").overlay == "0/0"
    total12 = sum(1 for no, _, ep in MAIN_ORDERS if ep <= 12)
    assert obj("ms_main").overlay == f"0/{total12}"
    # objets : toggle, consumable, ordre d'index, doublon d'index ignore
    ep1, ladder = item_name_to_id["Episode 1 Access"], item_name_to_id["Ladder Set"]
    g.fire("item", 1, ep1, "x", 1)
    g.fire("item", 2, ladder, "x", 1)
    g.fire("item", 3, ladder, "x", 1)
    g.fire("item", 3, ladder, "x", 1)       # rejoue (reconnexion) : ignore
    assert obj("ep1").Active is True and obj("ladder_set").AcquiredCount == 2
    # lieux : commande 2 deux fois (rejoue) + un palier de likes
    g.fire("loc", BASE_ID + 2, "x")
    g.fire("loc", BASE_ID + 2, "x")
    g.fire("loc", 7_771_001, "x")
    assert lua.eval(f"FAKE['{lm[BASE_ID + 2]}'].AvailableChestCount") == 0
    assert obj("ms_main").overlay == f"1/{total12}" and obj("ms_likes").overlay == "1/3"
    # bouton Resync : une case cochee a la main par erreur est restauree, une case cochee par le serveur reste cochee
    o3 = lm[BASE_ID + 3]
    fake = lua.eval("FAKE")                                # (le nom de la 3 contient une apostrophe : on passe par la table, pas par du code Lua en chaine)
    fake[o3].AvailableChestCount = 0
    fake[lua.eval("VICTORY_PATH")].AvailableChestCount = 0
    assert lua.eval("LUAITEM.CanProvideCodeFunc(LUAITEM, 'resync')") and lua.eval("LUAITEM.ProvidesCodeFunc(LUAITEM, 'resync')") == 1
    lua.execute("LUAITEM.OnLeftClickFunc(LUAITEM)")
    assert fake[o3].AvailableChestCount == 1 and lua.eval("FAKE[VICTORY_PATH].AvailableChestCount") == 1
    assert lua.eval(f"FAKE['{lm[BASE_ID + 2]}'].AvailableChestCount") == 0
    # reconnexion : tout est remis a zero (objectif 14 par defaut sans slot_data detaille)
    g.fire("clear", lua.table_from({}))
    assert obj("ep1").Active is False and obj("ladder_set").AcquiredCount == 0
    assert lua.eval(f"FAKE['{lm[BASE_ID + 2]}'].AvailableChestCount") == 1
    assert obj("goal14").CurrentStage == 0 and obj("ms_main").overlay == f"0/{len(MAIN_ORDERS)}"


if __name__ == "__main__":
    it, lo = test_json_and_files()
    test_world_correspondence(it, lo)
    test_autotracking()
    print("test_poptracker : OK")
