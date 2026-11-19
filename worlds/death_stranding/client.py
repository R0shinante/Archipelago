"""Client Archipelago pour Death Stranding (PC).

  * reseau (CommonClient)  : connexion, checks, items recus, victoire ;
  * memoire (memory.py)    : ressources, stocks, likes, compteurs de commandes, et titre du dernier point de controle
                             (detection des commandes principales terminees, sans dechiffrer les sauvegardes) ;
  * sauvegardes (savewatch): meme detection par dechiffrement des checkpoints, en option (secours) ;
  * mode manuel            : /check <lieu> envoie un check a la main.

Commandes : /ds_status, /ds_give, /ds_stock, /ds_stock_give, /ds_stock_target, /ds_stock_mode, /ds_stock_pool, /ds_hp, /ds_kill, /ds_effect, /ds_trap (alias),
/ds_likes, /ds_likes_give, /ds_likes_rebase, /ds_orders, /ds_orders_rebase, /ds_standard, /ds_standard_rebase, /ds_bot, /ds_bot_rebase, /ds_counters, /ds_held,
/ds_items, /ds_items_reset, /ds_resigner, /ds_saves, /ds_saves_dir, /ds_selftest, /ds_catchup.
"""
from __future__ import annotations

import asyncio
import random
import time
import json
import os
import re
import typing

import Utils
from CommonClient import CommonContext, ClientCommandProcessor, get_base_parser, gui_enabled, logger, server_loop
from MultiServer import mark_raw
from NetUtils import ClientStatus

from .data import EPISODES, ORDER_TO_LOCATION
from .locations import BOT_ORDER_BASE_ID, ORDER_PROGRESS_BASE_ID, STANDARD_ORDER_BASE_ID, location_name_to_id
from .memory import GameMemory, PymemBackend
from .savewatch import DEFAULT_COMPLETED_WORDS, ResignerCli, SaveWatcher, autodetect_root, parse_title, read_header

# lieu -> episode (option episode_gating) : meme table que la generation (data.EPISODES) ; le prologue (episode 0) n'est jamais retenu
EPISODE_OF_LOCATION: typing.Dict[int, int] = {location_name_to_id[name]: ep for ep, names in EPISODES.items() if ep > 0 for name in names}

# Familles de checks par type de commande lues dans la table de compteurs nommes : (base d'id, prefixe d'option, libelle, nom du lieu)
ORDER_TYPES = {"bot": (BOT_ORDER_BASE_ID, "bot", "commandes de bot", "Bot Orders")}

MAP_FILE = "memory_map.json"
PROGRESS_FILE = "DeathStranding_progress.json"
SETTINGS_FILE = "DeathStranding_settings.json"
SAVE_POLL_SECONDS = 2.0


def load_map() -> dict:
    import pkgutil
    default = json.loads(pkgutil.get_data(__name__, "memory_map.default.json").decode("utf-8"))
    path = Utils.user_path(MAP_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            logger.info(f"Configuration memoire : {path}")
            user = json.load(f)
        missing = [k for k in default if k not in user and not k.startswith("_")]
        if missing:   # un fichier d'une ancienne version ne doit pas masquer les sections ajoutees depuis
            logger.info(f"Configuration memoire : sections absentes de votre fichier, valeurs du paquet utilisees : {', '.join(missing)}")
            user = {**{k: default[k] for k in missing}, **user}
        return user
    logger.info("Configuration memoire : valeurs par defaut du paquet.")
    return default


def _clean_path(text: str) -> str:
    """Chemin saisi a la main : espaces et guillemets autour retires, "\\\\" doubles ramenes a "\\" si le chemin existe ainsi."""
    p = text.strip().strip('"').strip("'").strip()
    if "\\\\" in p and not os.path.exists(p):
        p2 = p.replace("\\\\", "\\")
        if os.path.exists(p2):
            return p2
    return p


RESEND_SECONDS = 15.0


def plan_location_sends(wanted: typing.Iterable[int], checked: typing.Set[int], server_locations: typing.Set[int],
                        sent_at: typing.Dict[int, float], now: float, resend: float = RESEND_SECONDS
                        ) -> typing.Tuple[typing.List[int], typing.List[int]]:
    """Decide quoi envoyer au serveur. Renvoie (a_envoyer, inconnus_du_serveur).

    - un lieu deja coche cote serveur n'est jamais renvoye ;
    - un lieu envoye est renvoye au plus toutes les `resend` secondes tant que le serveur ne l'a pas confirme ;
    - un lieu que le serveur ne connait pas (partie generee avec une autre version de l'APWorld) n'est jamais envoye.
    """
    pending = set(wanted) - checked
    unknown = sorted(pending - server_locations) if server_locations else []
    pending -= set(unknown)
    to_send = sorted(c for c in pending if now - sent_at.get(c, -1e9) >= resend)
    return to_send, unknown


def _json_load(name: str) -> dict:
    try:
        with open(Utils.user_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _json_save(name: str, data: dict) -> None:
    try:
        with open(Utils.user_path(name), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=1)
    except OSError:
        logger.warning(f"Impossible d'ecrire {name}.")


class DeathStrandingCommandProcessor(ClientCommandProcessor):
    def _debug_enabled(self) -> bool:
        """Les commandes de test qui ECRIVENT dans le jeu (/ds_give, /ds_effect, /ds_trap, /ds_likes_give, /ds_stock_give, /ds_kill) sont coupees
        par defaut : /ds_debug on les active pour la session en cours (jamais enregistre : elles sont coupees a chaque lancement du client)."""
        if getattr(self.ctx, "debug_commands", False):
            return True
        self.output("Commande de test desactivee : elle ecrit dans le jeu. Tapez /ds_debug on pour l'activer (jusqu'a la fermeture du client).")
        return False

    def _cmd_ds_debug(self, mode: str = "") -> None:
        """Active ou coupe les commandes de test qui ecrivent dans le jeu : /ds_debug on | off (coupees a chaque lancement)."""
        m = mode.strip().lower()
        if m in ("on", "off"):
            self.ctx.debug_commands = (m == "on")
        names = "/ds_give, /ds_effect, /ds_trap, /ds_likes_give, /ds_stock_give, /ds_kill"
        self.output(f"Commandes de test {'ACTIVEES' if getattr(self.ctx, 'debug_commands', False) else 'desactivees'} : {names}. "
                    "Usage : /ds_debug on | off.")

    @mark_raw
    def _cmd_check(self, name: str = "") -> None:
        """Envoie manuellement un check : /check <nom exact du lieu>"""
        loc = name.strip()
        if loc not in location_name_to_id:
            self.output(f"Lieu inconnu : {loc}")
            return
        self.ctx.manual_checks.add(location_name_to_id[loc])
        self.output(f"Check en file : {loc}")

    def _cmd_locations(self) -> None:
        """Liste les lieux restants."""
        for name, code in location_name_to_id.items():
            if code in self.ctx.missing_locations:
                self.output(name)

    def _cmd_ds_status(self) -> None:
        """Diagnostic : le client voit-il le jeu et l'inventaire ?"""
        ctx = self.ctx
        if not ctx.backend.attached() and not ctx.backend.attach():
            self.output("Jeu introuvable (ds.exe). Lance le jeu et charge une sauvegarde.")
            return
        obj = ctx.memory.resolve_object()
        if obj is None:
            self.output("Jeu detecte, mais inventaire introuvable (menu principal ? sauvegarde pas chargee ?).")
            return
        self.output(f"Inventaire trouve a {obj:#x}.")
        for name in ctx.map.get("inventory", {}).get("resources", {}):
            self.output(f"  {name} : {ctx.memory.read_resource(name)} (quantite, maximum)")

    def _cmd_ds_give(self, *args: str) -> None:
        """[test, /ds_debug on] /ds_give <ressource> <quantite>   ex : /ds_give Chiral Crystals 100"""
        if not self._debug_enabled():
            return
        if len(args) < 2:
            self.output("Usage : /ds_give <ressource> <quantite>")
            return
        resource = " ".join(args[:-1])
        try:
            n = int(args[-1])
        except ValueError:
            self.output("Quantite invalide.")
            return
        new = self.ctx.memory.add_resource(resource, n)
        self.output(f"{resource} -> {new}" if new is not None else "Echec (voir /ds_status).")

    @mark_raw
    def _cmd_ds_effect(self, name: str = "") -> None:
        """[test, /ds_debug on] Test d'un piege ou d'un effet : /ds_effect <nom>  (ex : /ds_effect Injury, /ds_effect Blood Bag). Sans nom : liste."""
        if not self._debug_enabled():
            return
        ctx = self.ctx
        traps = {k: v for d in ("traps", "boosts") for k, v in ctx.map.get(d, {}).items() if not k.startswith("_")}
        all_names = list(traps) + [k for k, v in ctx.map.get("item_grants", {}).items()
                                   if k.endswith("Trap")]
        q = name.strip().lower()
        match = [n for n in all_names if q and q in n.lower()]
        if len(match) != 1:
            self.output("Pieges : " + ", ".join(all_names) + ("  -> precisez le nom." if q else ""))
            return
        n = match[0]
        if n in traps:
            status, done = apply_effects(ctx.memory, traps[n])
            self.output({"ok": f"{n} : " + ", ".join(f"{f} {r[0]:.1f} -> {r[1]:.1f}" for f, r in done),
                         "wait": "Joueur illisible (menu ? chargement ?). Voir /ds_hp.",
                         "fail": "Valeur incoherente : effet abandonne."}[status])
        else:
            g = ctx.map["item_grants"][n]
            q2 = ctx.memory.add_resource(g["resource"], int(g["amount"]))
            self.output(f"{n} : {g['resource']} -> {q2}" if q2 is not None else "Inventaire illisible (voir /ds_status).")

    @mark_raw
    def _cmd_ds_trap(self, name: str = "") -> None:
        """[test, /ds_debug on] Alias de /ds_effect (ancien nom)."""
        self._cmd_ds_effect(name)

    def _cmd_ds_held(self) -> None:
        """Checks retenus en attente d'un objet « Episode N Access » (option episode_gating)."""
        ctx = self.ctx
        if not ctx.slot_data.get("episode_gating"):
            self.output("L'option episode_gating n'est pas activee dans cette partie : aucun check n'est retenu.")
            return
        if not ctx.held_codes:
            self.output("Aucun check retenu.")
            return
        for code in sorted(ctx.held_codes):
            self.output(f"  {ctx.location_names.lookup_in_game(code)} (episode {EPISODE_OF_LOCATION[code]})")

    def _cmd_ds_likes(self) -> None:
        """Likes lus en memoire (PNJ / autres joueurs / total)."""
        v = self.ctx.memory.read_likes()
        if v is None:
            self.output("Likes illisibles (jeu non charge ?).")
            return
        self.output(f"Likes : PNJ {v[0]} + joueurs {v[1]} = {v[0] + v[1]}")
        st, step = self.ctx.likes_state, int(self.ctx.slot_data.get("likes_step", 0))
        if "baseline" in st and step:
            gained = max(0, v[0] + v[1] - int(st["baseline"]) - int(st.get("granted", 0)))
            self.output(f"Paliers : {gained} likes gagnes depuis la base ({st['baseline']}), prochain palier a {(gained // step + 1) * step} "
                        f"(paliers atteints : {len(self.ctx.likes_checks)}/{self.ctx.slot_data.get('likes_checks', 0)})")

    def _cmd_ds_orders(self) -> None:
        """Compteur d'etapes de commande lu en memoire et etat des paliers de progression des commandes."""
        v = self.ctx.memory.read_order_progress()
        if v is None:
            self.output("Compteur de commandes illisible (jeu non charge ?).")
            return
        self.output(f"Compteur d'etapes de commande : {v}")
        st, step = self.ctx.order_state, int(self.ctx.slot_data.get("order_step", 0))
        if "baseline" in st and step > 0:
            gained = max(0, v - int(st["baseline"]))
            self.output(f"Paliers : {gained} etapes depuis la base ({st['baseline']}), prochain palier a {(gained // step + 1) * step} "
                        f"(paliers atteints : {len(self.ctx.order_checks)}/{self.ctx.slot_data.get('order_checks', 0)})")

    def _cmd_ds_orders_rebase(self) -> None:
        """Refixe la base des paliers de progression des commandes au compteur actuel (les checks deja envoyes restent envoyes)."""
        v = self.ctx.memory.read_order_progress()
        if v is None:
            self.output("Compteur de commandes illisible (jeu non charge ?).")
            return
        self.ctx.order_state["baseline"] = v
        self.ctx.save_progress()
        self.output(f"Base de progression des commandes : {v}.")

    def _cmd_ds_standard(self) -> None:
        """Commandes standard livrees (compteur exact du jeu) et etat des paliers « Standard Orders »."""
        v = self.ctx.memory.read_standard_orders()
        if v is None:
            self.output("Compteur de commandes standard illisible (jeu non charge ?).")
            return
        self.output(f"Commandes standard livrees : {v}")
        st, step = self.ctx.standard_state, int(self.ctx.slot_data.get("standard_step", 0))
        if "baseline" in st and step > 0:
            gained = max(0, v - int(st["baseline"]))
            self.output(f"Paliers : {gained} livraison(s) depuis la base ({st['baseline']}), prochain palier a {(gained // step + 1) * step} "
                        f"(paliers atteints : {len(self.ctx.standard_checks)}/{self.ctx.slot_data.get('standard_checks', 0)})")

    def _cmd_ds_standard_rebase(self) -> None:
        """Refixe la base des paliers de commandes standard au compteur actuel (les checks deja envoyes restent envoyes)."""
        v = self.ctx.memory.read_standard_orders()
        if v is None:
            self.output("Compteur de commandes standard illisible (jeu non charge ?).")
            return
        self.ctx.standard_state["baseline"] = v
        self.ctx.save_progress()
        self.output(f"Base des commandes standard : {v}.")

    def _explain_types_failure(self) -> None:
        named, why = self.ctx.memory.named_counters_report()
        if named is None:
            self.output(f"Compteurs de commandes illisibles : {why}")
        elif self.ctx.memory.read_standard_orders() is None:
            self.output("Compteurs de commandes illisibles : le compteur de commandes standard (table de statistiques) est illisible.")
        else:
            self.output("Compteurs de commandes illisibles (jeu non charge ?).")

    def _type_status(self, kind: str) -> None:
        label, opt = ORDER_TYPES[kind][2], ORDER_TYPES[kind][1]
        t = self.ctx.memory.read_order_types()
        if t is None:
            self._explain_types_failure()
            return
        self.output(f"Livraisons de {label} (compteur relatif, a une constante pres) : {t[kind]}  [{self.ctx.memory.named_counters_report()[1]}]")
        st, step = self.ctx.type_state.get(kind, {}), int(self.ctx.slot_data.get(f"{opt}_step", 0))
        if "baseline" in st and step > 0:
            gained = max(0, t[kind] - int(st["baseline"]))
            self.output(f"Paliers : {gained} livraison(s) depuis la base ({st['baseline']}), prochain palier a {(gained // step + 1) * step} "
                        f"(paliers atteints : {len(self.ctx.type_checks[kind])}/{self.ctx.slot_data.get(f'{opt}_checks', 0)})")

    def _type_rebase(self, kind: str) -> None:
        t = self.ctx.memory.read_order_types()
        if t is None:
            self._explain_types_failure()
            return
        self.ctx.type_state.setdefault(kind, {})["baseline"] = t[kind]
        self.ctx.save_progress()
        self.output(f"Base des {ORDER_TYPES[kind][2]} : {t[kind]}.")

    def _cmd_ds_bot(self) -> None:
        """Commandes de bot livrees (compteur en direct) et etat des paliers « Bot Orders »."""
        self._type_status("bot")

    def _cmd_ds_bot_rebase(self) -> None:
        """Refixe la base des paliers de commandes de bot au compteur actuel (les checks deja envoyes restent envoyes)."""
        self._type_rebase("bot")

    def _cmd_ds_counters(self, action: str = "", mode: str = "") -> None:
        """Diagnostic (lecture seule) : tous les compteurs nommes du jeu. /ds_counters snap = photo ; /ds_counters diff = ce qui a change depuis la photo ; /ds_counters save = fichier complet ; /ds_counters watch [on|off] = ecrit en continu chaque changement (recherche)."""
        ctx = self.ctx
        dump = ctx.memory.dump_named_table()
        if dump is None:
            self._explain_types_failure()
            return
        known = {bytes.fromhex(c["key"]).hex(): n for n, c in ctx.map.get("named_counters", {}).get("counters", {}).items()}
        act = (action.strip() + " " + mode.strip()).strip().lower()
        if act == "snap":
            ctx.counters_snap = dump
            self.output(f"Photo prise : {len(dump)} compteurs. Faites l'action a tester dans le jeu, attendez la fin de la sauvegarde (environ une minute), puis /ds_counters diff.")
        elif act == "diff":
            if ctx.counters_snap is None:
                self.output("Aucune photo : faites d'abord /ds_counters snap.")
                return
            old = ctx.counters_snap
            lines = [f"  {k} : {old[k] if k in old else 'absent'} -> {v}" + (f"   [{known[k]}]" if k in known else "")
                     for k, v in sorted(dump.items()) if old.get(k) != v]
            lines += [f"  {k} : {old[k]} -> disparu" + (f"   [{known[k]}]" if k in known else "") for k in sorted(old) if k not in dump]
            self.output(f"{len(lines)} compteur(s) different(s) de la photo ({len(old)} -> {len(dump)} compteurs) :" if lines else "Aucun compteur n'a change depuis la photo.")
            for line in lines[:40]:
                self.output(line)
            if len(lines) > 40:
                self.output(f"  ... et {len(lines) - 40} autres (utilisez /ds_counters save).")
        elif act in ("watch", "watch on", "watch off"):
            ctx.counters_watch = act != "watch off" and not (act == "watch" and ctx.counters_watch)
            ctx.counters_watch_last = None
            self.output("Mode recherche ACTIF : chaque changement de compteur nomme est ecrit dans la console (toutes les 5 s). Pensez a le couper apres le test : /ds_counters watch off."
                        if ctx.counters_watch else "Mode recherche coupe.")
        elif act == "save":
            path = Utils.user_path("DeathStranding_counters.json")
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump({"time": time.strftime("%Y-%m-%d %H:%M:%S"), "known": known, "counters": dump}, f, indent=1, sort_keys=True)
                self.output(f"{len(dump)} compteurs ecrits dans {path}")
            except OSError as e:
                self.output(f"Ecriture impossible : {e}")
        else:
            self.output(f"{len(dump)} compteurs dans la table nommee ({len(known)} utilises par le client). /ds_counters snap | diff | save | watch [on|off]")

    def _cmd_ds_likes_rebase(self) -> None:
        """Refixe la base des paliers de likes au total actuel (les checks deja envoyes restent envoyes)."""
        v = self.ctx.memory.read_likes()
        if v is None:
            self.output("Likes illisibles (jeu non charge ?).")
            return
        self.ctx.likes_state.update(baseline=v[0] + v[1], granted=0)
        self.ctx.save_progress()
        self.output(f"Base des paliers de likes : {v[0] + v[1]}.")

    def _cmd_ds_likes_give(self, which: str = "", amount: str = "") -> None:
        """[test, /ds_debug on] /ds_likes_give <npc|players> <quantite>"""
        if not self._debug_enabled():
            return
        try:
            n = int(amount)
        except ValueError:
            n = None
        if which not in ("npc", "players") or n is None:
            self.output("Usage : /ds_likes_give <npc|players> <quantite>")
            return
        r = self.ctx.memory.add_likes(which, n)
        self.output(f"Likes {which} -> {r}" if r is not None else "Likes illisibles (jeu non charge ?).")

    def _cmd_ds_hp(self) -> None:
        """Lit la vie du joueur en memoire (test avant d'activer DeathLink)."""
        ctx = self.ctx
        if not ctx.backend.attached() and not ctx.backend.attach():
            self.output("Jeu introuvable (ds.exe).")
            return
        v = ctx.memory.read_vitals()
        self.output(f"Vie : {v[0]:.0f} / {v[1]:.0f}" if v else "Vie introuvable (menu ? chargement ? sauvegarde pas chargee ?).")

    def _cmd_ds_kill(self) -> None:
        """[test, /ds_debug on] Met la vie de Sam a 0 (verifie si cela le tue vraiment)."""
        if not self._debug_enabled():
            return
        ok = self.ctx.memory.kill_player()
        self.output("Vie mise a 0." if ok else "Impossible (jeu non charge ou valeurs incoherentes). Voir /ds_hp.")

    def _cmd_ds_items(self) -> None:
        """Diagnostic : objets recus du serveur et objets deja appliques en jeu."""
        ctx = self.ctx
        names = [ctx.item_names.lookup_in_game(i.item) for i in ctx.items_received]
        self.output(f"Objets recus : {len(names)} ; appliques : {ctx.applied_index} (cle {ctx._progress_key()})")
        for k, n in enumerate(names[-5:], start=max(0, len(names) - 5)):
            self.output(f"  #{k} {n} {'(applique)' if k < ctx.applied_index else '(EN ATTENTE)'}")
        if ctx.applied_index > len(names):
            self.output("Index d'application superieur au nombre d'objets recus : /ds_items_reset pour le recaler.")

    def _cmd_ds_items_reset(self, n: str = "") -> None:
        """Recale l'index d'objets appliques : /ds_items_reset <n>  (les objets a partir de n seront reappliques)"""
        try:
            idx = int(n)
        except ValueError:
            self.output("Usage : /ds_items_reset <n>  (0 = tout reappliquer ; attention aux ressources deja ajoutees)")
            return
        self.ctx.applied_index = max(0, idx)
        self.ctx.save_progress()
        self.output(f"Index d'application : {self.ctx.applied_index}")

    @mark_raw
    def _cmd_ds_stock(self, facility: str = "") -> None:
        """Stocks de materiaux d'une installation : /ds_stock [installation]  (par defaut : celle(s) qui recoivent les objets)"""
        ctx = self.ctx
        if not ctx.backend.attached() and not ctx.backend.attach():
            self.output("Jeu introuvable (ds.exe). Lance le jeu et charge une sauvegarde.")
            return
        known = ctx.map.get("facilities", {}).get("stock", {})
        names = [facility.strip()] if facility.strip() else ctx.stock_targets()
        if ctx.memory.stock_base() is None:
            self.output("Stocks introuvables (menu principal ? sauvegarde pas chargee ? decalages a verifier).")
            return
        for n in names:
            if n not in known:
                self.output(f"Installation inconnue : {n}. Exemples : {', '.join(list(known)[:4])}...")
                continue
            vals = {m: ctx.memory.read_stock(n, m) for m in known[n]}
            self.output(f"{n} : " + ", ".join(f"{m} {v}" for m, v in vals.items()))

    def _cmd_ds_stock_mode(self, mode: str = "") -> None:
        """Repartition des materiaux recus : /ds_stock_mode random (installation au hasard) ou target (installation choisie)"""
        if mode not in ("random", "target"):
            cur = self.ctx.settings.get("stock_mode") or self.ctx.map.get("facilities", {}).get("stock_mode", "random")
            self.output(f"Mode actuel : {cur}. Usage : /ds_stock_mode random | target")
            return
        self.ctx.settings["stock_mode"] = mode
        _json_save(SETTINGS_FILE, self.ctx.settings)
        self.output(f"Mode de repartition des materiaux : {mode}")

    @mark_raw
    def _cmd_ds_stock_pool(self, names: str = "") -> None:
        """Limite le mode random a certaines installations : /ds_stock_pool Nom1; Nom2; Nom3   (/ds_stock_pool all pour tout reprendre)"""
        known = self.ctx.map.get("facilities", {}).get("stock", {})
        n = names.strip()
        if n.lower() in ("", "all", "tout"):
            self.ctx.settings.pop("stock_pool", None)
            _json_save(SETTINGS_FILE, self.ctx.settings)
            self.output(f"Pool : toutes les installations ({len(known)}).")
            return
        wanted = [x.strip() for x in n.split(";") if x.strip()]
        bad = [x for x in wanted if x not in known]
        if bad:
            self.output(f"Installations inconnues : {', '.join(bad)}")
            return
        self.ctx.settings["stock_pool"] = wanted
        _json_save(SETTINGS_FILE, self.ctx.settings)
        self.output(f"Pool du mode random : {', '.join(wanted)}")

    @mark_raw
    def _cmd_ds_stock_target(self, facility: str = "") -> None:
        """Choisit l'installation qui recoit les materiaux : /ds_stock_target <installation>  (ex : Port Knot City)"""
        n = facility.strip()
        if n not in self.ctx.map.get("facilities", {}).get("stock", {}):
            self.output(f"Installation inconnue : {n!r}. Voir /ds_stock pour un exemple de nom.")
            return
        self.ctx.settings["stock_target"] = [n]
        _json_save(SETTINGS_FILE, self.ctx.settings)
        self.output(f"Les materiaux recus seront credites a : {n}")

    def _cmd_ds_stock_give(self, *args: str) -> None:
        """[test, /ds_debug on] /ds_stock_give <materiau> <quantite>   ex : /ds_stock_give Metals 50  (credite l'installation choisie)"""
        if not self._debug_enabled():
            return
        if len(args) < 2:
            self.output("Usage : /ds_stock_give <Resins|Metals|Ceramics|Chemicals|Special Alloys|Chiral Crystals> <quantite>")
            return
        try:
            n = int(args[-1])
        except ValueError:
            self.output("Quantite invalide.")
            return
        material = " ".join(args[:-1])
        for f in self.ctx.stock_targets():
            new = self.ctx.memory.add_stock(f, material, n)
            self.output(f"{f} / {material} -> {new}" if new is not None else f"Echec pour {f} (voir /ds_stock).")

    # -- sauvegardes -------------------------------------------------------
    @mark_raw
    def _cmd_ds_resigner(self, path: str = "") -> None:
        """Indique l'outil de dechiffrement : /ds_resigner <chemin complet de death-stranding-savedata-resigner-cli.exe>"""
        if path.strip().lower() in ("off", "non", "desactiver"):
            self.ctx.settings["resigner_off"] = True
            _json_save(SETTINGS_FILE, self.ctx.settings)
            self.ctx.setup_saves()
            self.output("Dechiffrement des sauvegardes DESACTIVE (les commandes principales ne viennent plus que de la memoire). /ds_resigner on pour le reactiver.")
            return
        if path.strip().lower() in ("on", "oui", "activer"):
            self.ctx.settings["resigner_off"] = False
            _json_save(SETTINGS_FILE, self.ctx.settings)
            self.ctx.setup_saves()
            self.output("Dechiffrement des sauvegardes reactive.")
            return
        p = _clean_path(path)
        if not p or not os.path.isfile(p):
            self.output("Fichier introuvable. Exemple : /ds_resigner C:\\outils\\death-stranding-savedata-resigner-cli.exe")
            return
        self.ctx.settings["resigner"] = p
        _json_save(SETTINGS_FILE, self.ctx.settings)
        self.ctx.setup_saves()
        self.output(f"Outil enregistre : {p}. Lance /ds_selftest pour verifier.")

    def _cmd_ds_saves(self) -> None:
        """Etat de la surveillance des sauvegardes."""
        w = self.ctx.saves
        self.output(f"Dossier des sauvegardes : {w.root or 'INTROUVABLE (voir /ds_saves_dir)'}")
        self.output(f"Outil de dechiffrement : {self.ctx.settings.get('resigner') or 'NON CONFIGURE (/ds_resigner <chemin>)'}")
        self.output(f"Checkpoints vus : {len(w.files())} ; commandes terminees detectees : {sorted(w.completed) or 'aucune'}")
        if w.last_title:
            self.output(f"Dernier titre lu : {w.last_title}")
        if w.failures:
            self.output(f"Echecs de dechiffrement : {w.failures} (dernier journal : {' | '.join(w.decryptor.log) if w.decryptor else '-'})")

    @mark_raw
    def _cmd_ds_saves_dir(self, path: str = "") -> None:
        """Indique le dossier des sauvegardes : /ds_saves_dir <dossier contenant les sous-dossiers de checkpoints>"""
        p = _clean_path(path)
        if not p or not os.path.isdir(p):
            self.output("Dossier introuvable. Exemple : /ds_saves_dir C:\\Users\\toi\\AppData\\Local\\KojimaProductions\\DeathStrandingDC\\123456789")
            return
        self.ctx.settings["saves_root"] = p
        _json_save(SETTINGS_FILE, self.ctx.settings)
        self.ctx.setup_saves()
        self.output(f"Dossier enregistre : {p}")

    def _cmd_ds_selftest(self) -> None:
        """Dechiffre le checkpoint le plus recent et affiche son titre (verifie toute la chaine)."""
        w = self.ctx.saves
        if not w.ready():
            self.output("Pas pret : verifie /ds_saves (dossier des sauvegardes et outil de dechiffrement).")
            return
        files = w.files()
        if not files:
            self.output("Aucun checkpoint.dat dans le dossier des sauvegardes.")
            return
        newest = max(files, key=lambda f: f.stat().st_mtime)
        self.output(f"Test sur : {newest}")
        data = w.decryptor.decrypt(newest)
        for line in w.decryptor.log:
            self.output(f"  {line}")
        if data is None:
            self.output("ECHEC du dechiffrement.")
            return
        header = read_header(data)
        if header is None:
            self.output("Fichier dechiffre mais en-tete illisible.")
            return
        title = header.get("Title", "")
        self.output(f"Titre : {title}")
        parsed = parse_title(title, w.words)
        self.output(f"Lecture : {parsed}  (terminee ?, numero, nom)" if parsed else "Titre non reconnu comme une commande.")

    def _cmd_ds_catchup(self) -> None:
        """Traite TOUS les checkpoints existants (y compris anciens) et envoie les checks correspondants."""
        w = self.ctx.saves
        if not w.ready():
            self.output("Pas pret : verifie /ds_saves.")
            return
        found = w.catch_up()
        self.ctx.register_completed_orders(found)
        self.output(f"Commandes terminees trouvees : {sorted(found) or 'aucune'}")


class DeathStrandingContext(CommonContext):
    game = "Death Stranding"
    command_processor = DeathStrandingCommandProcessor
    items_handling = 0b111

    def __init__(self, server_address, password):
        super().__init__(server_address, password)
        self.manual_checks: set[int] = set()
        self.save_checks: set[int] = set()
        self.sent_at: dict[int, float] = {}
        self.warned_unknown: set[int] = set()
        self.applied_index = 0
        self.likes_checks: set[int] = set()
        self.likes_state: dict = {}
        self.likes_history: typing.List[int] = []
        self.order_checks: set[int] = set()
        self.order_state: dict = {}
        self.order_history: typing.List[int] = []
        self.standard_checks: set[int] = set()
        self.standard_state: dict = {}
        self.standard_history: typing.List[int] = []
        self.type_checks: typing.Dict[str, set] = {"bot": set()}
        self.type_state: typing.Dict[str, dict] = {}
        self.type_history: typing.List[tuple] = []
        self.title_zones: typing.Optional[typing.List[typing.Tuple[int, int]]] = None
        self.title_seen: typing.Set[typing.Tuple[int, str]] = set()
        self.title_baselined = False
        self.title_force_full = False
        self.title_hint_failed = False
        self.types_source_logged = False
        self.repair_last: typing.Optional[tuple] = None
        self.repair_marks: tuple = (None, None)
        self.debug_commands = False      # commandes de test qui ecrivent dans le jeu : coupees a chaque lancement (/ds_debug on)
        self.bot_hold_state: dict = {}
        self.bot_hold_logged = False
        self.sig_times: typing.List[float] = []       # heures des fins de commande principale / speciale reconnues dans les compteurs, pas encore identifiees
        self.sig_last_ta = None
        self.created_keys: typing.Dict[str, float] = {}      # cle -> heure de creation (120 s), pour les cles marqueurs de commande
        self.marker_done: typing.Set[tuple] = set()
        self.bot_hold_keys: typing.Optional[typing.Set[str]] = None     # cles de la table au releve precedent (detecte les creations)
        self.raw_logged: typing.Optional[tuple] = None
        self.title_burst_until = 0.0
        self.title_active_logged = False
        self.title_last_main: typing.Optional[typing.Tuple[int, int]] = None
        self.title_none_logged = False
        self.title_full_end = -1e9         # fin (horloge de la boucle) de la derniere recherche complete
        self.title_empty_streak = 0        # recherches completes vides de suite : espace les prochaines
        self.title_alert_until = 0.0       # jusqu'ici : cadence soutenue apres une variation des compteurs de livraisons
        self.unlisted_seen: typing.Set[int] = set()
        self.counters_snap: typing.Optional[typing.Dict[str, int]] = None
        self.counters_watch: bool = False
        self.held_codes: typing.Set[int] = set()
        self.held_logged: typing.Set[int] = set()
        self.counters_watch_last: typing.Optional[typing.Dict[str, int]] = None
        self.slot_data: dict = {}
        self.finished = False
        self.map = load_map()
        self.settings = _json_load(SETTINGS_FILE)
        self.backend = PymemBackend(self.map.get("process_name", "ds.exe"))
        self.memory = GameMemory(self.map, self.backend)
        self._warned_item: typing.Optional[int] = None
        self.death_pending = False
        self.alive_polls = 0
        self.death_suppress_until = 0.0
        self.saves: SaveWatcher
        self.setup_saves()

    def setup_saves(self) -> None:
        exe = self.settings.get("resigner") or self.map.get("saves", {}).get("resigner")
        if self.settings.get("resigner_off"):
            exe = None
        root = self.settings.get("saves_root") or self.map.get("saves", {}).get("root") or autodetect_root()
        words = self.map.get("saves", {}).get("completed_words", DEFAULT_COMPLETED_WORDS)
        self.saves = SaveWatcher(root, ResignerCli(exe) if exe else None, words)
        if exe and not root:
            logger.info("Sauvegardes : dossier introuvable. Tape /ds_saves_dir <dossier>.")

    def hint_windows(self) -> typing.Optional[typing.List[typing.Tuple[int, int]]]:
        """Zone de la memoire ou le jeu a place ses donnees lors de la derniere session (memorisee) : la recherche y commence."""
        h = self.settings.get("mem_hint")
        if isinstance(h, list) and len(h) == 2 and 0 < int(h[0]) < int(h[1]):
            return [(int(h[0]), int(h[1]) - int(h[0]))]
        return None

    def update_hint(self, addresses: typing.Iterable[int], margin: int = 768 << 20) -> None:
        addresses = list(addresses)
        if not addresses:
            return
        new = [max(0, min(addresses) - margin), max(addresses) + margin]
        old = self.settings.get("mem_hint")
        if not (isinstance(old, list) and len(old) == 2 and abs(int(old[0]) - new[0]) < (128 << 20) and abs(int(old[1]) - new[1]) < (128 << 20)):
            self.settings["mem_hint"] = new
            _json_save(SETTINGS_FILE, self.settings)

    def register_completed_orders(self, numbers: typing.Iterable[int], source: str = "sauvegarde") -> None:
        newly: typing.List[int] = []
        for n in numbers:
            loc = ORDER_TO_LOCATION.get(n)
            if loc is None:
                # les commandes standard / optionnelles ont des numeros a partir de 100 environ ; en dessous, il peut s'agir d'une commande
                # principale absente de la liste (voir « Limites connues ») : on le signale une fois pour aider a completer la liste
                if n < 100 and n not in self.unlisted_seen:
                    self.unlisted_seen.add(n)
                    logger.info(f"Commande n°{n} terminee, mais absente de la liste des checks (commande principale manquante ?). "
                                f"Merci de la signaler avec son nom et son episode.")
                else:
                    logger.debug(f"Commande n°{n} terminee (hors liste des checks : ignoree).")
                continue
            code = location_name_to_id[loc]
            if code not in self.save_checks:
                self.save_checks.add(code)
                logger.info(f"Commande terminee detectee ({source}) : {loc}")
                newly.append(n)
        if newly:
            self.sig_times, orphans = unmatched_signatures(self.sig_times, time.time(), len(newly), source in ("compteur", "marqueur"))
            if orphans:
                top = max(newly)
                maybe = sorted((n for n in ORDER_TO_LOCATION if n < top and location_name_to_id[ORDER_TO_LOCATION[n]] not in self.save_checks
                                and location_name_to_id[ORDER_TO_LOCATION[n]] not in self.checked_locations), reverse=True)[:orphans]
                logger.warning(f"{orphans} fin(s) de commande principale ou speciale reperee(s) dans les compteurs n'ont pas pu etre identifiee(s) : le jeu ne garde que la "
                               f"derniere commande terminee a chaque enregistrement. " + (f"Probablement : {' ; '.join(ORDER_TO_LOCATION[n] for n in maybe)}. " if maybe else "")
                               + "Si son check n'est pas parti, envoyez-le avec /check <nom exact du lieu> (ex. /check "
                               + (ORDER_TO_LOCATION[maybe[0]] if maybe else "Order 63 - Network Activation Key Delivery: Edge Knot City") + ").")

    def stock_targets(self) -> typing.List[str]:
        """Installations qui recoivent les materiaux : reglage utilisateur, sinon valeur par defaut du paquet."""
        t = self.settings.get("stock_target") or self.map.get("facilities", {}).get("stock_target") or []
        return [t] if isinstance(t, str) else list(t)

    def stock_targets_for(self, index: int) -> typing.List[str]:
        """Installation(s) creditee(s) pour l'objet n°`index` : au hasard dans le pool (reproductible), ou la cible choisie."""
        fac = self.map.get("facilities", {})
        stock = fac.get("stock", {})
        if (self.settings.get("stock_mode") or fac.get("stock_mode", "random")) == "random":
            pool = self.settings.get("stock_pool") or fac.get("stock_pool") or list(stock)
            valid = sorted(p for p in pool if p in stock) or sorted(stock)
            return [random.Random(f"{self._progress_key()}:{index}").choice(valid)]
        return self.stock_targets()

    def _progress_key(self) -> str:
        # Archipelago 0.6 : `seed_name` reste None cote client, la vraie graine est dans `server_seed_name`.
        return f"{self.server_seed_name or self.seed_name}:{self.team}:{self.slot}"

    async def server_auth(self, password_requested: bool = False):
        if password_requested and not self.password:
            await super().server_auth(password_requested)
        await self.get_username()
        await self.send_connect()

    def on_package(self, cmd: str, args: dict):
        if cmd == "Connected":
            self.slot_data = args.get("slot_data", {})
            self.sent_at.clear()
            self.applied_index = _json_load(PROGRESS_FILE).get(self._progress_key(), 0)
            self.likes_state = _json_load(PROGRESS_FILE).get(self._progress_key() + ":likes") or {}
            self.likes_checks.clear()
            self.order_state = _json_load(PROGRESS_FILE).get(self._progress_key() + ":orders") or {}
            self.order_checks.clear()
            self.standard_state = _json_load(PROGRESS_FILE).get(self._progress_key() + ":standard") or {}
            self.standard_checks.clear()
            self.type_state = {k: (_json_load(PROGRESS_FILE).get(self._progress_key() + ":" + k) or {}) for k in ORDER_TYPES}
            self.type_checks = {k: set() for k in ORDER_TYPES}
            # checks retenus (option episode_gating) : ils ne sont pas rejoues par la detection, on les retrouve ici
            self.save_checks |= set(_json_load(PROGRESS_FILE).get(self._progress_key() + ":held") or [])
            if self.slot_data.get("death_link"):
                Utils.async_start(self.update_death_link(True))

    def on_deathlink(self, data: dict):
        super().on_deathlink(data)
        if self.slot_data.get("death_link"):
            self.death_pending = True

    def run_gui(self):
        from kvui import GameManager

        class DSManager(GameManager):
            logging_pairs = [("Client", "Archipelago")]
            base_title = "Archipelago Death Stranding Client"

        self.ui = DSManager(self)
        self.ui_task = asyncio.create_task(self.ui.async_run(), name="UI")

    def save_progress(self) -> None:
        data = _json_load(PROGRESS_FILE)
        data[self._progress_key()] = self.applied_index
        if self.likes_state:
            data[self._progress_key() + ":likes"] = self.likes_state
        if self.order_state:
            data[self._progress_key() + ":orders"] = self.order_state
        if self.standard_state:
            data[self._progress_key() + ":standard"] = self.standard_state
        for k, st in self.type_state.items():
            if st:
                data[self._progress_key() + ":" + k] = st
        data[self._progress_key() + ":held"] = sorted(self.held_codes)
        _json_save(PROGRESS_FILE, data)


def likes_baseline_ready(history: typing.List[int], in_game: bool, needed: int = 3) -> bool:
    """La base n'est fixee que si Sam est en jeu (vie lisible) et que le total est identique sur `needed` lectures
    consecutives : pendant un chargement, les compteurs valent brievement 0."""
    return in_game and len(history) >= needed and len(set(history[-needed:])) == 1


def likes_milestones(total: int, baseline: int, granted: int, step: int, count: int) -> typing.List[int]:
    """Codes des paliers de likes atteints. Gain = total - baseline - likes accordes par des objets AP (jamais negatif)."""
    from .locations import LIKES_BASE_ID
    if step <= 0 or count <= 0:
        return []
    gained = max(0, total - baseline - granted)
    return [LIKES_BASE_ID + n for n in range(1, count + 1) if n * step <= gained]


def order_progress_milestones(current: int, baseline: int, step: int, count: int) -> typing.List[int]:
    """Codes des paliers de progression des commandes atteints (gain = compteur - base, jamais negatif)."""
    from .locations import ORDER_PROGRESS_BASE_ID
    if step <= 0 or count <= 0:
        return []
    gained = max(0, current - baseline)
    return [ORDER_PROGRESS_BASE_ID + n for n in range(1, count + 1) if n * step <= gained]


def standard_progress_milestones(current: int, baseline: int, step: int, count: int) -> typing.List[int]:
    """Codes des paliers « Standard Orders » atteints (gain = compteur - base, jamais negatif)."""
    from .locations import STANDARD_ORDER_BASE_ID
    if step <= 0 or count <= 0:
        return []
    gained = max(0, current - baseline)
    return [STANDARD_ORDER_BASE_ID + n for n in range(1, count + 1) if n * step <= gained]


def order_type_milestones(base_id: int, current: int, baseline: int, step: int, count: int) -> typing.List[int]:
    """Codes des paliers atteints pour un type de commande (gain = compteur - base, jamais negatif)."""
    if step <= 0 or count <= 0:
        return []
    gained = max(0, current - baseline)
    return [base_id + n for n in range(1, count + 1) if n * step <= gained]


REPAIR_WINDOW = 300.0      # secondes : delai maximal entre la hausse du total et l'apparition de la cle « repair » (releves en jeu : 36 a 124 s, selon les dialogues)


def episodes_held(codes: typing.Iterable[int], received_episodes: typing.Set[int],
                  episode_of: typing.Optional[typing.Dict[int, int]] = None) -> typing.Set[int]:
    """Option « retenir les checks selon les acces d'episode » : parmi `codes`, ceux qu'il faut garder en attente.
    Meme regle que la logique de generation (create_regions) : un lieu de l'episode N (N >= 1) demande les objets Episode 1 a N Access.
    `received_episodes` = numeros des objets « Episode N Access » deja recus (objets de depart compris). Un lieu hors des episodes
    (likes, progression, commandes standard, bot, prologue) n'est jamais retenu."""
    episode_of = EPISODE_OF_LOCATION if episode_of is None else episode_of
    held = set()
    for code in codes:
        ep = episode_of.get(code)
        if ep and any(e not in received_episodes for e in range(1, ep + 1)):
            held.add(code)
    return held


def counters_changes(old: typing.Optional[typing.Dict[str, int]], new: typing.Dict[str, int]) -> typing.List[typing.Tuple[str, typing.Optional[int], typing.Optional[int]]]:
    """Differences entre deux photos de la table nommee : [(cle, ancienne valeur ou None si absente, nouvelle valeur ou None si disparue)], triees par cle.
    Sert au mode de recherche `/ds_counters watch` (lecture seule) ; sans photo precedente, rien n'est signale."""
    if old is None:
        return []
    out = [(k, old.get(k), v) for k, v in new.items() if old.get(k) != v]
    out += [(k, v, None) for k, v in old.items() if k not in new]
    return sorted(out)


def repair_progress(prev: typing.Optional[typing.Tuple[int, int, int]], cur: typing.Tuple[int, int, int], now: float,
                    marks: typing.Tuple[typing.Optional[float], typing.Optional[float]]) -> typing.Tuple[bool, typing.Tuple[typing.Optional[float], typing.Optional[float]]]:
    """Reconnait la commande de reparation n°62 dans la table de compteurs, d'un releve (nobot, total, repair) au suivant.
    Elle fait monter le total (sans toucher a « nobot ») et fait apparaitre la cle « repair » (0 -> 1) mais les deux n'arrivent pas ensemble : le jeu
    ecrit ses compteurs separement, la cle avec une quarantaine de secondes de retard (ou parfois avant). On note donc l'heure de chaque hausse et on conclut
    quand les deux ont eu lieu a moins de REPAIR_WINDOW secondes l'une de l'autre. `marks` = (heure de la hausse du total, heure de la hausse de repair) ;
    renvoie (reconnue, nouvelles marques). Tout autre ecart (commande ordinaire : « nobot » bouge ; autre sauvegarde chargee : repair saute) est ignore.
    Le titre du point de controle peut etre masque par une autre commande suivie (un bot, par exemple) ; ces compteurs, eux, ne mentent pas."""
    t_total, t_rep = marks
    if prev is not None and cur[0] == prev[0]:
        if cur[1] > prev[1]:
            t_total = now
        if cur[2] == prev[2] + 1:
            t_rep = now
    if t_total is not None and t_rep is not None and now - t_total <= REPAIR_WINDOW and now - t_rep <= REPAIR_WINDOW:
        return True, (None, None)
    return False, (t_total, t_rep)


# Rythme des recherches COMPLETES de titres en memoire (une recherche complete lit tout le tas du jeu : ~55 s). Avant, sans titre trouve (fin du jeu,
# sauvegarde sans point de controle recent), une nouvelle recherche partait 60 s apres le DEBUT de la precedente, soit ~90 % du temps a lire la memoire.
# Maintenant : l'attente se compte depuis la FIN de la derniere recherche et double a chaque recherche vide (60, 120, 240, 480, puis 600 s), SAUF pendant
# TITLE_ALERT_SECONDS apres une variation d'un compteur de livraisons (cadence d'avant). Releve en jeu 19/11 : le titre d'une commande principale n'apparait
# qu'au premier enregistrement du jeu, 148 a 225 s apres la hausse des compteurs (64, 65, 67) ; une alerte plus courte retarderait la detection.
TITLE_ALERT_SECONDS = 360.0
TITLE_IDLE_BASE = 60.0
TITLE_IDLE_MAX = 600.0
TITLE_RESCAN_SECONDS = 240.0


def title_idle_wait(empty_streak: int) -> float:
    """Attente (apres la fin de la derniere recherche complete) avant d'en refaire une, quand les `empty_streak` dernieres n'ont rien trouve."""
    return min(TITLE_IDLE_MAX, TITLE_IDLE_BASE * 2 ** max(0, empty_streak - 1))


def title_scan_due(now: float, zones: typing.Optional[list], last_start: float, last_end: float, empty_streak: int, force: bool, burst_until: float,
                   alert_until: float = 0.0) -> bool:
    """Faut-il lancer une recherche COMPLETE de titres maintenant ? (`zones` : None = jamais fait, [] = rien trouve, sinon zones surveillees.)"""
    if zones is None or force or now < burst_until:
        return True
    if not zones:
        if now < alert_until:                  # peu apres une livraison : le titre peut arriver d'une minute a l'autre, on relit en continu comme avant
            return now - last_start >= TITLE_IDLE_BASE          # exactement le rythme d'avant (60 s apres le DEBUT de la precedente)
        return now - last_end >= title_idle_wait(empty_streak)
    return now - last_start >= TITLE_RESCAN_SECONDS


# Retenue de la confirmation « livraison de bot » : le total monte avant « nobot » pendant la fin d'une commande ordinaire (cinematique, ecran de resultat,
# dialogues) et reste en avance de 20 a 100 s selon le rythme du joueur, parfois plus que les 90 s exigees pour croire a un bot. Deux signes (releves en jeu,
# 18/11) permettent de savoir que ce n'est PAS un bot, et on retient alors la confirmation (jamais de check perdu : on retarde seulement) :
#  - cle de likes cumules +1000 ou plus au meme moment que la hausse du total : commande speciale (62 : +1000 ; 70 : +101 000) ; la retenue dure jusqu'a
#    l'apparition de la cle « repair » (62) ou BOT_HOLD_SECONDS ;
#  - cle 4c615b8a... a 1 : livraison d'une commande standard en cours (0 -> 1 a la cinematique, 1 -> 0 a la sortie de l'ecran de resultat).
BOT_HOLD_SECONDS = 300.0
BOT_HOLD_LIKES_JUMP = 1000
BOT_HOLD_COINCIDENCE = 10.0          # ecart maximal (s) entre la hausse du total et le saut de likes (ou la creation d'une cle)
BOT_HOLD_MAX_NEW_KEYS = 12           # au-dela, c'est un chargement de sauvegarde (des dizaines de cles apparaissent d'un coup), pas une fin de commande
LIKES_STAT_KEY = "26adb4dfac794d7dbc80aa23969c7652"
DELIVERY_FLAG_KEY = "4c615b8a055c41ad89d8490292abbae7"


def bot_hold_step(state: dict, now: float, total: typing.Optional[int], repair: typing.Optional[int], likes: typing.Optional[int],
                  flag: typing.Optional[int], new_keys: int = 0, bot: typing.Optional[int] = None) -> bool:
    """Met a jour `state` (dict conserve d'un releve au suivant) avec un releve (total, repair, likes cumules, drapeau de livraison, nombre de cles creees depuis
    le releve precedent hors drapeau de livraison, valeur brute du compteur de bot) et renvoie True si la confirmation d'une livraison de bot doit etre retenue.
    Les valeurs None (illisibles) sont ignorees.
    Une hausse du total accompagnee (a 10 s pres) d'un saut de likes OU de la creation d'une cle est une fin de commande principale / speciale : elle est
    retenue BOT_HOLD_SECONDS et enregistree comme « candidate » pour `bot_absorb` (releve en jeu 19/11 : 62, 63, 64, 65, 67, 68 creent une cle avec le total ;
    4 bots et 2 marchandises perdues non)."""
    if total is not None and state.get("total") is not None and total > state["total"]:
        state["total_at"] = now
        state["bot_pre"] = state.get("bot")                    # valeur du bot juste avant cette hausse
    if likes is not None and state.get("likes") is not None and likes - state["likes"] >= BOT_HOLD_LIKES_JUMP:
        state["likes_at"] = now
    if 0 < new_keys <= BOT_HOLD_MAX_NEW_KEYS:
        state["key_at"] = now
    if repair is not None and state.get("repair") is not None and repair > state["repair"]:
        state["until"] = 0.0                                   # la 62 est terminee : le compteur de bot est revenu a sa valeur
        state["cand"] = None
    ta = state.get("total_at")
    for tag in ("likes_at", "key_at"):
        other = state.get(tag)
        if ta is not None and other is not None and abs(ta - other) <= BOT_HOLD_COINCIDENCE and state.get("paired_" + tag) != (ta, other):
            state["paired_" + tag] = (ta, other)
            state["until"] = max(state.get("until", 0.0), max(ta, other) + BOT_HOLD_SECONDS)
            if state.get("cand_ta") != ta and state.get("bot_pre") is not None:       # une seule candidate par hausse du total
                state["cand_ta"] = ta
                cand = state.get("cand") or {"pre": state["bot_pre"], "n": 0}
                cand["n"] += 1
                state["cand"] = cand
    for k, v in (("total", total), ("repair", repair), ("likes", likes), ("bot", bot)):
        if v is not None:
            state[k] = v
    if flag == 1:
        if state.get("flag_since") is None:
            state["flag_since"] = now
    elif flag is not None:
        state["flag_since"] = None
    flag_on = state.get("flag_since") is not None and now - state["flag_since"] <= BOT_HOLD_SECONDS
    return now < state.get("until", 0.0) or flag_on


def bot_absorb(state: dict, now: float, held: bool, flag: typing.Optional[int], bot: int, baseline: int) -> int:
    """Nombre de hausses du compteur de bot a ecarter (decalage de la base) : fin de retenue (delai ecoule) d'une ou plusieurs hausses « candidates » (fins de
    commande principale / speciale, voir `bot_hold_step`) restees sans compensation (`nobot` ou `repair` ne les a pas annulees) et visibles comme un gain.
    Rien tant qu'une livraison standard est en cours (drapeau a 1 : `nobot` va suivre) ; 0 si le gain est nul (un creux du compteur absorbe deja la hausse)."""
    cand = state.get("cand")
    if not cand or held or flag == 1:
        return 0
    state["cand"] = None
    excess, gain = bot - cand["pre"], bot - baseline
    return max(0, min(cand["n"], excess, gain))


# Marqueurs de fin de commande principale : cles de la table creees (absent -> 0 ou 1) dans le meme releve que la hausse du total (a 10 s pres) a la fin de CHAQUE
# commande. Identiques sur deux courses completes (19/11, 15:58 et 17:12, meme jeu) pour 63, 64, 65, 67, 68 ; 61 / 62 / 70 : releves des 18-19/11 (62 : 3 fois).
ORDER_MARKER_KEYS: typing.Dict[int, typing.Tuple[str, ...]] = {
    61: ("4374086b9e9b3ee88b4d803290017d75",),
    62: ("f496b86a3afa3f29ad6f18bc97c8045c",),
    63: ("d9574e651dcd36ed87180a9f278628e0",),
    64: ("4e96248a5d2e34fb8a57b7e6db2ad2ab",),
    65: ("d4a6a0e4aca4367b99d3d3e22ab040ed",),
    67: ("6f1785696af642fe8a24ca61bf9cc800",),
    68: ("6134f3c4104f33cf8afbd18145c9972e", "811181711eb83dfeab21291cc2e20b14", "d32463f383fa38a095d99a3f4b127210"),
    70: ("88a3ea04c3823061bcaebc35392411aa", "cd8735b9fac33b97a60a4025de0f97d3"),
}


def marker_orders(created: typing.Dict[str, float], total_at: typing.Optional[float], window: float = 10.0,
                  markers: typing.Optional[typing.Dict[int, typing.Tuple[str, ...]]] = None) -> typing.Set[int]:
    """Commandes principales dont TOUTES les cles marqueurs ont ete creees (`created` : cle -> heure) a `window` s ou moins de la derniere hausse du total."""
    if total_at is None:
        return set()
    markers = ORDER_MARKER_KEYS if markers is None else markers
    return {n for n, keys in markers.items() if keys and all(k in created and abs(created[k] - total_at) <= window for k in keys)}


SIGNATURE_GRACE = 15.0          # une fin de commande plus recente que cela n'est pas encore « orpheline » (le titre n'est lu que quelques secondes apres l'ecriture ; releve 19/11 : 48 a 77 s apres la fin)


def unmatched_signatures(sigs: typing.List[float], now: float, n_new: int, from_counter: bool = False) -> typing.Tuple[typing.List[float], int]:
    """Fins de commande reconnues dans les compteurs (`sigs`, heures) et `n_new` commandes principales qui viennent d'etre identifiees (titre en memoire,
    sauvegarde, compteur). Renvoie (signatures conservees, nombre de fins de commande restees sans identification). Un titre ne designe que la DERNIERE commande
    terminee avant l'enregistrement : les fins plus anciennes (de plus de SIGNATURE_GRACE s) qui restent apres avoir associe les `n_new` plus recentes n'ont
    jamais ete identifiees (releve 19/11 : la 63, terminee avant la 64 sans enregistrement entre les deux). Une identification par compteur (62) retire simplement
    la signature correspondante."""
    if n_new <= 0:
        return sigs, 0
    if from_counter:
        return sigs[:max(0, len(sigs) - n_new)], 0
    old = sorted(t for t in sigs if now - t >= SIGNATURE_GRACE)
    recent = [t for t in sigs if now - t < SIGNATURE_GRACE]
    left = old[:max(0, len(old) - n_new)]
    return recent, len(left)


def apply_trap(memory, spec: dict) -> typing.Tuple[str, typing.Optional[typing.Tuple[float, float]]]:
    """Applique un piege decrit dans memory_map["traps"]. Renvoie ("ok", (avant, apres)), ("wait", None) si le joueur
    n'est pas lisible (menu, chargement) ou ("fail", None) si la valeur visee est incoherente (piege abandonne)."""
    if not memory.player_ready():
        return "wait", None
    delta = float(spec.get("delta", 0.0))
    floor, ceil = spec.get("floor"), spec.get("ceil")
    if "of" in spec:
        ref = memory.read_player_field(spec["of"])
        if ref is None or ref <= 0:
            return "fail", None
        if "frac" in spec:
            delta = float(spec["frac"]) * ref
        if "floor_frac" in spec:
            floor = float(spec["floor_frac"]) * ref
        if "ceil_frac" in spec:
            ceil = float(spec["ceil_frac"]) * ref
    res = memory.adjust_player(spec["field"], delta, floor, ceil)
    return ("ok", res) if res else ("fail", None)


def apply_effects(memory, spec) -> typing.Tuple[str, typing.List[typing.Tuple[str, typing.Optional[typing.Tuple[float, float]]]]]:
    """Applique un effet (dict) ou plusieurs (liste de dicts). ("wait", []) si le joueur est illisible ; sinon ("ok", [(champ, (avant, apres))...])
    si au moins un effet a ete applique, ("fail", []) sinon."""
    specs = spec if isinstance(spec, list) else [spec]
    if not memory.player_ready():
        return "wait", []
    done = []
    for s in specs:
        st, res = apply_trap(memory, s)
        if st == "ok":
            done.append((s["field"], res))
    return ("ok", done) if done else ("fail", [])


def death_step(vitals: typing.Optional[typing.Tuple[float, float]], alive_polls: int, pending: bool,
               now: float, suppress_until: float) -> typing.Tuple[typing.Optional[str], int, bool, float]:
    """Logique DeathLink pure. Renvoie (action, alive_polls, pending, suppress_until), action = "kill" | "send" | None.

    - kill : un DeathLink recu attend et le joueur est vivant -> on le tue, et on ignore sa mort pendant 20 s.
    - send : le joueur etait vivant sur 2 lectures consecutives puis sa vie tombe a 0 -> on previent les autres (30 s de repit).
    """
    if vitals is None:                       # menu, chargement : on ne decide rien
        return None, 0, pending, suppress_until
    hp, _ = vitals
    if hp > 0.5:
        if pending:
            return "kill", 0, False, now + 20.0
        return None, alive_polls + 1, pending, suppress_until
    # mort en cours
    if alive_polls >= 2 and now >= suppress_until:
        return "send", 0, False, now + 30.0
    return None, 0, False, suppress_until   # deja mort (ou mort provoquee) : un DeathLink en attente est caduc


async def _game_watcher_loop(ctx: DeathStrandingContext) -> None:
    grants = ctx.map.get("item_grants", {})
    loop = asyncio.get_running_loop()
    last_save_poll = 0.0
    last_likes_poll = 0.0
    last_order_poll = 0.0
    last_standard_poll = 0.0
    last_types_poll = 0.0
    last_watch_poll = 0.0
    last_table_scan = -1e9
    last_title_poll, last_title_full, title_running = 0.0, -1e9, False
    table_scan_running = False
    while not ctx.exit_event.is_set():
        await asyncio.sleep(0.5)
        if ctx.slot is None:
            continue

        if not ctx.backend.attached():
            ctx.backend.attach()

        # 1. Checks : commandes terminees (sauvegardes) + manuels
        if loop.time() - last_save_poll >= SAVE_POLL_SECONDS:
            last_save_poll = loop.time()
            try:
                done = await loop.run_in_executor(None, ctx.saves.poll)
            except Exception as e:  # le suivi des sauvegardes ne doit jamais faire tomber le client
                logger.warning(f"Surveillance des sauvegardes : {e}")
                done = []
            ctx.register_completed_orders(done)
        # 1b. Commandes terminees lues directement en memoire (titre du point de controle) : pas de dechiffrement
        if ctx.settings.get("memory_titles", True) and not title_running and ctx.backend.attached() \
                and loop.time() - last_title_poll >= 4.0:
            last_title_poll = loop.time()
            # sans zone connue : nouvel essai complet de plus en plus espace (1 a 10 min apres la FIN du precedent) ; avec zone : rescan complet toutes les 4 min
            # au cas ou le jeu ecrive ailleurs ; tout de suite quand un compteur de livraisons bouge (force / rafale)
            full = title_scan_due(loop.time(), ctx.title_zones, last_title_full, ctx.title_full_end, ctx.title_empty_streak, ctx.title_force_full, ctx.title_burst_until, ctx.title_alert_until)
            ctx.title_force_full = False
            if full:
                last_title_full = loop.time()
                if ctx.title_zones is None:
                    logger.info("Commandes principales : recherche en memoire (jusqu'a 1 min la premiere fois)...")
            title_running = True

            async def _titles(full: bool = full) -> None:
                nonlocal title_running
                try:
                    t0 = loop.time()
                    zones = None if full else ctx.title_zones
                    used_hint = False
                    if full and not ctx.title_hint_failed:    # d'abord la zone memorisee de la derniere session, bien plus rapide
                        zones = ctx.hint_windows()
                        used_hint = zones is not None
                    titles, new_zones = await loop.run_in_executor(None, ctx.memory.scan_titles, ctx.saves.words, zones, 600.0, lambda msg: loop.call_soon_threadsafe(logger.debug, msg))
                    if full:
                        ctx.title_zones = new_zones
                        if used_hint and not new_zones:
                            ctx.title_hint_failed = True     # la zone memorisee ne contient plus rien : recherche complete tout de suite
                            ctx.title_force_full = True
                            return
                        if not used_hint and new_zones:
                            ctx.title_hint_failed = False
                        if new_zones:
                            ctx.title_empty_streak = 0
                        elif loop.time() >= ctx.title_burst_until:      # les recherches vides de la rafale (apres une livraison) ne comptent pas
                            ctx.title_empty_streak += 1
                        if new_zones:
                            ctx.update_hint([z[0] for z in new_zones] + [z[0] + z[1] for z in new_zones], margin=256 << 20)
                        if ctx.title_baselined:      # nouvelle recherche complete : ce qui est apparu entre-temps compte
                            ctx.register_completed_orders([n for n, _ in sorted(titles - ctx.title_seen)], "memoire")
                        ctx.title_seen |= set(titles)
                        ctx.title_baselined = True
                        if not new_zones:
                            if not ctx.title_none_logged:
                                ctx.title_none_logged = True
                                logger.info(f"Commandes principales : aucun titre de sauvegarde en memoire pour l'instant (recherche en "
                                            f"{loop.time() - t0:.0f} s) : nouvel essai espace (1 a 10 min) et immediat a chaque livraison.")
                        else:
                            (logger.debug if ctx.title_active_logged else logger.info)(
                                f"Commandes principales : lecture en memoire active ({sum(z[1] for z in new_zones) >> 20} Mo surveilles, "
                                f"recherche en {loop.time() - t0:.0f} s).")
                            ctx.title_active_logged = True
                    else:
                        fresh = sorted(t for t in titles if t not in ctx.title_seen)
                        ctx.title_seen |= set(titles)
                        # les zones suivent les points de controle les plus recents ; si on n'en voit plus, on refait une recherche complete
                        ctx.title_zones = new_zones
                        if fresh:
                            ctx.register_completed_orders([n for n, _ in fresh], "memoire")
                except Exception as e:
                    logger.warning(f"Lecture des titres en memoire : {e}")
                finally:
                    if full:
                        ctx.title_full_end = loop.time()
                    title_running = False
            Utils.async_start(_titles())
        released = ctx.save_checks
        if ctx.slot_data.get("episode_gating"):
            received = {int(m.group(1)) for m in (re.fullmatch(r"Episode (\d+) Access", ctx.item_names.lookup_in_game(i.item)) for i in ctx.items_received) if m}
            received |= {int(m.group(1)) for m in (re.fullmatch(r"Episode (\d+) Access", n) for n in ctx.slot_data.get("starting_items", [])) if m}
            held = episodes_held(ctx.save_checks - ctx.checked_locations, received)
            if held != ctx.held_codes:
                for code in sorted(held - ctx.held_codes - ctx.held_logged):
                    ep = EPISODE_OF_LOCATION[code]
                    missing = [e for e in range(1, ep + 1) if e not in received]
                    logger.info(f"Check retenu (objets manquants : {', '.join(f'Episode {e} Access' for e in missing)}) : {ctx.location_names.lookup_in_game(code)}")
                    ctx.held_logged.add(code)
                for code in sorted(ctx.held_codes - held):
                    logger.info(f"Check libere : {ctx.location_names.lookup_in_game(code)}")
                ctx.held_codes = held
                ctx.save_progress()
            released = ctx.save_checks - held
        to_send, unknown = plan_location_sends(ctx.manual_checks | released | ctx.likes_checks | ctx.order_checks | ctx.standard_checks | ctx.type_checks["bot"], ctx.checked_locations,
                                               ctx.server_locations, ctx.sent_at, loop.time())
        for code in unknown:
            if code not in ctx.warned_unknown:
                ctx.warned_unknown.add(code)
                logger.warning(f"Le lieu {code} n'existe pas dans la partie hebergee : la seed a probablement ete generee "
                               "avec une autre version de l'APWorld. Regenere et relance la partie.")
        if to_send:
            await ctx.send_msgs([{"cmd": "LocationChecks", "locations": to_send}])
            for code in to_send:
                ctx.sent_at[code] = loop.time()

        # 2. Items recus : l'index n'avance que si l'item a bien ete applique
        while ctx.applied_index < len(ctx.items_received):
            item = ctx.items_received[ctx.applied_index]
            name = ctx.item_names.lookup_in_game(item.item)
            grant = grants.get(name)
            if isinstance(grant, dict) and "stock" in grant:
                targets = ctx.stock_targets_for(ctx.applied_index)
                if ctx.memory.stock_base() is None:
                    if ctx._warned_item != ctx.applied_index:
                        logger.info(f"En attente du jeu pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                results = [ctx.memory.add_stock(f, grant["stock"], int(grant["amount"])) for f in targets]
                logger.info(f"Objet applique : {name} (+{grant['amount']} {grant['stock']} -> "
                            + ", ".join(f"{f} : {r}" for f, r in zip(targets, results)) + ")")
            elif isinstance(grant, dict) and "likes" in grant:
                if int(ctx.slot_data.get("likes_checks", 0)) > 0 and "baseline" not in ctx.likes_state:
                    if ctx._warned_item != ctx.applied_index:   # la base des paliers doit etre fixee avant d'ajouter des likes
                        logger.info(f"En attente de la base des paliers de likes pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                new_likes = ctx.memory.add_likes(grant["likes"], int(grant["amount"]))
                if new_likes is None:
                    if ctx._warned_item != ctx.applied_index:
                        logger.info(f"En attente du jeu pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                ctx.likes_state["granted"] = int(ctx.likes_state.get("granted", 0)) + int(grant["amount"])
                logger.info(f"Objet applique : {name} ({grant['amount']:+d} likes {grant['likes']} -> {new_likes})")
            elif name in ctx.map.get("traps", {}) or name in ctx.map.get("boosts", {}):
                is_trap = name in ctx.map.get("traps", {})
                status, done = apply_effects(ctx.memory, (ctx.map["traps"] if is_trap else ctx.map["boosts"])[name])
                if status == "wait":
                    if ctx._warned_item != ctx.applied_index:
                        logger.info(f"En attente du jeu pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                label = "Piege" if is_trap else "Effet"
                if status == "ok":
                    logger.info(f"{label} applique : {name} (" + ", ".join(f"{f} : {r[0]:.0f} -> {r[1]:.0f}" for f, r in done) + ")")
                else:
                    logger.warning(f"{label} ignore : {name} (valeur du jeu incoherente, voir /ds_effect)")
            elif isinstance(grant, dict):
                new_qty = ctx.memory.add_resource(grant["resource"], int(grant["amount"]))
                if new_qty is None:
                    if ctx._warned_item != ctx.applied_index:
                        logger.info(f"En attente du jeu pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                logger.info(f"Objet applique : {name} ({grant['amount']:+d} {grant['resource']} -> {new_qty})")
            else:
                logger.info(f"Objet recu (sans effet en jeu pour l'instant) : {name}")
            ctx.applied_index += 1
            ctx.save_progress()

        # 2b. DeathLink : mort recue -> tue le joueur ; mort du joueur -> previent les autres
        if ctx.slot_data.get("death_link"):
            action, ctx.alive_polls, ctx.death_pending, ctx.death_suppress_until = death_step(
                ctx.memory.read_vitals(), ctx.alive_polls, ctx.death_pending, loop.time(), ctx.death_suppress_until)
            if action == "kill":
                if ctx.memory.kill_player():
                    logger.info("DeathLink recu : Sam est mort.")
                else:
                    ctx.death_pending = True
            elif action == "send":
                await ctx.send_death(f"{ctx.player_names.get(ctx.slot, 'Sam')} est mort dans Death Stranding.")

        # 2c. Paliers de likes (optionnels) : gain organique = total - base - likes accordes par des objets
        step, count = int(ctx.slot_data.get("likes_step", 0)), int(ctx.slot_data.get("likes_checks", 0))
        if count > 0 and step > 0 and loop.time() - last_likes_poll >= SAVE_POLL_SECONDS:
            last_likes_poll = loop.time()
            lk = ctx.memory.read_likes()
            if lk is not None:
                total = lk[0] + lk[1]
                ctx.likes_history = (ctx.likes_history + [total])[-5:]
                if "baseline" not in ctx.likes_state:
                    if not likes_baseline_ready(ctx.likes_history, ctx.memory.read_vitals() is not None):
                        continue_likes = False
                    else:
                        ctx.likes_state.update(baseline=total, granted=0)
                        ctx.save_progress()
                        logger.info(f"Paliers de likes : base fixee a {total} likes (palier = {step} likes gagnes).")
                        continue_likes = True
                else:
                    continue_likes = True
                new = set() if not continue_likes else set(likes_milestones(total, int(ctx.likes_state["baseline"]), int(ctx.likes_state.get("granted", 0)), step, count))
                for code in sorted(new - ctx.likes_checks):
                    logger.info(f"Palier de likes atteint : {code - 7_771_000} ({(code - 7_771_000) * step} likes gagnes)")
                ctx.likes_checks |= new

        # 2d. Progression des commandes (optionnelle) : compteur d'etapes de commande ([module+0x7BFA148]+0x168), gain depuis la base
        ostep, ocount = int(ctx.slot_data.get("order_step", 0)), int(ctx.slot_data.get("order_checks", 0))
        if ocount > 0 and ostep > 0 and loop.time() - last_order_poll >= SAVE_POLL_SECONDS:
            last_order_poll = loop.time()
            cur = ctx.memory.read_order_progress()
            if cur is not None:
                ctx.order_history = (ctx.order_history + [cur])[-5:]
                ready = True
                if "baseline" not in ctx.order_state:
                    if likes_baseline_ready(ctx.order_history, ctx.memory.read_vitals() is not None):
                        ctx.order_state["baseline"] = cur
                        ctx.save_progress()
                        logger.info(f"Progression des commandes : base fixee a {cur} (palier = {ostep} etapes de commande).")
                    else:
                        ready = False
                if ready:
                    new = set(order_progress_milestones(cur, int(ctx.order_state["baseline"]), ostep, ocount))
                    for code in sorted(new - ctx.order_checks):
                        logger.info(f"Palier de progression des commandes atteint : {code - ORDER_PROGRESS_BASE_ID} "
                                    f"({(code - ORDER_PROGRESS_BASE_ID) * ostep} etapes)")
                    ctx.order_checks |= new

        # 2e. Commandes standard livrees (optionnel) : cle 17 de la table de statistiques, gain depuis la base
        sstep, scount = int(ctx.slot_data.get("standard_step", 0)), int(ctx.slot_data.get("standard_checks", 0))
        if scount > 0 and sstep > 0 and loop.time() - last_standard_poll >= SAVE_POLL_SECONDS:
            last_standard_poll = loop.time()
            cur = ctx.memory.read_standard_orders()
            if cur is not None:
                ctx.standard_history = (ctx.standard_history + [cur])[-5:]
                ready = True
                if "baseline" not in ctx.standard_state:
                    if likes_baseline_ready(ctx.standard_history, ctx.memory.read_vitals() is not None):
                        ctx.standard_state["baseline"] = cur
                        ctx.save_progress()
                        logger.info(f"Commandes standard : base fixee a {cur} (palier = {sstep} livraison(s)).")
                    else:
                        ready = False
                if ready:
                    new = set(standard_progress_milestones(cur, int(ctx.standard_state["baseline"]), sstep, scount))
                    for code in sorted(new - ctx.standard_checks):
                        logger.info(f"Palier de commandes standard atteint : {code - STANDARD_ORDER_BASE_ID} "
                                    f"({(code - STANDARD_ORDER_BASE_ID) * sstep} livraison(s))")
                    ctx.standard_checks |= new

        # 2f. Commandes principales et de bot livrees (optionnel) : compteurs nommes du jeu, gain depuis la base
        wanted = {k: (int(ctx.slot_data.get(f"{v[1]}_step", 0)), int(ctx.slot_data.get(f"{v[1]}_checks", 0))) for k, v in ORDER_TYPES.items()}
        if any(step > 0 and cnt > 0 for step, cnt in wanted.values()) and loop.time() - last_types_poll >= SAVE_POLL_SECONDS:
            last_types_poll = loop.time()
            cur = ctx.memory.read_order_types()
            if cur is None and not table_scan_running and ctx.memory.read_standard_orders() is not None \
                    and loop.time() - last_table_scan >= 120.0:
                # les chaines de pointeurs ne marchent plus (redemarrage, autre sauvegarde) : recherche de la table par sa signature, en arriere-plan
                last_table_scan = loop.time()
                table_scan_running = True
                logger.info("Compteurs de commandes : recherche de la table en memoire (jusqu'a quelques minutes)...")

                async def _scan() -> None:
                    nonlocal table_scan_running
                    try:
                        hint = ctx.hint_windows()
                        base = await loop.run_in_executor(None, ctx.memory.scan_named_table, 240.0, None, hint) if hint else None
                        if base is None:
                            base = await loop.run_in_executor(None, ctx.memory.scan_named_table)
                        if base:
                            ctx.update_hint([base])
                        logger.info(f"Compteurs de commandes : table retrouvee (0x{base:X})." if base else
                                    "Compteurs de commandes : table introuvable (sera retentee).")
                    except Exception as e:
                        logger.warning(f"Recherche de la table de compteurs : {e}")
                    finally:
                        table_scan_running = False
                Utils.async_start(_scan())
            if cur is not None and not ctx.types_source_logged:
                ctx.types_source_logged = True
                logger.debug(f"Compteurs de commandes : table lue [{ctx.memory.named_counters_report()[1]}].")
            if cur is not None:
                snap = (cur["standard"], cur["main"], cur["bot"])           # valeurs brutes : servent a juger de la stabilite
                if ctx.title_last_main is not None and (cur["main"], cur["bot"]) != ctx.title_last_main:
                    ctx.title_force_full = True      # un compteur de livraisons a bouge : on relit les titres tout de suite
                    ctx.title_empty_streak = 0       # et on repart sur l'attente courte (1 min) apres la rafale
                    ctx.title_alert_until = loop.time() + TITLE_ALERT_SECONDS      # le titre n'arrive qu'au prochain enregistrement : 2,5 a 4 min plus tard
                    ctx.title_burst_until = loop.time() + 90.0      # puis toutes les 4 s pendant 90 s : le jeu ecrit son point de controle un peu apres
                ctx.title_last_main = (cur["main"], cur["bot"])
                named = ctx.memory.read_named_counters()
                raw_now = (named.get("nobot"), named.get("total"), named.get("repair"), cur["standard"]) if named else None
                if raw_now != ctx.raw_logged:
                    if ctx.raw_logged is not None and raw_now is not None:
                        logger.debug(f"[{time.strftime('%H:%M:%S')}] Compteurs bruts : sans bot {ctx.raw_logged[0]} -> {raw_now[0]}, total {ctx.raw_logged[1]} -> {raw_now[1]}, "
                                    f"reparation {ctx.raw_logged[2]} -> {raw_now[2]}, standard {ctx.raw_logged[3]} -> {raw_now[3]}")
                    ctx.raw_logged = raw_now
                if named and "repair" in named:
                    sig = (named["nobot"], named["total"], named["repair"])
                    if sig != ctx.repair_last:      # releves bruts, sans attendre qu'ils soient stables : la 62 peut etre livree juste apres le lancement du client
                        done, ctx.repair_marks = repair_progress(ctx.repair_last, sig, time.time(), ctx.repair_marks)
                        ctx.repair_last = sig
                        if done:
                            ctx.register_completed_orders([62], "compteur")
                ctx.type_history = (ctx.type_history + [snap])[-60:]
                bot_held = False
                if named:
                    try:
                        table = ctx.memory.dump_named_table() or {}
                    except Exception:
                        table = {}
                    keys_now = set(table) if table else None
                    new_names = (keys_now - ctx.bot_hold_keys - {DELIVERY_FLAG_KEY}) if keys_now is not None and ctx.bot_hold_keys is not None else set()
                    new_keys = len(new_names)
                    if 0 < new_keys <= BOT_HOLD_MAX_NEW_KEYS:           # (au-dela : chargement de sauvegarde)
                        for k in new_names:
                            ctx.created_keys[k] = loop.time()
                    ctx.created_keys = {k: t for k, t in ctx.created_keys.items() if loop.time() - t <= 120.0}
                    if keys_now is not None:
                        ctx.bot_hold_keys = keys_now
                    delivery_flag = table.get(DELIVERY_FLAG_KEY, 0) if table else None
                    bot_held = bot_hold_step(ctx.bot_hold_state, loop.time(), named.get("total"), named.get("repair", 0),
                                             table.get(LIKES_STAT_KEY), delivery_flag, new_keys, cur["bot"])
                    sig_ta = ctx.bot_hold_state.get("cand_ta")
                    if sig_ta is not None and sig_ta != ctx.sig_last_ta:
                        ctx.sig_last_ta = sig_ta
                        ctx.sig_times.append(time.time())      # fin de commande principale / speciale reperee dans les compteurs
                    # identification par les cles marqueurs : la commande est connue tout de suite, sans attendre le titre du prochain enregistrement
                    for n in sorted(marker_orders(ctx.created_keys, ctx.bot_hold_state.get("total_at"))):
                        if (n, ctx.bot_hold_state.get("total_at")) not in ctx.marker_done:
                            ctx.marker_done.add((n, ctx.bot_hold_state.get("total_at")))
                            ctx.register_completed_orders([n], "marqueur")
                    bot_state = ctx.type_state.get("bot", {})
                    if "baseline" in bot_state:
                        shift = bot_absorb(ctx.bot_hold_state, loop.time(), bot_held, delivery_flag, cur["bot"], int(bot_state["baseline"]))
                        if shift:
                            bot_state["baseline"] = int(bot_state["baseline"]) + shift
                            ctx.save_progress()
                            logger.info(f"Fin de commande principale ou speciale reconnue dans les compteurs (cle creee avec le total, pas de livraison de bot) : "
                                        f"{shift} hausse(s) du compteur de bot ecartee(s) (base {bot_state['baseline'] - shift} -> {bot_state['baseline']}).")
                    if bot_held and not ctx.bot_hold_logged:
                        ctx.bot_hold_logged = True
                        logger.debug("Livraison de bot : confirmation retenue (fin de commande ordinaire ou speciale en cours).")
                    elif not bot_held:
                        ctx.bot_hold_logged = False
                # le jeu ecrit les compteurs separement et parfois a plusieurs secondes d'intervalle (le compteur total peut avancer seul
                # un moment) : on ne tient compte d'une variation que si les trois valeurs sont restees identiques ~16 s
                stable = len(ctx.type_history) >= 8 and len(set(ctx.type_history[-8:])) == 1
                # pour le bot, le compteur "total" peut rester en avance pendant toute la livraison d'une commande principale :
                # on exige ~90 s sans aucun changement avant de croire a une livraison de bot
                stable_bot = len(ctx.type_history) >= 45 and len(set(ctx.type_history[-45:])) == 1
                # coherence : un compteur de livraisons ne diminue pas. Pendant une livraison, le compteur "total" peut avancer avant le compteur
                # "sans bot" (principales = sans bot - standard baisse, bot = total - sans bot monte) : on attend que le jeu ait fini d'ecrire.
                consistent = True
                if stable:
                    prev = getattr(ctx, "type_prev", None)
                    if prev is not None and (snap[1] < prev[1] or snap[2] < prev[2]) and getattr(ctx, "type_incoherent", 0) < 30:
                        consistent = False
                        ctx.type_incoherent = getattr(ctx, "type_incoherent", 0) + 1
                    else:
                        ctx.type_prev, ctx.type_incoherent = snap, 0
                in_game = ctx.memory.read_vitals() is not None
                for kind, (step, cnt) in wanted.items():
                    if step <= 0 or cnt <= 0:
                        continue
                    state = ctx.type_state.setdefault(kind, {})
                    if "baseline" not in state:
                        if likes_baseline_ready(ctx.type_history, in_game):
                            state["baseline"] = cur[kind]
                            ctx.save_progress()
                            logger.info(f"{ORDER_TYPES[kind][2].capitalize()} : base fixee a {cur[kind]} (palier = {step} livraison(s)).")
                        continue
                    if not (stable_bot if kind == "bot" else stable) or not consistent or (kind == "bot" and bot_held):
                        continue
                    base_id = ORDER_TYPES[kind][0]
                    new = set(order_type_milestones(base_id, cur[kind], int(state["baseline"]), step, cnt))
                    for code in sorted(new - ctx.type_checks[kind]):
                        logger.info(f"Palier de {ORDER_TYPES[kind][2]} atteint : {code - base_id} ({(code - base_id) * step} livraison(s))")
                    ctx.type_checks[kind] |= new

        # 2g. Mode recherche (/ds_counters watch) : ecrit chaque changement de la table nommee (lecture seule, coupe par defaut)
        if ctx.counters_watch and loop.time() - last_watch_poll >= 5.0:
            last_watch_poll = loop.time()
            dump = ctx.memory.dump_named_table()
            if dump is not None:
                changes = counters_changes(ctx.counters_watch_last, dump)
                ctx.counters_watch_last = dump
                if changes:
                    known = {bytes.fromhex(c["key"]).hex(): n for n, c in ctx.map.get("named_counters", {}).get("counters", {}).items()}
                    logger.info(f"[{time.strftime('%H:%M:%S')}] {len(changes)} compteur(s) modifie(s) :")
                    for k, a, b in changes[:30]:
                        delta = f" ({b - a:+d})" if a is not None and b is not None else ""
                        logger.info(f"  {k} : {'absent' if a is None else a} -> {'disparu' if b is None else b}{delta}" + (f"   [{known[k]}]" if k in known else ""))
                    if len(changes) > 30:
                        logger.info(f"  ... et {len(changes) - 30} autres (chargement d'une sauvegarde ?)")

        # 3. Victoire : derniere commande de l'episode but
        goal_ep = ctx.slot_data.get("goal_episode", 14)
        last = location_name_to_id[EPISODES[goal_ep][-1]]
        if not ctx.finished and last in (ctx.checked_locations | ctx.manual_checks | (ctx.save_checks - ctx.held_codes)):
            ctx.finished = True
            logger.info(f"Objectif atteint : {EPISODES[goal_ep][-1]} terminee, victoire envoyee au serveur.")
            await ctx.send_msgs([{"cmd": "StatusUpdate", "status": ClientStatus.CLIENT_GOAL}])


async def game_watcher(ctx: DeathStrandingContext) -> None:
    """Relance la surveillance si elle plante : une exception ne doit jamais l'arreter en silence."""
    import traceback
    last_error = ""
    while not ctx.exit_event.is_set():
        try:
            await _game_watcher_loop(ctx)
            return
        except asyncio.CancelledError:
            raise
        except Exception:
            text = traceback.format_exc()
            if text != last_error:  # une seule fois par erreur differente
                last_error = text
                logger.error("Erreur dans la surveillance du jeu (elle redemarre) :\n" + text)
            await asyncio.sleep(2.0)


def launch(*launch_args: str) -> None:
    import logging
    for noisy in ("websockets", "websockets.client", "pymem", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.INFO)     # les echanges reseau et la memoire ne sont pas utiles a l'utilisateur
    async def main(args):
        ctx = DeathStrandingContext(args.connect, args.password)
        ctx.auth = args.name
        ctx.server_task = asyncio.create_task(server_loop(ctx), name="ServerLoop")
        if gui_enabled:
            ctx.run_gui()
        ctx.run_cli()
        watcher = asyncio.create_task(game_watcher(ctx), name="GameWatcher")
        await ctx.exit_event.wait()
        ctx.server_address = None
        await ctx.shutdown()
        await watcher

    import colorama
    parser = get_base_parser(description="Client Death Stranding")
    parser.add_argument("--name", default=None)
    parser.add_argument("url", nargs="?", help="Archipelago connection url")
    args = parser.parse_args(launch_args)
    colorama.just_fix_windows_console()
    asyncio.run(main(args))
    colorama.deinit()
