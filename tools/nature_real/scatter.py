"""Végétation de sol : touffes d'herbe, herbes sèches, litière de feuilles, brindilles — pour poser chaque asset dans un décor crédible."""
import math
import random

import rmat
from rgeo import V

UP = V(0, 0, 1)


def _lean(rng, spread):
    return V(rng.gauss(0, spread), rng.gauss(0, spread), 0)


def clump(b, mat, c, n=36, radius=0.12, hmin=0.15, hmax=0.45, width=0.012, rng=None, spread=0.35, curl=0.9, seg=3):
    rng = rng or random.Random(0)
    c = V(c)
    for i in range(n):
        a = rng.uniform(0, 6.283)
        r = radius * math.sqrt(rng.random())
        base = c + V(math.cos(a) * r, math.sin(a) * r, -0.01)
        h = rng.uniform(hmin, hmax) * (1.0 - 0.45 * (r / max(radius, 1e-6)))
        out = V(math.cos(a), math.sin(a), 0) * rng.uniform(0.05, spread) + _lean(rng, 0.12)
        d = (V(0, 0, 1) + out).normalized()
        side = rng.uniform(0, 6.283)
        up = V(math.cos(side), math.sin(side), 0.5)
        b.leaf(base, d, up, h, width * rng.uniform(0.8, 1.3), mat, curl=curl * rng.uniform(0.5, 1.5), twist=rng.uniform(-0.6, 0.6), rand=rng.random(), seg=seg, shape="grass", fold=0.5, droop=0.0)


def field(b, mat, center, size, count, rng, hmin=0.12, hmax=0.4, avoid=None, spread=0.35, zfn=None):
    """Prairie : `count` touffes réparties sur un disque / une ellipse ; avoid(x, y) -> True pour laisser un vide."""
    cx, cy = center
    sx, sy = size if isinstance(size, (tuple, list)) else (size, size)
    k = 0
    tries = 0
    while k < count and tries < count * 8:
        tries += 1
        a = rng.uniform(0, 6.283)
        r = math.sqrt(rng.random())
        x, y = cx + math.cos(a) * r * sx, cy + math.sin(a) * r * sy
        if avoid and avoid(x, y):
            continue
        clump(b, mat, (x, y, zfn(x, y) if zfn else 0.0), n=rng.randint(10, 22), radius=rng.uniform(0.05, 0.12), hmin=hmin, hmax=hmax, rng=rng, spread=spread)
        k += 1


def leaf_litter(b, mat, center, size, count, rng, scale=1.0, avoid=None, z=0.012):
    cx, cy = center
    sx, sy = size if isinstance(size, (tuple, list)) else (size, size)
    k = 0
    tries = 0
    while k < count and tries < count * 6:
        tries += 1
        a = rng.uniform(0, 6.283)
        r = math.sqrt(rng.random())
        x, y = cx + math.cos(a) * r * sx, cy + math.sin(a) * r * sy
        if avoid and avoid(x, y):
            continue
        az = rng.uniform(0, 6.283)
        d = V(math.cos(az), math.sin(az), rng.uniform(0.0, 0.12))
        L = rng.uniform(0.05, 0.1) * scale
        b.leaf(V(x, y, z + rng.uniform(0, 0.01)), d.normalized(), UP, L, L * rng.uniform(0.45, 0.7), mat, curl=rng.uniform(0.0, 0.6), twist=rng.uniform(-0.5, 0.5), rand=rng.random(), seg=3, shape="ovate", fold=0.35)
        k += 1


def twigs(b, mat, center, size, count, rng, avoid=None):
    cx, cy = center
    sx, sy = size if isinstance(size, (tuple, list)) else (size, size)
    for _ in range(count):
        a = rng.uniform(0, 6.283)
        r = math.sqrt(rng.random())
        x, y = cx + math.cos(a) * r * sx, cy + math.sin(a) * r * sy
        if avoid and avoid(x, y):
            continue
        az = rng.uniform(0, 6.283)
        d = V(math.cos(az), math.sin(az), 0)
        L = rng.uniform(0.12, 0.4)
        p = V(x, y, 0.012)
        pts = [p, p + d * L * 0.5 + V(0, 0, 0.006 * rng.random()), p + d * L + V(0, 0, 0.004)]
        b.tube(pts, [0.005, 0.0045, 0.003], mat, sides=5, cap_a=True, cap_b=True)
