"""Outils de decouverte memoire (lecture seule) : recherche de valeurs dans tout le processus et remontee de pointeurs
vers une racine statique (module). Equivalent d'un « pointer scan », mais automatique. Necessite numpy.

Le backend doit fournir : regions() -> iterable de (base, taille), read(adresse, taille) -> bytes | None,
module_range() -> (base, taille) | None.
"""
from __future__ import annotations

import struct
import time
import typing

CHUNK = 1 << 26     # 64 Mo par lecture


def _np():
    try:
        import numpy
        return numpy
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("numpy est requis pour cette commande : py -3.12 -m pip install numpy") from e


def iter_chunks(backend, chunk: int = CHUNK) -> typing.Iterator[typing.Tuple[int, bytes]]:
    for base, size in backend.regions():
        off = 0
        while off < size:
            n = min(chunk, size - off)
            data = backend.read(base + off, n)
            if data is None and n > (1 << 20):           # lecture partielle : on retente par blocs de 1 Mo
                for sub in range(0, n, 1 << 20):
                    d = backend.read(base + off + sub, min(1 << 20, n - sub))
                    if d:
                        yield base + off + sub, d
            elif data:
                yield base + off, data
            off += n


def find_object_bases(backend, checks: typing.Dict[int, int], width: int = 8, limit: int = 50,
                      deadline: float = float("inf")) -> typing.List[int]:
    """Bases d'objets dont les entiers (`width` octets) aux decalages `checks` valent les valeurs donnees, dans tout le processus."""
    np = _np()
    dt = "<i8" if width == 8 else "<i4"
    anchor_off = max(checks, key=lambda o: abs(checks[o]))          # la plus grande valeur = la moins courante
    anchor = checks[anchor_off]
    found: typing.List[int] = []
    for base, data in iter_chunks(backend):
        if time.time() > deadline or len(found) >= limit:
            break
        arr = np.frombuffer(data, dtype=dt, count=len(data) // width)
        for i in np.flatnonzero(arr == anchor):
            obj = base + int(i) * width - anchor_off
            ok = True
            for off, val in checks.items():
                raw = backend.read(obj + off, width)
                if raw is None or int.from_bytes(raw, "little", signed=True) != val:
                    ok = False
                    break
            if ok and obj not in found:
                found.append(obj)
                if len(found) >= limit:
                    break
    return found


class _Node:
    __slots__ = ("addr", "off", "parent")

    def __init__(self, addr: int, off: int, parent: "typing.Optional[_Node]"):
        self.addr, self.off, self.parent = addr, off, parent


def reverse_chains(backend, target: int, max_depth: int = 4, first_slack: int = 0x40, max_off: int = 0x2000,
                   per_level: int = 300, deadline: float = float("inf"),
                   progress: typing.Optional[typing.Callable[[str], None]] = None
                   ) -> typing.List[typing.Tuple[int, typing.List[int]]]:
    """Cherche des chaines [module+rel] -> +o1 -> +o2 ... menant a `target`. Renvoie [(rel, [o1, o2, ...])] avec la regle :
        p = lire64(module+rel) ; pour chaque o sauf le dernier : p = lire64(p + o) ; adresse finale = p + dernier o.
    """
    np = _np()
    mod = backend.module_range()
    if not mod:
        return []
    mbase, msize = mod
    frontier: typing.List[_Node] = [_Node(target, 0, None)]
    results: typing.List[typing.Tuple[int, typing.List[int]]] = []
    seen: typing.Set[int] = {target}
    for depth in range(1, max_depth + 1):
        if not frontier or time.time() > deadline:
            break
        slack = first_slack if depth == 1 else max_off
        tgt = np.array(sorted({n.addr for n in frontier}), dtype="<i8")
        by_addr = {n.addr: n for n in frontier}
        hits: typing.List[typing.Tuple[int, int, int]] = []         # (adresse du champ, decalage, cible)
        for base, data in iter_chunks(backend):
            if time.time() > deadline:
                break
            arr = np.frombuffer(data, dtype="<i8", count=len(data) // 8)
            j = np.searchsorted(tgt, arr, side="left")
            jj = np.minimum(j, len(tgt) - 1)
            diff = tgt[jj] - arr
            ok = (j < len(tgt)) & (arr > 0x10000) & (diff >= 0) & (diff <= slack)
            for i in np.flatnonzero(ok):
                hits.append((base + int(i) * 8, int(diff[i]), int(tgt[jj[i]])))
            if len(hits) > 200_000:
                break
        if progress:
            progress(f"niveau {depth} : {len(hits)} pointeur(s) candidat(s)")
        nxt: typing.List[_Node] = []
        for field, off, t in hits:
            node = _Node(field, off, by_addr[t])
            if mbase <= field < mbase + msize:                      # racine statique trouvee
                offs, n = [], node
                while n.parent is not None:
                    offs.append(n.off)
                    n = n.parent
                results.append((field - mbase, offs))
            elif field not in seen:
                seen.add(field)
                nxt.append(node)
        if results:
            break
        nxt.sort(key=lambda n: n.off)
        frontier = nxt[:per_level]
    return results


def eval_chain(backend, rel: int, offs: typing.List[int]) -> typing.Optional[int]:
    mod = backend.module_range()
    if not mod or not offs:
        return None
    raw = backend.read(mod[0] + rel, 8)
    if raw is None:
        return None
    p = struct.unpack("<Q", raw)[0]
    for o in offs[:-1]:
        raw = backend.read(p + o, 8)
        if raw is None:
            return None
        p = struct.unpack("<Q", raw)[0]
    return p + offs[-1]
