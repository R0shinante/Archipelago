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

    def regions(self) -> typing.Iterator[typing.Tuple[int, int]]:
        """Regions memoire lisibles du processus (VirtualQueryEx) : (base, taille)."""
        if not self._pm:
            return
        import ctypes
        from ctypes import wintypes as w

        class MBI(ctypes.Structure):
            _fields_ = [("BaseAddress", ctypes.c_void_p), ("AllocationBase", ctypes.c_void_p),
                        ("AllocationProtect", w.DWORD), ("PartitionId", w.WORD), ("RegionSize", ctypes.c_size_t),
                        ("State", w.DWORD), ("Protect", w.DWORD), ("Type", w.DWORD)]

        query = ctypes.windll.kernel32.VirtualQueryEx
        query.argtypes = [w.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
        handle, addr, mbi = self._pm.process_handle, 0, MBI()
        while addr < 0x7FFFFFFFFFFF:
            if not query(handle, ctypes.c_void_p(addr), ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base, size = int(mbi.BaseAddress or 0), int(mbi.RegionSize)
            readable = mbi.State == 0x1000 and (mbi.Protect & 0xEE) and not (mbi.Protect & 0x101)
            if readable and size:
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

