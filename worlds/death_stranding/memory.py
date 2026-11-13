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
    return value if isinstance(value, int) else int(value, 16) if value.lower().startswith("0x") else int(value)


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
