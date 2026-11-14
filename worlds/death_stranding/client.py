"""Client Archipelago pour Death Stranding (PC).

  * reseau (CommonClient)  : connexion, checks, items recus, victoire ;
  * memoire (memory.py)    : ressources du joueur via une chaine de pointeurs ;
  * sauvegardes (savewatch): detecte les commandes terminees d'apres le titre des checkpoints ;
  * mode manuel            : /check <lieu> envoie un check a la main.

Commandes de diagnostic : /ds_status, /ds_give, /ds_stock, /ds_stock_give, /ds_stock_target, /ds_stock_mode, /ds_stock_pool, /ds_items, /ds_resigner, /ds_saves, /ds_selftest, /ds_catchup.
"""
from __future__ import annotations

import asyncio
import random
import json
import os
import typing

import Utils
from CommonClient import CommonContext, ClientCommandProcessor, get_base_parser, gui_enabled, logger, server_loop
from MultiServer import mark_raw
from NetUtils import ClientStatus

from .data import EPISODES, ORDER_TO_LOCATION
from .locations import location_name_to_id
from .memory import GameMemory, PymemBackend
from .savewatch import DEFAULT_COMPLETED_WORDS, ResignerCli, SaveWatcher, autodetect_root, parse_title, read_header

MAP_FILE = "memory_map.json"
PROGRESS_FILE = "DeathStranding_progress.json"
SETTINGS_FILE = "DeathStranding_settings.json"
SAVE_POLL_SECONDS = 2.0


def load_map() -> dict:
    path = Utils.user_path(MAP_FILE)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            logger.info(f"Configuration memoire : {path}")
            return json.load(f)
    import pkgutil
    logger.info("Configuration memoire : valeurs par defaut du paquet.")
    return json.loads(pkgutil.get_data(__name__, "memory_map.default.json").decode("utf-8"))


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
        """Test : /ds_give <ressource> <quantite>   ex : /ds_give Chiral Crystals 100"""
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
        """Test : /ds_stock_give <materiau> <quantite>   ex : /ds_stock_give Metals 50  (credite l'installation choisie)"""
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
        self.slot_data: dict = {}
        self.finished = False
        self.map = load_map()
        self.settings = _json_load(SETTINGS_FILE)
        self.backend = PymemBackend(self.map.get("process_name", "ds.exe"))
        self.memory = GameMemory(self.map, self.backend)
        self._warned_item: typing.Optional[int] = None
        self.saves: SaveWatcher
        self.setup_saves()

    def setup_saves(self) -> None:
        exe = self.settings.get("resigner") or self.map.get("saves", {}).get("resigner")
        root = self.settings.get("saves_root") or self.map.get("saves", {}).get("root") or autodetect_root()
        words = self.map.get("saves", {}).get("completed_words", DEFAULT_COMPLETED_WORDS)
        self.saves = SaveWatcher(root, ResignerCli(exe) if exe else None, words)
        if not exe:
            logger.info("Sauvegardes : outil de dechiffrement non configure. Tape /ds_resigner <chemin de l'exe>.")
        if not root:
            logger.info("Sauvegardes : dossier introuvable. Tape /ds_saves_dir <dossier>.")

    def register_completed_orders(self, numbers: typing.Iterable[int]) -> None:
        for n in numbers:
            loc = ORDER_TO_LOCATION.get(n)
            if loc is None:
                logger.info(f"Commande n°{n} terminee (hors liste des checks : ignoree).")
                continue
            code = location_name_to_id[loc]
            if code not in self.save_checks:
                self.save_checks.add(code)
                logger.info(f"Commande terminee detectee : {loc}")

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
            if self.slot_data.get("death_link"):
                Utils.async_start(self.update_death_link(True))

    def on_deathlink(self, data: dict):
        super().on_deathlink(data)
        # TODO : tuer le joueur (Blood/Conscience du personnage) une fois verifie.

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
        _json_save(PROGRESS_FILE, data)


async def _game_watcher_loop(ctx: DeathStrandingContext) -> None:
    grants = ctx.map.get("item_grants", {})
    loop = asyncio.get_running_loop()
    last_save_poll = 0.0
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
        to_send, unknown = plan_location_sends(ctx.manual_checks | ctx.save_checks, ctx.checked_locations,
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
            elif isinstance(grant, dict):
                new_qty = ctx.memory.add_resource(grant["resource"], int(grant["amount"]))
                if new_qty is None:
                    if ctx._warned_item != ctx.applied_index:
                        logger.info(f"En attente du jeu pour appliquer : {name}")
                        ctx._warned_item = ctx.applied_index
                    break
                logger.info(f"Objet applique : {name} (+{grant['amount']} {grant['resource']} -> {new_qty})")
            else:
                logger.info(f"Objet recu (sans effet en jeu pour l'instant) : {name}")
            ctx.applied_index += 1
            ctx.save_progress()

        # 3. Victoire : derniere commande de l'episode but
        goal_ep = ctx.slot_data.get("goal_episode", 14)
        last = location_name_to_id[EPISODES[goal_ep][-1]]
        if not ctx.finished and last in (ctx.checked_locations | ctx.manual_checks | ctx.save_checks):
            ctx.finished = True
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
