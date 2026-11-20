"""Acces memoire a Death Stranding (PC), sans dependance a Archipelago : testable seul.

Chemin de l'inventaire (confirme par tes releves) :
    a = lire64(module + global_module_offset)
    pour chaque decalage de `chain` : a = lire64(a + decalage)
    adresse de la ressource = a + resources[nom].qty   (maximum a + resources[nom].max)
"""
from __future__ import annotations

import re
import struct
import typing
import threading
from urllib.parse import unquote

_VQ_INIT = threading.Lock()

_NB = rb"(?:\xc2\xa0|%C2%A0|\s)"


def _alts(chars: str) -> bytes:
    """Alternative d'octets pour des caracteres : UTF-8 brut ou encode en %XX (majuscules), comme le jeu l'ecrit selon l'endroit."""
    out = []
    for c in chars:
        raw = c.encode("utf-8")
        out.append(re.escape(raw))
        if len(raw) > 1 or not c.isalnum():
            out.append("".join(f"%{x:02X}" for x in raw).encode())
    return b"(?:" + b"|".join(out) + b")"


# « ... : nº 62 « nom » - 22:48:17 » tel que le jeu l'ecrit en memoire (texte brut ou encode en %XX). Variantes pour d'autres langues (NON validees en jeu,
# sauf le francais) : deux-points pleine chasse, prefixes de numero (n°, nº, no., nr., N.º, №, #), guillemets «», “”, „“, 「」, 『』.
_COLON = _alts(":\uff1a")
_NUM_PREFIX = rb"(?:n(?:\.?\s?" + _alts("\u00ba\u00b0") + rb"|o|r|um)|" + _alts("\u2116") + rb"|\#)\.?"
_QUOTE_OPEN = _alts("\u00ab\u201c\u201e\u300c\u300e\"")
_QUOTE_CLOSE = _alts("\u00bb\u201d\u201c\u300d\u300f\"")
_DASH = _alts("-\u2013\u2014")
_TITLE_RE = re.compile(
    _COLON + _NB + rb"*" + _NUM_PREFIX + _NB + rb"*(\d{1,4})" + _NB + rb"*" + _QUOTE_OPEN + rb"(.{0,450}?)" + _QUOTE_CLOSE
    + _NB + rb"*" + _DASH + _NB + rb"*(\d{1,3}:\d\d:\d\d)", re.IGNORECASE)      # « No. », « Nr. » en majuscule initiale

# Etats qui contiennent un mot d'achevement sans signifier « terminee » (« incomplete », « non terminee »...) : jamais pris pour une fin de commande.
NEGATIVE_WORDS = ("incompl", "inconclu", "unvollst", "non termin", "not complet", "unfinish", "uncomplet", "nicht abgeschlossen", "no complet", "no termin",
                  "niewykon", "nieukoncz", "nedokonc", "незаверш", "невыполн", "未完", "未達", "미완")


def _fold(text: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")).casefold()   # NFC : recompose le hangul


def state_completed(state: str, words: typing.Iterable[str]) -> bool:
    """`state` : texte avant les deux-points, deja passe par _fold. Vrai s'il contient un mot « terminee » et aucun mot de negation."""
    return any(w in state for w in words) and not any(n in state for n in NEGATIVE_WORDS)


def iter_memory_titles(data: bytes) -> typing.Iterator[typing.Tuple[str, int, str, str, int]]:
    """TOUS les titres « Title = <etat> : nº N « nom » - hh:mm:ss » de `data`, quel que soit l'etat : (etat brut, numero, nom, heure, position).
    Sert a la commande /ds_titles (diagnostic pour une autre langue) et a parse_memory_titles."""
    i = data.find(b"Title")      # recherche rapide du mot-cle d'abord ; l'expression reguliere ne tourne que sur 900 octets autour
    while i >= 0:
        seg = data[i:i + 900]
        if seg[5:60].lstrip(b" \t").startswith(b"="):
            m = _TITLE_RE.search(seg)
            if m and m.start() < 300:
                eq = seg.find(b"=") + 1
                raw_state = unquote(seg[eq:m.start()].decode("utf-8", "replace")).replace("\xa0", " ").strip()
                name = unquote(m.group(2).decode("utf-8", "replace")).replace("\xa0", " ").strip()
                yield raw_state, int(m.group(1)), name, m.group(3).decode("ascii"), i
        i = data.find(b"Title", i + 5)


def parse_memory_titles(data: bytes, words: typing.Iterable[str]
                        ) -> typing.Tuple[typing.List[typing.Tuple[int, str, int]], typing.List[int]]:
    """Titres de points de controle « Title = Commande terminee : nº N « nom » - hh:mm:ss » presents dans `data`.
    Renvoie ([(numero, heure de jeu, position)] des commandes TERMINEES, positions de toutes les lignes « Title = »). Les listes d'historique de
    l'interface (sans « Title ») sont ignorees. Les positions de tous les titres servent a delimiter la zone ou le jeu ecrit ses points de controle,
    meme quand la commande en cours n'est pas terminee."""
    words = tuple(words)
    found: typing.List[typing.Tuple[int, str, int]] = []
    anchors: typing.List[int] = []
    i = data.find(b"Title")
    while i >= 0:
        if data[i + 5:i + 60].lstrip(b" \t").startswith(b"="):
            anchors.append(i)
        i = data.find(b"Title", i + 5)
    for raw_state, num, _name, hhmmss, pos in iter_memory_titles(data):
        if state_completed(_fold(raw_state), words):
            found.append((num, hhmmss, pos))
    return found, anchors


PTR_MIN = 0x10000
PTR_MAX = 0x7FFFFFFFFFFF
CHUNK = 4 * 1024 * 1024
PAGE = 4096


def _num(value: typing.Union[int, str]) -> int:
    if isinstance(value, int):
        return value
    v = value.strip().lower()
    return int(v, 16) if v.startswith(("0x", "-0x")) else int(v)


def aob_to_regex(pattern: str) -> "re.Pattern[bytes]":
    parts = []
    for tok in pattern.split():
        parts.append(b"." if tok == "??" else re.escape(bytes([int(tok, 16)])))
    return re.compile(b"".join(parts), re.DOTALL)


class PymemBackend:
    """Backend reel (Windows). Les erreurs de lecture renvoient None au lieu de lever."""

    def __init__(self, process_name: str):
        self.process_name = process_name
        self._pm = None
        self._base = 0
        self._size = 0

    def attach(self) -> bool:
        try:
            import pymem
            import pymem.process
            self._pm = pymem.Pymem(self.process_name)
            info = pymem.process.module_from_name(self._pm.process_handle, self.process_name)
            self._base, self._size = info.lpBaseOfDll, info.SizeOfImage
            return True
        except Exception:
            self._pm = None
            return False

    def attached(self) -> bool:
        return self._pm is not None and self.read(self._base, 2) is not None

    def module_range(self) -> typing.Optional[typing.Tuple[int, int]]:
        return (self._base, self._size) if self._pm else None

    def read(self, address: int, size: int) -> typing.Optional[bytes]:
        if not self._pm:
            return None
        try:
            return bytes(self._pm.read_bytes(address, size))
        except Exception:
            return None

    _vq: typing.Any = None

    @classmethod
    def _virtual_query(cls):
        """VirtualQueryEx et sa structure, definis une seule fois : deux recherches en parallele (titres, table) ne doivent pas se marcher dessus."""
        with _VQ_INIT:
            if cls._vq is None:
                import ctypes
                from ctypes import wintypes as w

                class MBI(ctypes.Structure):
                    _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                                ("AllocationProtect", w.DWORD), ("PartitionId", w.WORD), ("RegionSize", ctypes.c_size_t),
                                ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD)]

                query = ctypes.WinDLL("kernel32", use_last_error=True).VirtualQueryEx
                query.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
                query.restype = ctypes.c_size_t
                cls._vq = (query, MBI)
        return cls._vq

    def regions(self, private_only: bool = False) -> typing.Iterator[typing.Tuple[int, int]]:
        """Regions memoire lisibles du processus (VirtualQueryEx) : (base, taille). `private_only` : tas du jeu seulement (MEM_PRIVATE), sans
        les fichiers mappes ni la memoire video, tres volumineux et lents a lire."""
        if not self._pm:
            return
        import ctypes
        query, MBI = self._virtual_query()
        handle, addr, mbi = self._pm.process_handle, 0, MBI()
        while addr < 0x7FFFFFFFFFFF:
            if not query(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base, size = int(mbi.BaseAddress or 0), int(mbi.RegionSize)
            readable = mbi.State == 0x1000 and (mbi.Protect & 0xEE) and not (mbi.Protect & 0x101)
            if readable and size and (not private_only or mbi.Type == 0x20000):
                yield base, size
            addr = base + size

    def write(self, address: int, data: bytes) -> bool:
        if not self._pm:
            return False
        try:
            self._pm.write_bytes(address, data, len(data))
            return True
        except Exception:
            return False


class GameMemory:
    def __init__(self, config: dict, backend):
        self.cfg = config
        self.inv = config.get("inventory", {})
        self.backend = backend
        self._good_global: typing.Optional[int] = None
        self._aob_cache: typing.Optional[typing.List[int]] = None
        self.fac = config.get("facilities", {})
        self._stock_base: typing.Optional[int] = None
        self.player = config.get("player", {})

    # -- lecture de base ---------------------------------------------------
    def _u64(self, addr: int) -> typing.Optional[int]:
        data = self.backend.read(addr, 8)
        return struct.unpack("<Q", data)[0] if data and len(data) == 8 else None

    def _i32(self, addr: int) -> typing.Optional[int]:
        data = self.backend.read(addr, 4)
        return struct.unpack("<i", data)[0] if data and len(data) == 4 else None

    @staticmethod
    def _plausible(p: typing.Optional[int]) -> bool:
        return p is not None and PTR_MIN <= p <= PTR_MAX

    # -- resolution --------------------------------------------------------
    def _follow(self, global_addr: int) -> typing.Optional[int]:
        a = self._u64(global_addr)
        for off in self.inv.get("chain", []):
            if not self._plausible(a):
                return None
            a = self._u64(a + _num(off))
        return a if self._plausible(a) else None

    def _sane(self, obj: int) -> bool:
        """Controle : la premiere ressource doit avoir 0 <= quantite <= maximum <= 10 millions."""
        for res in self.inv.get("resources", {}).values():
            q, m = self._i32(obj + _num(res["qty"])), self._i32(obj + _num(res["max"]))
            return q is not None and m is not None and 0 <= q <= m <= 10_000_000 and m > 0
        return False

    def _scan_module(self, pattern: str) -> typing.List[int]:
        rng = self.backend.module_range()
        if not rng:
            return []
        base, size = rng
        rx = aob_to_regex(pattern)
        overlap = len(pattern.split())
        found: typing.List[int] = []
        pos = 0
        while pos < size:
            n = min(CHUNK + overlap, size - pos)
            data = self.backend.read(base + pos, n)
            if data is None:  # page non lisible dans le bloc : on lit page par page
                data = b""
                for off in range(0, n, PAGE):
                    part = self.backend.read(base + pos + off, min(PAGE, n - off))
                    data += part if part is not None else b"\x00" * min(PAGE, n - off)
            for m in rx.finditer(data):
                found.append(base + pos + m.start())
            pos += CHUNK
        return found

    def _aob_globals(self) -> typing.List[int]:
        if self._aob_cache is not None:
            return self._aob_cache
        out: typing.List[int] = []
        pattern = self.inv.get("global_aob")
        if pattern:
            for hit in self._scan_module(pattern):
                disp = self._i32(hit + 3)
                if disp is None:
                    continue
                g = hit + 7 + disp  # mov rax,[rip+disp32] : 7 octets
                for d in self.inv.get("global_aob_deltas", ["0x0"]):
                    out.append(g + _num(d))
        self._aob_cache = out
        return out

    def _candidates(self) -> typing.Iterator[int]:
        if self._good_global is not None:
            yield self._good_global
        rng = self.backend.module_range()
        if rng and "global_module_offset" in self.inv:
            yield rng[0] + _num(self.inv["global_module_offset"])
        yield from self._aob_globals()

    def resolve_object(self) -> typing.Optional[int]:
        """Adresse de l'objet d'inventaire, ou None (jeu pas charge, menu principal, etc.)."""
        for g in self._candidates():
            obj = self._follow(g)
            if obj is not None and self._sane(obj):
                self._good_global = g
                return obj
        self._good_global = None
        return None

    # -- ressources --------------------------------------------------------
    def read_resource(self, name: str) -> typing.Optional[typing.Tuple[int, int]]:
        res = self.inv.get("resources", {}).get(name)
        obj = self.resolve_object() if res else None
        if obj is None:
            return None
        q, m = self._i32(obj + _num(res["qty"])), self._i32(obj + _num(res["max"]))
        return (q, m) if q is not None and m is not None else None

    def add_resource(self, name: str, delta: int) -> typing.Optional[int]:
        """Ajoute `delta` (plafonne entre 0 et le maximum). Renvoie la nouvelle quantite, ou None."""
        res = self.inv.get("resources", {}).get(name)
        obj = self.resolve_object() if res else None
        if obj is None:
            return None
        q, m = self._i32(obj + _num(res["qty"])), self._i32(obj + _num(res["max"]))
        if q is None or m is None:
            return None
        new = max(0, min(q + delta, m))
        return new if self.backend.write(obj + _num(res["qty"]), struct.pack("<i", new)) else None

    # -- instantanes et comparaison (decouverte, lecture seule) -------------
    # -- stocks de materiaux par installation ------------------------------
    def _stock_sane(self, base: int) -> bool:
        """Controle : les 6 valeurs de la premiere installation sont des quantites plausibles (0..10 millions)."""
        stock = self.fac.get("stock", {})
        if not stock:
            return False
        for off in next(iter(stock.values())).values():
            v = self._i32(base + _num(off))
            if v is None or not 0 <= v <= 10_000_000:
                return False
        return True

    def _find_stock_base(self) -> typing.Optional[int]:
        rng = self.backend.module_range()
        if not rng or "global_module_offset" not in self.fac:
            return None
        g = rng[0] + _num(self.fac["global_module_offset"])
        for layout in self.fac.get("layouts", []):
            p = self._u64(g)
            for off in layout.get("chain", []):
                if not self._plausible(p):
                    break
                p = self._u64(p + _num(off))
            if self._plausible(p):
                base = p + _num(layout.get("shift", 0))
                if self._stock_sane(base):
                    return base
        return None

    def stock_base(self) -> typing.Optional[int]:
        """Adresse de reference des stocks, ou None (jeu pas charge). Revalidee a chaque appel."""
        if self._stock_base is not None and self._stock_sane(self._stock_base):
            return self._stock_base
        self._stock_base = self._find_stock_base()
        return self._stock_base

    def stock_address(self, facility: str, material: str) -> typing.Optional[int]:
        base = self.stock_base()
        off = self.fac.get("stock", {}).get(facility, {}).get(material)
        return None if base is None or off is None else base + _num(off)

    def read_stock(self, facility: str, material: str) -> typing.Optional[int]:
        addr = self.stock_address(facility, material)
        return None if addr is None else self._i32(addr)

    def add_stock(self, facility: str, material: str, delta: int) -> typing.Optional[int]:
        """Ajoute `delta` au stock d'une installation (plafonne entre 0 et max_stock). Renvoie la nouvelle quantite ou None."""
        addr = self.stock_address(facility, material)
        cur = None if addr is None else self._i32(addr)
        if addr is None or cur is None:
            return None
        new = max(0, min(cur + delta, int(self.fac.get("max_stock", 99999))))
        return new if self.backend.write(addr, struct.pack("<i", new)) else None

    # -- likes -------------------------------------------------------------
    def _likes_addr(self, which: str) -> typing.Optional[int]:
        cfg, rng = self.cfg.get("likes", {}), self.backend.module_range()
        if not cfg or not rng or which not in ("npc", "players") or which not in cfg:
            return None
        obj = self._u64(rng[0] + _num(cfg["global_module_offset"]))
        return obj + _num(cfg[which]) if self._plausible(obj) else None

    def read_order_progress(self) -> typing.Optional[int]:
        """Compteur d'etapes de commande accomplies ([module+global] + counter, int32), ou None si illisible ou incoherent."""
        cfg, rng = self.cfg.get("order_progress", {}), self.backend.module_range()
        if not cfg or not rng:
            return None
        obj = self._u64(rng[0] + _num(cfg["global_module_offset"]))
        if not self._plausible(obj):
            return None
        v = self._i32(obj + _num(cfg["counter"]))
        return v if v is not None and 0 <= v <= 1_000_000 else None

    def read_standard_orders(self) -> typing.Optional[int]:
        """Commandes standard livrees : valeur de la cle `key` dans la table de statistiques ([[module+global]+chain]), ou None si illisible ou incoherent."""
        cfg, rng = self.cfg.get("standard_orders", {}), self.backend.module_range()
        if not cfg or not rng:
            return None
        p = self._u64(rng[0] + _num(cfg["global_module_offset"]))
        for off in cfg.get("chain", []):
            if not self._plausible(p):
                return None
            p = self._u64(p + _num(off))
        if not self._plausible(p):
            return None
        data = self.backend.read(p, _num(cfg.get("table_size", "0x280")))
        if not data:
            return None
        key, found, known = int(cfg.get("key", 17)), None, 0
        for o in range(0, len(data) - 15, 16):
            k, flags, val = struct.unpack_from("<iii", data, o)
            state = flags & 0xFF
            if state in (1, 2):
                known += 1
            if k == key and state in (1, 2):
                found = val if state == 2 else 0
        if known < 5 or found is None:   # ce n'est pas la table attendue
            return None
        return found if 0 <= found <= 1_000_000 else None

    def _follow_chain(self, rel: int, offs: typing.List[int]) -> typing.Tuple[typing.Optional[int], str]:
        """Suit une chaine comme /ds_chain : tous les decalages sauf le dernier sont des pointeurs a suivre, le dernier s'ajoute. (adresse ou None, trace)."""
        rng = self.backend.module_range()
        p = self._u64(rng[0] + rel)
        trace = f"ds.exe+0x{rel:X}=0x{p or 0:X}"
        for off in offs[:-1]:
            if not self._plausible(p):
                return None, trace
            p = self._u64(p + off)
            trace += f" -> +0x{off:X}=0x{p or 0:X}"
        if not self._plausible(p):
            return None, trace
        return p + (offs[-1] if offs else 0), trace

    def _table_capacity(self, cfg: dict, base: int) -> typing.Tuple[typing.Optional[bytes], int]:
        """Lit la table et devine sa capacite (puissance de 2) : la table de hachage grandit quand elle se remplit. Chaque case occupee doit se trouver
        pres de `hash & (capacite - 1)` ; on garde la plus grande capacite coherente (au-dela de la vraie table, la memoire est vide ou incoherente)."""
        size, lo = int(cfg.get("slot_size", 24)), int(cfg.get("slots", 512))
        ho = _num(cfg.get("hash_offset", 0))
        n = lo
        cands = []
        while n <= int(cfg.get("max_slots", 4096)):
            cands.append(n)
            n *= 2
        for n in reversed(cands):
            data = self.backend.read(base, n * size)
            if not data or len(data) < n * size:
                continue
            occ = ok = 0
            for s in range(n):
                h = struct.unpack_from("<I", data, s * size + ho)[0]
                if h:
                    occ += 1
                    if (s - (h & (n - 1))) % n < 64:
                        ok += 1
            if occ >= int(cfg.get("min_occupied", 100)) and ok * 10 >= occ * 9:
                return data, n
        return None, 0

    def _read_counters_at(self, cfg: dict, base: int) -> typing.Tuple[typing.Optional[typing.Dict[str, int]], str]:
        size = int(cfg.get("slot_size", 24))
        data, slots = self._table_capacity(cfg, base)
        if data is None:
            return None, f"0x{base:X} : pas une table de compteurs (illisible, peu remplie ou incoherente)"
        ko, vo = _num(cfg.get("key_offset", 4)), _num(cfg.get("value_offset", 20))
        ho = _num(cfg.get("hash_offset", 0))
        wanted = {name: (bytes.fromhex(c["key"]), _num(c["hash"]) if c.get("hash") else None) for name, c in cfg.get("counters", {}).items()}
        optional = {name for name, c in cfg.get("counters", {}).items() if c.get("optional")}     # cle absente = compteur pas encore cree = 0
        found: typing.Dict[str, typing.List[int]] = {name: [] for name in wanted}
        seen_key: typing.Dict[str, typing.List[str]] = {name: [] for name in wanted}
        for s in range(slots):
            o = s * size
            h = struct.unpack_from("<I", data, o + ho)[0]
            key = data[o + ko:o + ko + 16]
            for name, (k, kh) in wanted.items():
                if key == k:
                    v = struct.unpack_from("<i", data, o + vo)[0]
                    seen_key[name].append(f"case {s} hash 0x{h:X} valeur {v}")
                    # hash connu : on l'exige ; sinon (compteur dont le hash n'a pas ete releve) : hash non nul et case compatible avec le sondage
                    # (les copies anciennes ont un hash nul)
                    if (h == kh) if kh is not None else (h != 0 and (s - (h & (slots - 1))) % slots < 256):
                        found[name].append(v)
        out = {}
        for name, vals in found.items():
            if not vals and name in optional:
                out[name] = 0
                continue
            if len(vals) != 1:
                return None, f"0x{base:X} ({slots} cases) : compteur « {name} » : {len(vals)} case(s) valides ; cases avec la cle : {'; '.join(seen_key[name]) or 'aucune'}"
            if not 0 <= vals[0] <= 1_000_000:
                return None, f"0x{base:X} : compteur « {name} » : valeur aberrante {vals[0]}"
            out[name] = vals[0]
        return out, f"{slots} cases"

    def scan_titles(self, words: typing.Iterable[str], windows: typing.Optional[typing.List[typing.Tuple[int, int]]] = None,
                    deadline: float = 600.0, progress: typing.Optional[typing.Callable[[str], None]] = None) -> typing.Tuple[typing.Set[typing.Tuple[int, str]], typing.List[typing.Tuple[int, int]]]:
        """Cherche les titres de points de controle en memoire. `windows` None = toute la memoire (lent, 1 a 5 min), sinon seulement ces zones
        (base, taille). Renvoie ({(numero, heure)}, zones ou des titres ont ete vus)."""
        import time
        stop, titles, spans = time.time() + deadline, set(), []
        chunk, overlap = 1 << 23, 512
        todo = self._regions_in(windows)
        grand, done, last_say = sum(t for _, t in todo), 0, time.time()
        for base, total in todo:
            if time.time() > stop:
                break
            off = 0
            while off < total:
                n = min(chunk, total - off)
                data = self.backend.read(base + off, n)
                done += n
                if progress and windows is None and time.time() - last_say >= 20:
                    last_say = time.time()
                    progress(f"Recherche des titres : {done >> 20} / {grand >> 20} Mo lus...")
                if data:
                    found, anchors = parse_memory_titles(data, words)
                    titles.update((num, hhmmss) for num, hhmmss, _ in found)
                    spans.extend(base + off + a for a in anchors)
                off += n - overlap if off + n < total else n
        zones: typing.List[typing.Tuple[int, int]] = []
        margin = 6 << 20
        for a in sorted(spans):
            lo, hi = max(0, a - margin), a + margin
            if zones and lo <= zones[-1][0] + zones[-1][1]:
                zones[-1] = (zones[-1][0], max(zones[-1][1], hi - zones[-1][0]))
            else:
                zones.append((lo, hi - lo))
        return titles, zones

    def list_titles(self, windows: typing.Optional[typing.List[typing.Tuple[int, int]]] = None, deadline: float = 600.0
                    ) -> typing.List[typing.Tuple[str, int, str, str]]:
        """Diagnostic : TOUS les titres de points de controle lus en memoire, quel que soit leur etat (etat brut, numero, nom, heure), sans doublon."""
        import time
        stop, out, seen = time.time() + deadline, [], set()
        chunk, overlap = 1 << 23, 512
        for base, total in self._regions_in(windows):
            if time.time() > stop:
                break
            off = 0
            while off < total:
                n = min(chunk, total - off)
                data = self.backend.read(base + off, n)
                if data:
                    for state, num, name, hhmmss, _pos in iter_memory_titles(data):
                        if (state, num, name, hhmmss) not in seen:
                            seen.add((state, num, name, hhmmss))
                            out.append((state, num, name, hhmmss))
                off += n - overlap if off + n < total else n
        return out

    def _regions_in(self, windows: typing.Optional[typing.List[typing.Tuple[int, int]]]) -> typing.List[typing.Tuple[int, int]]:
        """Tas du jeu (memoire privee), limite aux fenetres (base, taille) si elles sont donnees."""
        try:
            todo = list(self.backend.regions(private_only=True))
        except TypeError:           # fausse memoire des tests
            todo = list(self.backend.regions())
        if windows is not None:
            todo = [(max(b0, w0), min(b0 + sz, w0 + wl) - max(b0, w0)) for b0, sz in todo for w0, wl in windows
                    if max(b0, w0) < min(b0 + sz, w0 + wl)]
        return todo

    def scan_named_table(self, deadline: float = 240.0, progress: typing.Optional[typing.Callable[[str], None]] = None,
                         windows: typing.Optional[typing.List[typing.Tuple[int, int]]] = None) -> typing.Optional[int]:
        """Retrouve la table de compteurs nommes dans la memoire du jeu par sa signature (hash + cle du premier compteur), quand les chaines de
        pointeurs ne marchent plus (redemarrage, changement de sauvegarde). Bloquant (de quelques secondes a quelques minutes) : a lancer hors de la boucle
        principale. Renvoie la base verifiee (cles et hash controles) ou None."""
        import time
        cfg = self.cfg.get("named_counters", {})
        counters = cfg.get("counters", {})
        if not cfg or not counters or not hasattr(self.backend, "regions"):
            return None
        first = next(iter(counters.values()))
        h0, size = _num(first["hash"]), int(cfg.get("slot_size", 24))
        pat = struct.pack("<I", h0) + bytes.fromhex(first["key"])
        rng, stop = self.backend.module_range(), time.time() + deadline
        hits: typing.List[int] = []
        chunk = 1 << 24
        for base, total in self._regions_in(windows):
            if time.time() > stop:
                break
            if rng and rng[0] <= base < rng[0] + rng[1]:
                continue
            off = 0
            while off < total:
                n = min(chunk, total - off)
                data = self.backend.read(base + off, n)
                if data is None and n > (1 << 20):       # lecture partielle : on retente par blocs de 1 Mio
                    for sub_off in range(0, n, 1 << 20):
                        d = self.backend.read(base + off + sub_off, min(1 << 20, n - sub_off))
                        i = d.find(pat) if d else -1
                        while i >= 0:
                            hits.append(base + off + sub_off + i)
                            i = d.find(pat, i + 1)
                elif data:
                    i = data.find(pat)
                    while i >= 0:
                        hits.append(base + off + i)
                        i = data.find(pat, i + 1)
                off += n - (len(pat) - 1) if off + n < total else n
        if progress:
            progress(f"{len(hits)} occurrence(s) de la signature.")
        lo, hi = int(cfg.get("slots", 512)), int(cfg.get("max_slots", 4096))
        for hit in hits:
            n = lo
            while n <= hi:
                home = h0 & (n - 1)
                for d in range(0, 256):   # la case peut etre decalee par le sondage lineaire
                    base = hit - (home + d) * size
                    if base <= 0:
                        break
                    out, _ = self._read_counters_at(cfg, base)
                    if out is not None:
                        self._named_base = base
                        return base
                n *= 2
        return None

    def named_counters_report(self) -> typing.Tuple[typing.Optional[typing.Dict[str, int]], str]:
        """(compteurs nommes {nom: valeur} ou None, explication). Essaie chaque racine configuree (la derniere qui a marche d'abord) ;
        la table doit contenir les bonnes cles avec le bon hash."""
        cfg, rng = self.cfg.get("named_counters", {}), self.backend.module_range()
        if not cfg:
            return None, "section « named_counters » absente de la configuration memoire"
        if not rng:
            return None, "module ds.exe introuvable (jeu non detecte)"
        scanned = getattr(self, "_named_base", None)
        if scanned is not None:      # base retrouvee par recherche memoire : on la reverifie a chaque lecture
            out, why = self._read_counters_at(cfg, scanned)
            if out is not None:
                self._named_last_base = scanned
                return out, f"ok (recherche memoire, {why})"
            self._named_base = None
        roots = cfg.get("roots") or []
        order = list(range(len(roots)))
        last = getattr(self, "_named_root", None)
        if last in order:
            order.remove(last)
            order.insert(0, last)
        reasons, table_level = [], []
        for i in order:
            r = roots[i]
            base, trace = self._follow_chain(_num(r["global_module_offset"]), [_num(o) for o in r.get("chain", [])])
            if base is None:
                reasons.append(f"#{i + 1} {trace}")
                continue
            out, why = self._read_counters_at(cfg, base)
            if out is not None:
                self._named_root = i
                self._named_last_base = base
                return out, f"ok (chaine n°{i + 1}, {why})"
            table_level.append(f"#{i + 1} {why}")
        shown = (table_level + reasons)[:3]
        return None, f"aucune des {len(roots)} chaine(s) ne mene a la table ; " + " | ".join(shown) + (" ..." if len(table_level) + len(reasons) > 3 else "")

    def read_named_counters(self) -> typing.Optional[typing.Dict[str, int]]:
        """Compteurs nommes du jeu ({nom: valeur}), ou None si illisible ou incoherent (voir named_counters_report)."""
        return self.named_counters_report()[0]

    def dump_named_table(self) -> typing.Optional[typing.Dict[str, int]]:
        """TOUS les compteurs de la table nommee ({cle en hexadecimal (32 caracteres): valeur int32}), pas seulement les trois que le client utilise.
        Diagnostic en lecture seule : sert a reperer, par difference avant / apres un evenement du jeu, quels autres compteurs bougent (par categorie
        de commande, par exemple). Les cases a hash nul (copies anciennes) sont ignorees. None si la table n'est pas lisible."""
        if self.named_counters_report()[0] is None:
            return None
        base, cfg = getattr(self, "_named_last_base", None), self.cfg.get("named_counters", {})
        if base is None:
            return None
        data, slots = self._table_capacity(cfg, base)
        if data is None:
            return None
        size = int(cfg.get("slot_size", 24))
        ko, vo, ho = _num(cfg.get("key_offset", 4)), _num(cfg.get("value_offset", 20)), _num(cfg.get("hash_offset", 0))
        out: typing.Dict[str, int] = {}
        for s in range(slots):
            o = s * size
            if struct.unpack_from("<I", data, o + ho)[0]:
                out[data[o + ko:o + ko + 16].hex()] = struct.unpack_from("<i", data, o + vo)[0]
        return out

    def read_order_types(self) -> typing.Optional[typing.Dict[str, int]]:
        """Totaux de livraisons par type, a une constante pres (seuls les ecarts comptent) : {"standard", "main", "bot"}, ou None.
        main = nobot - standard ; bot = total - nobot. Lecture coherente exigee (les trois compteurs sont ecrits separement par le jeu)."""
        named, std = self.read_named_counters(), self.read_standard_orders()
        if named is None or std is None or "nobot" not in named or "total" not in named:
            return None
        # "repair" : cle creee quand la commande de reparation n°62 se termine (absente avant = 0) ; le total monte alors, pas « nobot » : sans elle la 62 ressemblerait a un bot ;
        # le +1000 ne sert qu'a garder une valeur positive (seuls les ecarts comptent)
        return {"standard": std, "main": named["nobot"] - std, "bot": named["total"] - named["nobot"] - named.get("repair", 0) + 1000}

    def _i64(self, addr: int) -> typing.Optional[int]:
        data = self.backend.read(addr, 8)
        return struct.unpack("<q", data)[0] if data and len(data) == 8 else None

    def read_likes(self) -> typing.Optional[typing.Tuple[int, int]]:
        """(likes PNJ, likes autres joueurs), ou None si illisible ou incoherent."""
        mx = int(self.cfg.get("likes", {}).get("max", 999_999_999))
        out = []
        for w in ("npc", "players"):
            a = self._likes_addr(w)
            v = None if a is None else self._i64(a)
            if v is None or not 0 <= v <= mx:
                return None
            out.append(v)
        return out[0], out[1]

    def add_likes(self, which: str, delta: int) -> typing.Optional[int]:
        """Ajoute `delta` au compteur `which` (plafonne 0..max). Renvoie la nouvelle valeur ou None."""
        if self.read_likes() is None:
            return None
        a = self._likes_addr(which)
        cur = None if a is None else self._i64(a)
        if cur is None:
            return None
        new = max(0, min(cur + delta, int(self.cfg["likes"].get("max", 999_999_999))))
        return new if self.backend.write(a, struct.pack("<q", new)) else None

    # -- sante du joueur (DeathLink) ---------------------------------------
    def _f32(self, addr: int) -> typing.Optional[float]:
        data = self.backend.read(addr, 4)
        return struct.unpack("<f", data)[0] if data and len(data) == 4 else None

    def _player_object(self) -> typing.Optional[int]:
        """Objet des stats du joueur : meme racine que l'inventaire, autre branche (chaine `player.chain`)."""
        if not self.player or self.resolve_object() is None or self._good_global is None:
            return None
        a = self._u64(self._good_global)
        for off in self.player.get("chain", []):
            if not self._plausible(a):
                return None
            a = self._u64(a + _num(off))
        return a if self._plausible(a) else None

    def read_vitals(self) -> typing.Optional[typing.Tuple[float, float]]:
        """(vie, vie max) du joueur, ou None si introuvable ou incoherent (menu, chargement...)."""
        obj = self._player_object()
        if obj is None:
            return None
        hp, mx = self._f32(obj + _num(self.player["health"])), self._f32(obj + _num(self.player["max_health"]))
        if hp is None or mx is None or not (0 < mx <= 100_000) or not (-1.0 <= hp <= mx + 1.0):
            return None
        return hp, mx

    def player_ready(self) -> bool:
        return self.read_vitals() is not None

    def read_player_field(self, field: str) -> typing.Optional[float]:
        obj = self._player_object()
        if obj is None or field not in self.player:
            return None
        v = self._f32(obj + _num(self.player[field]))
        return v if v is not None and v == v and abs(v) < 1e7 else None   # v == v : pas NaN

    def adjust_player(self, field: str, delta: float, floor: typing.Optional[float] = None,
                      ceil: typing.Optional[float] = None) -> typing.Optional[typing.Tuple[float, float]]:
        """Ajoute `delta` a un champ float du joueur. `floor` (si delta < 0) et `ceil` (si delta > 0) bornent le resultat ;
        une valeur deja au-dela de la borne n'est jamais modifiee dans le mauvais sens. Renvoie (avant, apres) ou None."""
        obj = self._player_object()
        cur = self.read_player_field(field)
        if obj is None or cur is None:
            return None
        new = cur + delta
        if delta < 0 and floor is not None:
            new = max(new, min(cur, floor))
        if delta > 0 and ceil is not None:
            new = min(new, max(cur, ceil))
        if not self.backend.write(obj + _num(self.player[field]), struct.pack("<f", new)):
            return None
        return cur, new

    def kill_player(self) -> bool:
        """Met la vie du joueur a 0 (seulement si les valeurs sont coherentes)."""
        obj = self._player_object()
        if obj is None or self.read_vitals() is None:
            return False
        return bool(self.backend.write(obj + _num(self.player["health"]), struct.pack("<f", 0.0)))

