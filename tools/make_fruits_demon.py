"""Fruits du démon (One Piece) : modèles LISSES faits de pièces, une forme par fruit, plein de petites spirales.

Usage :
    python tools/make_fruits_demon.py SORTIE.blend      # génère la scène (nécessite `pip install bpy`, Pillow, numpy)
    python tools/make_fruits_demon.py --stats           # compte les faces par fruit, sans Blender

Chaque fruit = UN SEUL maillage lisse (pas de pixels, pas de cubes) assemblé à partir de pièces fusionnées :
corps (révolution / surface implicite), tiges et feuilles (tubes), pointes, pétales, cornes, lames, bosses...
La peau est une petite texture de spirales (seamless, 6x6 spirales qui s'enroulent dans les deux sens) projetée
en « box » sur l'objet : de très nombreuses petites spirales sur tout le fruit pour quelques Ko, et aucune UV.
Les 26 présentoirs / plateaux / étiquettes forment un seul objet.

Les formes suivent les descriptions de l'œuvre retrouvées par recherche web (voir README) ; certains fruits n'ont pas
de design officiel (Hie Hie) ou plusieurs designs selon les sources.
"""
import math
import random
import sys

import numpy as np

SC = 0.18          # unités de forme -> unités Blender (un fruit fait ~22 unités de large)
SW = 2.7           # diamètre d'une petite spirale (unités de forme)


# ======================================================================= géométrie
class Geo:
    def __init__(self, v, f):
        self.v = np.asarray(v, float).reshape(-1, 3)
        self.f = [tuple(t) for t in f]

    def xf(self, M=None, t=(0, 0, 0)):
        v = self.v if M is None else self.v @ np.asarray(M, float).T
        return Geo(v + np.asarray(t, float), self.f)


def merge(geos):
    vs, fs, o = [], [], 0
    for g in geos:
        vs.append(g.v)
        fs.extend(tuple(i + o for i in f) for f in g.f)
        o += len(g.v)
    return Geo(np.concatenate(vs), fs)


def rings_to_geo(rings):
    vs, offs, o = [], [], 0
    for r in rings:
        vs.append(r)
        offs.append(o)
        o += len(r)
    f = []
    for k in range(len(rings) - 1):
        A, B, a0, b0 = rings[k], rings[k + 1], offs[k], offs[k + 1]
        if len(A) == 1 and len(B) == 1:
            continue
        n = len(B) if len(A) == 1 else len(A)
        for j in range(n):
            j2 = (j + 1) % n
            if len(A) == 1:
                f.append((a0, b0 + j2, b0 + j))
            elif len(B) == 1:
                f.append((a0 + j, a0 + j2, b0))
            else:
                f.append((a0 + j, a0 + j2, b0 + j2, b0 + j))
    return Geo(np.concatenate(vs), f)


def rot(ax=0.0, ay=0.0, az=0.0):
    ax, ay, az = map(math.radians, (ax, ay, az))
    X = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    Y = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    Z = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    return Z @ Y @ X


def orient(d):
    """Matrice qui envoie l'axe z sur la direction d."""
    d = np.asarray(d, float)
    d = d / np.linalg.norm(d)
    a = np.array([0, 0, 1.0])
    v = np.cross(a, d)
    c = float(a @ d)
    if np.linalg.norm(v) < 1e-9:
        return np.eye(3) if c > 0 else np.diag([1, -1, -1.0])
    K = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + K + K @ K / (1 + c)


def catmull(pts, m=4):
    P = [np.asarray(p, float) for p in pts]
    if len(P) < 3:
        return [p for p in P] if m <= 1 else [P[0] + (P[-1] - P[0]) * t / m for t in range(m + 1)]
    Q = [P[0]] + P + [P[-1]]
    out = []
    for i in range(1, len(Q) - 2):
        p0, p1, p2, p3 = Q[i - 1], Q[i], Q[i + 1], Q[i + 2]
        for s in range(m):
            t = s / m
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-1])
    return out


def lathe(profile, n=28, mod=None, smooth=4):
    """Surface de révolution autour de z. profile = [(r, z), ...] ; r=0 en bout = pôle."""
    pr = [np.array(p, float) for p in catmull(profile, smooth)] if smooth else [np.array(p, float) for p in profile]
    ph = np.arange(n) * 2 * math.pi / n
    rings = []
    for r, z in pr:
        if r < 1e-6:
            rings.append(np.array([[0, 0, z]]))
        else:
            k = np.array([mod(p, z) for p in ph]) if mod else 1.0
            rings.append(np.stack([r * k * np.cos(ph), r * k * np.sin(ph), np.full(n, z)], 1))
    return rings_to_geo(rings)


def ellipsoid(c, r, rotm=None, n=20, nv=11):
    prof = [(0, -1)] + [(math.sin(math.pi * j / nv), -math.cos(math.pi * j / nv)) for j in range(1, nv)] + [(0, 1)]
    g = lathe(prof, n=n, smooth=0)
    g = Geo(g.v * np.asarray(r, float), g.f)
    return g.xf(rotm, c)


def star(f, c, rmax, nu=36, nv=22):
    """Surface implicite f(P) <= 0 étoilée par rapport à c (bissection le long de chaque rayon)."""
    c = np.asarray(c, float)
    dirs, shape = [], []
    th = [math.pi * j / nv for j in range(1, nv)]
    ph = np.arange(nu) * 2 * math.pi / nu
    D = [np.array([0, 0, 1.0])]
    for t in th:
        for p in ph:
            D.append(np.array([math.sin(t) * math.cos(p), math.sin(t) * math.sin(p), math.cos(t)]))
    D.append(np.array([0, 0, -1.0]))
    D = np.array(D)
    lo, hi = np.zeros(len(D)), np.full(len(D), float(rmax))
    for _ in range(30):
        mid = (lo + hi) / 2
        inside = f(c + D * mid[:, None]) <= 0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    V = c + D * lo[:, None]
    rings = [V[:1]] + [V[1 + k * nu:1 + (k + 1) * nu] for k in range(nv - 1)] + [V[-1:]]
    return rings_to_geo(rings)


def metaball_profile(balls, thr=1.0, zs=None, p=1.5, n=28):
    """Profil d'une poire lisse : somme de boules (z, R) fusionnées (metaballs), solide de révolution."""
    def r_at(z):
        def fld(r):
            return sum((R * R / (r * r + (z - zc) ** 2 + 1e-9)) ** p for zc, R in balls)
        if fld(0) < thr:
            return None
        lo, hi = 0.0, 3.0 * max(R for _, R in balls)
        for _ in range(40):
            mid = (lo + hi) / 2
            if fld(mid) >= thr:
                lo = mid
            else:
                hi = mid
        return lo
    zlo = min(zc - R for zc, R in balls)
    zhi = max(zc + R for zc, R in balls)
    zz = np.linspace(zlo, zhi, 90)
    pts = [(r_at(z), z) for z in zz]
    pts = [(r, z) for r, z in pts if r is not None]
    z0, z1 = pts[0][1], pts[-1][1]
    pts = [(0, z0 - 0.4)] + pts[::3] + [pts[-1]] + [(0, z1 + 0.3)]
    return pts


def tube(points, r0, r1=None, sy=1.0, n=8, up=(0, 0, 1), seg=None, pw=1.0, smooth=True):
    """Tube (ou lame si sy<1) balayé le long d'une courbe, rayon qui s'effile r0 -> r1, bouts fermés."""
    r1 = r0 if r1 is None else r1
    if smooth and len(points) <= 6:
        P = catmull(points, seg or (1 if len(points) == 2 else 4))
    else:
        P = [np.asarray(p, float) for p in points]
    P = np.array(P)
    m = len(P)
    T = np.zeros_like(P)
    T[1:-1] = P[2:] - P[:-2]
    T[0], T[-1] = P[1] - P[0], P[-1] - P[-2]
    T /= np.linalg.norm(T, axis=1)[:, None]
    N = np.asarray(up, float)
    N = N - T[0] * (N @ T[0])
    if np.linalg.norm(N) < 1e-6:
        N = np.cross(T[0], [1.0, 0, 0] if abs(T[0][0]) < 0.9 else [0, 1.0, 0])
    N /= np.linalg.norm(N)
    ang = np.arange(n) * 2 * math.pi / n
    rings = [P[:1] - T[0:1] * 0.0]
    for i in range(m):
        if i:
            N = N - T[i] * (N @ T[i])
            N /= np.linalg.norm(N)
        B = np.cross(T[i], N)
        t = i / (m - 1)
        r = r0 + (r1 - r0) * t ** pw
        rings.append(P[i] + np.outer(np.cos(ang), N) * r * sy + np.outer(np.sin(ang), B) * r)
    rings.append(P[-1:] + T[-1:] * r1 * 0.5)
    rings[0] = P[:1] - T[0:1] * r0 * 0.3
    return rings_to_geo(rings)


# ======================================================================= pièces communes
GREEN = (0.28, 0.50, 0.18)
LEAF = (0.36, 0.64, 0.22)


def fib(n, zmin_=-1.0, zmax_=1.0):
    out = []
    for i in range(n):
        z = zmin_ + (zmax_ - zmin_) * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        a = i * 2.399963229728653
        out.append((r * math.cos(a), r * math.sin(a), z))
    return out


def leaf(c, r, rotz=0.0, ry=0.0):
    return ellipsoid(c, r, rot(0, ry, rotz), n=12, nv=6)


def stem_T(z, h=3.0, half=4.5):
    """Tige en T (la marque des fruits du démon)."""
    g = [tube([(0, 0, z - 1), (0, 0, z + h * 0.5), (0, 0, z + h)], 1.1, 0.95, n=8)]
    g.append(tube([(-half, 0, z + h - 0.8), (0, 0, z + h + 0.4), (half, 0, z + h - 0.8)], 1.0, 1.0, n=8))
    return merge(g)


def curl_stem(z, h=6.0, k=1.0):
    return tube([(0, 0, z - 2), (0, 0, z + h * 0.6), (1.2 * k, 0, z + h), (3.2 * k, 0, z + h + 1.0), (4.6 * k, 0, z + h)],
                1.2, 0.8, n=8)


def spike(base, tip, r, n=6):
    return tube([base, tip], r, 0.0, n=n, smooth=False)


# ======================================================================= les fruits
# chaque fruit rend (pièces, peaux) :  pièces = [(Geo, clé)]  clé = indice de peau (spirales) ou couleur plate
#                                      peaux  = {indice: (couleur de base, couleur des spirales)}
def f_gomu():
    return ([(ellipsoid((0, 0, 0), (12, 12, 11.5), n=32, nv=16), 0), (curl_stem(10, 5, 1), GREEN),
             (leaf((-2.4, 0, 14.4), (2.8, 1.0, 1.2), 0, -20), LEAF), (leaf((2.6, 0, 13.3), (2.6, 1.0, 1.1), 0, 25), LEAF)],
            {0: ((0.45, 0.17, 0.55), (0.80, 0.47, 0.88))})


def f_mera():
    body = ellipsoid((0, 0, -1), (10, 10, 9), n=28, nv=14)
    T = [((0, 0, 3), (0.5, 0, 12), (1.5, 0, 22), 6.0), ((-5, 0, 2), (-8, 0, 8), (-9.5, 0, 16), 4.6),
         ((5, 0, 2), (7.5, 0, 9), (8.8, 0, 17.5), 4.6), ((0, -4.5, 2), (-0.5, -5.5, 7), (-0.5, -6.3, 12.5), 4.0),
         ((0, 4.5, 2), (0.5, 5.5, 8), (1, 6, 14.5), 4.0), ((-3, 3, 2), (-4, 3.6, 7), (-5, 4, 12.5), 3.2),
         ((3, -3, 2), (4, -3.8, 7), (5, -4.6, 13), 3.2)]
    tong = [tube(list(p[:3]), p[3], 0.3, n=10, seg=5) for p in T]
    return ([(body, 0), (merge(tong), 1)],
            {0: ((0.96, 0.44, 0.08), (0.80, 0.12, 0.05)), 1: ((1.0, 0.78, 0.16), (0.96, 0.42, 0.08))})


def heart_f(k):
    def f(P):
        X, Y, Z = P[:, 0] / k, P[:, 1] / k, P[:, 2] / k
        return (X * X + 2.25 * Y * Y + Z * Z - 1) ** 3 - X * X * Z ** 3 - 0.1125 * Y * Y * Z ** 3
    return f


def heart(k, c=(0, 0, 0), rotm=None):
    g = star(heart_f(k), (0, 0, 0.1 * k), 1.8 * k, nu=44, nv=28)
    return g.xf(rotm, c), 1.05 * k


def f_ope():
    h, top = heart(8.6)
    return ([(h, 0), (stem_T(top - 4, 4, 4.5), GREEN)], {0: ((0.80, 0.07, 0.12), (1.0, 0.50, 0.55))})


def f_mero():
    ra, rb = rot(0, -18, 0), rot(0, 18, 0)
    a, ta = heart(6.4, (-6.6, 0, 0), ra)
    b, _ = heart(6.4, (6.6, 0, 0), rb)
    za = 6.4 + 1
    stems = [tube([(-6.6 + 1.5, 0, za - 2), (-4.5, 0, za + 1), (-2, 0, za + 4), (0, 0, za + 6)], 0.9, 0.9),
             tube([(6.6 - 1.5, 0, za - 2), (4.5, 0, za + 1), (2, 0, za + 4), (0, 0, za + 6)], 0.9, 0.9),
             tube([(0, 0, za + 5.5), (0, 0, za + 9)], 1.0, 0.9), leaf((1.8, 0, za + 8), (2.8, 1.0, 1.1), 0, 25)]
    return ([(a, 0), (b, 1)] + [(s, GREEN) for s in stems],
            {0: ((0.88, 0.08, 0.14), (1.0, 0.55, 0.60)), 1: ((0.55, 0.20, 0.66), (0.85, 0.60, 0.92))})


def f_ito():
    pr = metaball_profile([(0, 11.0), (9.5, 6.8)])
    body = lathe(pr, n=32, smooth=0)
    zt = max(p[1] for p in pr)
    pts = [(2.4 * math.cos(a) * (1 - 0.3 * t), 2.4 * math.sin(a) * (1 - 0.3 * t), zt - 1 + 11 * t)
           for a, t in ((i / 33 * 2.6 * 2 * math.pi, i / 33) for i in range(34))]
    return ([(body, 0), (tube(pts, 0.95, 0.7, n=7, smooth=False), (0.86, 0.12, 0.55))],
            {0: ((0.80, 0.68, 0.93), (0.96, 0.90, 1.0))})


def f_doru():
    pr = metaball_profile([(0, 11.0), (9.0, 7.2)])
    zt = max(p[1] for p in pr) - 2.0
    prof = [(0, pr[0][1])] + [(r, z) for r, z in pr[1:-1] if z < zt - 0.3]
    rim = prof[-1][0]
    prof += [(rim * 0.9, zt), (rim * 0.62, zt + 0.1), (rim * 0.55, zt - 1.0), (rim * 0.3, zt - 1.7), (0, zt - 1.8)]
    body = lathe(prof, n=32, smooth=0)
    rng = random.Random(5)
    parts = []
    for q in range(13):
        a = q * 2 * math.pi / 13 + rng.uniform(-0.2, 0.2)
        ln = rng.uniform(4, 12)
        rr = rim + 0.2
        pts = [(rr * math.cos(a), rr * math.sin(a), zt), (rr * 1.12 * math.cos(a), rr * 1.12 * math.sin(a), zt - ln * 0.5),
               (rr * 1.18 * math.cos(a), rr * 1.18 * math.sin(a), zt - ln)]
        parts.append(tube(pts, 1.3, 0.9, n=7))
        parts.append(ellipsoid((rr * 1.19 * math.cos(a), rr * 1.19 * math.sin(a), zt - ln - 0.6), (1.7, 1.7, 1.9), n=10, nv=6))
    parts.append(tube([(0, 0, zt - 3), (0, 0, zt + 3.2)], 0.8, 0.5, n=6))
    cream = merge(parts[:-1])
    return ([(body, 0), (cream, (1.0, 0.86, 0.50)), (parts[-1], (0.20, 0.12, 0.10))],
            {0: ((0.97, 0.97, 0.95), (0.78, 0.80, 0.86))})


def f_ushi():
    prof = []
    for j in range(0, 27):
        z = -13 + j
        t = z / 13.0
        r = 12.0 * math.sqrt(max(0.0, 1 - t * t)) * (0.55 + 0.45 * min(1.0, max(0.0, (z + 13) / 22.0)))
        prof.append((r if 0 < j < 26 else 0, z))
    body = lathe(prof, n=32, smooth=0)
    zt = 12.5
    horns = [tube([(s * 9, 0, zt - 6), (s * 14, 0, zt - 4.5), (s * 17, 0, zt + 1.5), (s * 15.5, 0, zt + 6.5)], 2.4, 0.4, n=10)
             for s in (-1, 1)]
    calyx = [tube([(0, 0, zt - 0.3), (3.0 * math.cos(a), 3.0 * math.sin(a), zt + 1.4), (6.2 * math.cos(a), 6.2 * math.sin(a), zt + 0.4)],
                  1.7, 0.5, sy=0.3, n=6, up=(0, 0, 1)) for a in [k * 2 * math.pi / 7 for k in range(7)]]
    return ([(body, 0), (merge(horns), (0.95, 0.92, 0.82)), (merge(calyx), LEAF),
             (tube([(0, 0, zt), (0, 0, zt + 4.5)], 1.0, 0.9, n=7), GREEN)],
            {0: ((0.07, 0.07, 0.10), (0.30, 0.30, 0.38))})


def f_neko():
    head = ellipsoid((0, 0, 0), (12.5, 9.5, 10), n=32, nv=16)
    snout = ellipsoid((0, -8, -3.5), (5.5, 3.6, 3.6), n=20, nv=10)
    nose = ellipsoid((0, -11.2, -1.5), (1.6, 1.0, 1.1), n=10, nv=6)
    ears = [ellipsoid((s * 8.2, 0, 9), (4.4, 3.2, 4.4), n=16, nv=8) for s in (-1, 1)]
    rng = random.Random(21)
    dark, mid = [], []
    for d in fib(30, -0.5, 0.95):
        if d[1] < -0.55 and d[2] < 0.1:
            continue
        sz = rng.uniform(1.7, 2.6)
        p = np.array([d[0] * 12.5, d[1] * 9.5, d[2] * 10]) * 0.985
        nrm = np.array([d[0] / 12.5, d[1] / 9.5, d[2] / 10])
        M = orient(nrm)
        dark.append(ellipsoid(p, (sz, sz, 0.7), M, n=12, nv=4))
        mid.append(ellipsoid(p * 1.003, (sz * 0.5, sz * 0.5, 0.95), M, n=10, nv=4))
    return ([(head, 0), (snout, (0.99, 0.90, 0.68)), (nose, (0.16, 0.08, 0.08)), (merge(ears), 1),
             (merge(dark), (0.30, 0.17, 0.08)), (merge(mid), (0.82, 0.55, 0.20)), (stem_T(9.4, 3, 4), GREEN)],
            {0: ((0.95, 0.76, 0.30), (0.78, 0.50, 0.14)), 1: ((0.95, 0.76, 0.30), (0.30, 0.17, 0.08))})


def f_nikyu():
    lumps = [ellipsoid((-7, 0, 10.5), (4.4, 4, 4), n=16, nv=8), ellipsoid((0, 0, 13), (4.6, 4.2, 4.4), n=16, nv=8),
             ellipsoid((7, 0, 10.5), (4.4, 4, 4), n=16, nv=8)]
    return ([(ellipsoid((0, 0, 0), (12, 11, 11), n=32, nv=16), 0), (merge(lumps), 1), (stem_T(16.5, 3, 4), GREEN)],
            {0: ((0.97, 0.72, 0.66), (0.80, 0.42, 0.40)), 1: ((0.92, 0.55, 0.55), (0.70, 0.30, 0.34))})


def f_hana():
    core = ellipsoid((0, 0, 0), (8.5, 8.5, 7.5), n=24, nv=12)
    pet = []
    for i, d in enumerate(fib(70, -0.35, 1.0)):
        ln = 15.5 if i % 2 == 0 else 13
        b = np.array([d[0] * 6, d[1] * 6, d[2] * 5.5])
        tip = np.array([d[0] * ln, d[1] * ln, d[2] * ln * 0.9 + 1])
        mid = (b + tip) / 2 + np.array([d[0], d[1], 0]) * 1.3
        h = (d[0], d[1], 0) if math.hypot(d[0], d[1]) > 0.2 else (1, 0, 0)
        pet.append(tube([b, mid, tip], 2.7, 0.5, sy=0.3, n=6, up=h, seg=2))
    top = 15.0
    return ([(merge(pet), 0), (core, 1), (tube([(0, 0, top - 3), (0, 0, top + 5)], 1.1, 0.9, n=7), GREEN),
             (leaf((2.5, 0, top + 2), (3.0, 1.0, 1.2), 0, 25), LEAF)],
            {0: ((0.96, 0.62, 0.78), (0.78, 0.25, 0.50)), 1: ((0.82, 0.22, 0.45), (1.0, 0.80, 0.50))})


def f_suna():
    def mod(p, z):
        return 1 - 0.12 * (0.5 + 0.5 * math.cos(8 * p))
    prof = [(0, -12.5)] + [(11.0 * math.sin(math.pi * j / 14), -12.5 * math.cos(math.pi * j / 14)) for j in range(1, 14)] + [(0, 12.5)]
    body = lathe(prof, n=48, mod=mod, smooth=0)
    arms = []
    for s in (-1, 1):
        arms.append(tube([(s * 9.5, 0, -2), (s * 13.2, 0, 0), (s * 13.6, 0, 6), (s * 13.6, 0, 12)], 3.4, 3.1, n=14))
        arms.append(ellipsoid((s * 13.6, 0, 12.2), (3.1, 3.1, 2.6), n=14, nv=6))
    sp = []
    for k in range(8):
        ph = k * math.pi / 4
        for z in (-8, -4, 0, 4, 8):
            rr = 11.0 * math.sqrt(1 - (z / 12.5) ** 2) * 0.99
            sp.append(spike((rr * math.cos(ph), rr * math.sin(ph), z), (rr * 1.12 * math.cos(ph), rr * 1.12 * math.sin(ph), z + 0.3), 0.35, 4))
    return ([(body, 0), (merge(arms), 0), (merge(sp), (1.0, 0.97, 0.82)), (stem_T(12.0, 3, 4.5), GREEN)],
            {0: ((0.86, 0.72, 0.46), (0.62, 0.46, 0.24))})


def f_bara():
    bumps = [ellipsoid((d[0] * 7.8, d[1] * 7.8, d[2] * 10.8), (3.1, 3.1, 3.1), n=10, nv=6) for d in fib(96)]
    core = ellipsoid((0, 0, 0), (8.5, 8.5, 11.5), n=20, nv=10)
    crown = [tube([(0, 0, 10), (2.5 * math.cos(a), 2.5 * math.sin(a), 13), (5 * math.cos(a), 5 * math.sin(a), 15.5)], 1.5, 0.4,
                  sy=0.3, n=6, seg=2, up=(0, 0, 1)) for a in [k * 2 * math.pi / 6 for k in range(6)]]
    return ([(merge([core] + bumps), 0), (merge(crown), LEAF)], {0: ((0.92, 0.32, 0.14), (0.99, 0.80, 0.30))})


def f_mochi():
    pts = [(0, 15.5), (5, 14.5), (9, 11.5), (10.8, 6), (9.6, 1.5), (6.5, -1.5), (5.4, -3.5), (7.5, -6), (9.8, -8.5),
           (10.2, -10.5), (9, -11.2), (0, -11.2)]
    return ([(lathe(pts, n=36, smooth=4), 0), (curl_stem(14, 4.5, 0.9), GREEN)], {0: ((0.99, 0.94, 0.84), (0.95, 0.66, 0.60))})


def f_bomu():
    pts = [(0, 8.3), (3.5, 9.4), (7, 10.4), (10.5, 8.5), (11.5, 3), (10.5, -4), (7, -9.5), (3.5, -11), (0, -11.2)]
    rope = tube([(0, 0, 8), (0, 0, 13), (1.6, 0, 16.5), (3.8, 0, 18.5)], 1.5, 1.1, n=8)
    rng = random.Random(8)
    fr = [spike((3.8, 0, 18.5), (3.8 + 2.4 * math.cos(a), 2.4 * math.sin(a), 20.5 + rng.uniform(0, 2)), 0.7, 4)
          for a in (rng.uniform(0, 6.28) for _ in range(13))]
    spark = [ellipsoid((4.6, 0, 21.2), (1.4, 1.4, 1.4), n=8, nv=5), ellipsoid((3.2, 0, 22.2), (1.0, 1.0, 1.0), n=8, nv=5),
             ellipsoid((5.6, 1.4, 22.8), (0.7, 0.7, 0.7), n=8, nv=5)]
    return ([(lathe(pts, n=36, smooth=4), 0), (merge([rope] + fr), (0.95, 0.80, 0.28)), (merge(spark), (1.0, 0.45, 0.10))],
            {0: ((0.30, 0.12, 0.40), (0.66, 0.40, 0.84))})


def f_gura():
    pr = metaball_profile([(-2, 11.5), (9.5, 6.4)])
    body = lathe(pr, n=36, smooth=0)
    zt = max(p[1] for p in pr)
    rz = lambda z: max((r for r, zz in pr if abs(zz - z) < 0.6), default=3.0)
    rng = random.Random(3)
    cr = []
    zb = pr[0][1]
    for k in range(5):
        ph = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
        pts = []
        for j in range(14):
            ph += rng.uniform(-0.3, 0.3)
            z = zb + 0.6 + j * 1.15
            r = rz(z) * 0.985
            pts.append((r * math.cos(ph), r * math.sin(ph), z))
        cr.append(tube(pts, 0.45, 0.2, n=5, smooth=False))
    return ([(body, 0), (merge(cr), (0.04, 0.08, 0.22)), (tube([(0, 0, zt - 1), (0, 0, zt + 5)], 1.1, 0.9, n=7), GREEN),
             (leaf((2.8, 0, zt + 3.2), (3.0, 1.0, 1.2), 0, 25), LEAF)],
            {0: ((0.30, 0.55, 0.95), (0.68, 0.84, 1.0))})


def f_goro():
    pts = [(0, -12.5), (6, -11), (10.2, -6), (10.6, -1), (9.5, 4), (7, 9), (4.2, 13), (2.6, 15.5), (0, 15.8)]
    body = lathe(pts, n=36, smooth=4)
    sp = []
    for d in fib(46, -0.6, 0.8):
        b = np.array([d[0] * 9.8, d[1] * 9.8, d[2] * 10 - 1.5])
        sp.append(spike(b, b + np.array(d) * 4.8, 1.4, 5))
    zt = 15.8
    zig = tube([(0, 0, zt - 1), (2.2, 0, zt + 2), (-1.4, 0, zt + 4.5), (2.8, 0, zt + 7.5), (-0.6, 0, zt + 9.5)], 1.0, 0.8, n=7)
    bar = tube([(-3.5, 0, zt + 1.5), (3.5, 0, zt + 1.5)], 0.9, 0.9, n=7)
    return ([(body, 0), (merge(sp), (1.0, 0.98, 0.72)), (merge([zig, bar]), GREEN)],
            {0: ((0.99, 0.84, 0.22), (1.0, 0.97, 0.62))})


def f_magu():
    cs = [(d[0] * 8.2, d[1] * 8.2, d[2] * 8.2) for d in fib(38)]
    g = merge([ellipsoid((0, 0, 0), (9.5, 9.5, 9.5), n=20, nv=10)] + [ellipsoid(c, (4.6, 4.6, 4.6), n=12, nv=7) for c in cs])
    hx = [(2.2 * math.cos(i / 31 * 2.2 * 2 * math.pi), 2.2 * math.sin(i / 31 * 2.2 * 2 * math.pi), 12 + 9 * i / 31) for i in range(32)]
    return ([(g, 0), (tube(hx, 1.0, 0.7, n=7, smooth=False), (0.95, 0.50, 0.10))], {0: ((0.42, 0.04, 0.04), (1.0, 0.52, 0.10))})


def f_yami():
    ds = fib(84)
    prof = [(0, 0), (2.9, 1.0), (2.9, 3.5), (1.5, 7.0), (0, 10.8)]
    drop = lathe(prof, n=7, smooth=2)
    parts = [ellipsoid((0, 0, 0), (9.5, 9.5, 9.5), n=20, nv=10)]
    for d in ds:
        parts.append(drop.xf(orient(d), np.array(d) * 8.6))
    crown = [tube([(0, 0, 10), (3 * math.cos(a), 3 * math.sin(a), 14), (6 * math.cos(a), 6 * math.sin(a), 17)], 1.8, 0.4,
                  sy=0.3, n=6, seg=2) for a in [k * 2 * math.pi / 7 for k in range(7)]]
    return ([(merge(parts), 0), (merge(crown), LEAF)], {0: ((0.66, 0.56, 0.86), (0.38, 0.28, 0.62))})


def f_tori():
    body = ellipsoid((0, 0, 0), (9.8, 9.8, 13), n=32, nv=16)
    sp = []
    for ring in range(9):
        z = -10.5 + 2.6 * ring
        rz = 9.4 * math.sqrt(max(0.0, 1 - (z / 13) ** 2))
        for k in range(13):
            a = (k + 0.5 * (ring % 2)) * 2 * math.pi / 13
            c = np.array([math.cos(a) * rz, math.sin(a) * rz, z])
            sp.append(spike(c, c * 1.18 + np.array([0, 0, 0.6]), 1.3, 5))
    parts = [(body, 0), (merge(sp), (0.30, 0.58, 0.24))]
    for k in range(10):
        a = k * 2 * math.pi / 10
        col = (0.16, 0.50, 0.98) if k % 2 == 0 else (1.0, 0.85, 0.2)
        tip = 24 + (k % 2) * 3
        parts.append((tube([(0.6 * math.cos(a), 0.6 * math.sin(a), 12), (3.2 * math.cos(a), 3.2 * math.sin(a), 18),
                            (6.5 * math.cos(a), 6.5 * math.sin(a), tip)], 1.9, 0.3, sy=0.35, n=6, seg=2, up=(math.cos(a), math.sin(a), 0)), col))
    return (parts, {0: ((0.50, 0.76, 0.36), (0.16, 0.38, 0.14))})


def f_yomi():
    feet = [ellipsoid((sx * 6.4, sy * 6.4, -10), (3.8, 3.8, 3.4), n=14, nv=8) for sx in (-1, 1) for sy in (-1, 1)]
    return ([(merge([ellipsoid((0, 0, 0), (11.5, 11.5, 11), n=32, nv=16)] + feet), 0), (curl_stem(9, 4.5, 1), GREEN),
             (leaf((-2.6, 0, 13.4), (3.0, 1.0, 1.2), 0, -25), LEAF)], {0: ((0.88, 0.66, 0.22), (0.55, 0.34, 0.08))})


def f_kage():
    lv = []
    for c, d in (((-9.5, 0, 6), (-1, 0, 0.9)), ((-11, -3, 2.5), (-1, -0.5, 0.2)), ((-11, 3, 2.5), (-1, 0.5, 0.2))):
        d = np.array(d) / np.linalg.norm(d)
        lv.append(ellipsoid(c, (3.2, 3.0, 3.0), n=12, nv=7))
        lv.append(spike(np.array(c), np.array(c) + d * 8, 3.0, 8))
    return ([(ellipsoid((0, 0, 0), (11.5, 11.5, 11), n=32, nv=16), 0), (curl_stem(9, 4.5, 1), GREEN), (merge(lv), (0.30, 0.62, 0.25))],
            {0: ((0.05, 0.05, 0.07), (0.32, 0.32, 0.40))})


def f_hobi():
    def disc(sx):
        p = [(0, -1.6), (7, -1.6), (10.3, -1.0), (10.8, 0), (10.3, 1.0), (7, 1.6), (0, 1.6)]
        g = lathe(p, n=40, smooth=2)
        return g.xf(rot(0, 90, 0) @ np.eye(3), (sx * 6.0, 0, 0))
    rim = lathe([(0, -4), (11.6, -4), (11.8, -3), (11.8, 3), (11.6, 4), (0, 4)], n=40, smooth=0).xf(rot(0, 90, 0))
    eight = []
    for i in range(53):
        t = i / 52 * 2 * math.pi
        den = 1 + math.sin(t) ** 2
        eight.append((4.8 * math.cos(t) / den, 0, 16.2 + 5.9 * math.sin(t) * math.cos(t) / den))
    return ([(rim, 0), (merge([disc(-1), disc(1)]), 1), (tube([(0, 0, 9), (0, 0, 14)], 1.3, 1.1, n=8), GREEN),
             (tube(eight, 0.95, 0.95, n=7, smooth=False), GREEN)],
            {0: ((0.86, 0.10, 0.12), (0.55, 0.04, 0.06)), 1: ((0.98, 0.95, 0.60), (0.88, 0.70, 0.18))})


def f_supa():
    bl = []
    for dx in (-12, -6, 0, 6, 12):
        L = 22 - abs(dx) * 0.35
        bl.append(tube([(0, 0, -12), (dx * 0.35, 0, 0), (dx * 0.8, 0, L - 10), (dx * 1.05, 0, L - 1)], 4.4, 0.9, sy=0.28, n=10,
                       up=(0, 1, 0), seg=4))
    return ([(merge(bl), 0), (tube([(0, 0, -16), (0, 0, -10)], 1.8, 1.6, n=8), (0.45, 0.60, 0.25))],
            {0: ((0.82, 0.85, 0.90), (0.14, 0.24, 0.56))})


def f_sube():
    def f(P):
        x, y, z = P[:, 0], P[:, 1], P[:, 2]
        k = 1 - 0.11 * np.exp(-(x / 2.4) ** 2) * np.where(y < 0, 1.0, 0.35)
        return (x / (11.5 * k)) ** 2 + (y / (11 * k)) ** 2 + (z / (11 * k)) ** 2 - 1
    return ([(star(f, (0, 0, 0), 14, nu=40, nv=24), 0), (curl_stem(9.5, 3.5, 0.8), GREEN),
             (leaf((3.2, 0, 12), (3.6, 1.0, 1.3), 0, 25), LEAF)], {0: ((0.98, 0.66, 0.72), (1.0, 0.90, 0.92))})


def f_pika():
    pts = [(0, 14), (3.4, 13.3), (5.6, 11.6), (6.0, 9), (6.0, 3), (6.8, -1), (8.4, -4.5), (11, -7.8), (14.2, -10.6), (15.4, -11.3),
           (14.6, -12.3), (12.5, -11.3), (8, -8.8), (0, -7.5)]
    return ([(lathe(pts, n=44, smooth=3), 0),
             (tube([(0, 0, 13), (0, 0, 16.5), (1.4, 0, 18.5), (3.4, 0, 19), (4.8, 0, 17.7)], 1.2, 0.9, n=8), (0.55, 0.82, 0.98))],
            {0: ((0.98, 0.85, 0.22), (1.0, 0.97, 0.66))})


def f_hie():
    sh = []
    for i, d in enumerate(fib(22, -0.7, 0.8)):
        ln = 15.5 if i % 2 == 0 else 13
        sh.append(spike(np.array(d) * 7, np.array(d) * ln, 3.0, 5))
    return ([(ellipsoid((0, 0, 0), (9.2, 9.2, 9.2), n=28, nv=14), 0), (merge(sh), (0.83, 0.93, 1.0)),
             (tube([(0, 0, 8), (0, 0, 12), (1.4, 0, 14), (3.2, 0, 14.5)], 1.2, 0.9, n=8), (0.30, 0.78, 0.78))],
            {0: ((0.56, 0.80, 0.97), (0.90, 0.97, 1.0))})


FRUITS = [
    ("Gomu Gomu no Mi", f_gomu), ("Mera Mera no Mi", f_mera), ("Ope Ope no Mi", f_ope),
    ("Mero Mero no Mi", f_mero), ("Ito Ito no Mi", f_ito), ("Doru Doru no Mi", f_doru),
    ("Ushi Ushi no Mi Bison", f_ushi), ("Neko Neko no Mi Leopard", f_neko), ("Nikyu Nikyu no Mi", f_nikyu),
    ("Hana Hana no Mi", f_hana), ("Suna Suna no Mi", f_suna), ("Bara Bara no Mi", f_bara),
    ("Mochi Mochi no Mi", f_mochi), ("Bomu Bomu no Mi", f_bomu), ("Gura Gura no Mi", f_gura),
    ("Goro Goro no Mi", f_goro), ("Magu Magu no Mi", f_magu), ("Yami Yami no Mi", f_yami),
    ("Tori Tori no Mi Phoenix", f_tori), ("Yomi Yomi no Mi", f_yomi), ("Kage Kage no Mi", f_kage),
    ("Hobi Hobi no Mi", f_hobi), ("Supa Supa no Mi", f_supa), ("Sube Sube no Mi", f_sube),
    ("Pika Pika no Mi", f_pika), ("Hie Hie no Mi", f_hie),
]


def assemble(i):
    """(sommets, faces, clé de matière par face, liste des clés, peaux) du fruit i, en unités Blender."""
    parts, skins = FRUITS[i][1]()
    keys, V, F, M, o = [], [], [], [], 0
    for g, key in parts:
        if key not in keys:
            keys.append(key)
        ki = keys.index(key)
        V.append(g.v * SC)
        F.extend(tuple(j + o for j in f) for f in g.f)
        M.extend([ki] * len(g.f))
        o += len(g.v)
    V = np.concatenate(V)
    return V, F, M, keys, skins


# ======================================================================= peau : petites spirales seamless
def swirl_tile(rows=6, cols=6, px=1024):
    """Masque (0 = fond, 1 = trait) de petites spirales en quinconce, sens alternés ; se répète sans couture."""
    W = px
    H = int(round(px * rows * 0.8660254 / cols))
    ss = 2
    y, x = np.mgrid[0:H * ss, 0:W * ss].astype(np.float32)
    x /= ss * W / cols
    y /= ss * H / rows
    best = np.full(x.shape, 9.0, np.float32)
    arg = np.zeros(x.shape + (3,), np.float32)
    for rr in range(-1, rows + 1):
        for cc in range(-1, cols + 1):
            cx, cy = cc + 0.5 * (rr % 2) + 0.25, rr + 0.5
            # hauteur de ligne hexagonale : le pas vertical réel est 0.866 colonne -> on corrige dans l'espace y
            dx, dy = x - cx, (y - cy) * 0.8660254
            d = dx * dx + dy * dy
            m = d < best
            best = np.where(m, d, best)
            sgn = 1.0 if (((rr % rows) + (cc % cols)) % 2 == 0) else -1.0
            arg[..., 0] = np.where(m, dx, arg[..., 0])
            arg[..., 1] = np.where(m, dy, arg[..., 1])
            arg[..., 2] = np.where(m, sgn, arg[..., 2])
    rho = np.sqrt(best) / 0.5
    th = np.arctan2(arg[..., 1], arg[..., 0])
    s = rho * 1.7 + arg[..., 2] * th / (2 * math.pi)
    fr = s - np.floor(s)
    line = ((fr < 0.46) & (rho < 0.94)) | (rho < 0.12)
    from PIL import Image
    img = Image.fromarray((line * 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    return np.array(img).astype(np.float32) / 255.0, W, H


def make_image(name):
    import bpy
    a, W, H = swirl_tile()
    img = bpy.data.images.new(name, W, H, alpha=False)
    g = np.flipud(a)
    rgba = np.stack([g, g, g, np.ones_like(g)], -1)
    img.pixels.foreach_set(rgba.ravel())
    img.file_format = "PNG"
    img.pack()
    img.colorspace_settings.name = "Non-Color"
    return img, W, H


def skin_material(name, base, line, img, W, H):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.42
    co = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    cols = 6
    mp.inputs["Scale"].default_value = (1 / (cols * SW * SC), 1 / (cols * SW * SC * 0.866), 1 / (cols * SW * SC))
    tx = nt.nodes.new("ShaderNodeTexImage")
    tx.image = img
    tx.projection = "BOX"
    tx.projection_blend = 0.12
    tx.interpolation = "Linear"
    mx = nt.nodes.new("ShaderNodeMix")
    mx.data_type = "RGBA"
    mx.inputs[6].default_value = (*base, 1)
    mx.inputs[7].default_value = (*line, 1)
    bp = nt.nodes.new("ShaderNodeBump")
    bp.inputs["Strength"].default_value = 0.25
    bp.inputs["Distance"].default_value = 0.02
    nt.links.new(co.outputs["Object"], mp.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], tx.inputs["Vector"])
    nt.links.new(tx.outputs["Color"], mx.inputs[0])
    nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    nt.links.new(tx.outputs["Color"], bp.inputs["Height"])
    nt.links.new(bp.outputs["Normal"], b.inputs["Normal"])
    return m


def flat_material(name, color, rough=0.5):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def fruit_object(i, img, W, H, mat_cache):
    import bpy
    import bmesh
    V, F, M, keys, skins = assemble(i)
    name = FRUITS[i][0]
    me = bpy.data.meshes.new(f"Fruit_{name}")
    me.from_pydata([tuple(v) for v in V], [], F)
    for k in keys:
        if isinstance(k, int):
            base, line = skins[k]
            mk = ("skin", base, line)
            if mk not in mat_cache:
                mat_cache[mk] = skin_material(f"Peau_{len(mat_cache)}", base, line, img, W, H)
        else:
            mk = ("flat", k)
            if mk not in mat_cache:
                mat_cache[mk] = flat_material(f"Uni_{len(mat_cache)}", k)
        me.materials.append(mat_cache[mk])
    me.polygons.foreach_set("material_index", M)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    me.update()
    return me


def mesh_stats():
    rows = []
    for i in range(len(FRUITS)):
        V, F, M, keys, _ = assemble(i)
        rows.append((FRUITS[i][0], len(V), len(F)))
    return rows


# ======================================================================= scène
def simple_material(name, color, rough=0.7):
    return flat_material(name, color, rough)


def wood_floor():
    import bpy
    m = bpy.data.materials.new("Parquet")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.8
    co = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.20, 0.12, 0.07, 1)
    br.inputs["Color2"].default_value = (0.16, 0.09, 0.05, 1)
    br.inputs["Mortar"].default_value = (0.05, 0.03, 0.02, 1)
    br.inputs["Scale"].default_value = 0.5
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Brick Width"].default_value = 3.0
    br.inputs["Row Height"].default_value = 0.5
    nt.links.new(co.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    return m


def image_from_array(name, arr):
    import bpy
    AH, AW = arr.shape[0], arr.shape[1]
    img = bpy.data.images.new(name, AW, AH, alpha=False)
    img.pixels.foreach_set((arr.astype("float32") / 255.0).ravel())
    img.file_format = "PNG"
    img.pack()
    return img


def label_mat(img):
    import bpy
    m = bpy.data.materials.new("Etiquettes")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.55
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 0.9
    return m


def label_array(names):
    from PIL import Image, ImageDraw, ImageFont
    LW, LH, cols = 256, 24, 4
    rows = (len(names) + cols - 1) // cols
    img = Image.new("RGB", (LW * cols, LH * rows), (66, 40, 20))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=15)
    except TypeError:
        font = ImageFont.load_default()
    for i, n in enumerate(names):
        r, c = divmod(i, cols)
        box_ = d.textbbox((0, 0), n, font=font)
        d.text((c * LW + (LW - (box_[2] - box_[0])) / 2, r * LH + (LH - (box_[3] - box_[1])) / 2 - box_[1]), n,
               fill=(255, 205, 90), font=font)
    arr = np.flipud(np.array(img))
    rgba = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, np.uint8)], axis=2)
    return rgba, LW, LH, cols, rows


COLS, DX, DY = 9, 7.9, 10.2


def layout(i):
    n_row = [9, 9, len(FRUITS) - 18]
    row, col = divmod(i, COLS)
    n = n_row[row]
    return (col - (n - 1) / 2) * DX, row * DY, 1.5 + 2.8 * row


def stage_mesh(label_info):
    import bpy
    rgba, LW, LH, cols, rows = label_info
    verts, faces, mats, uvs = [], [], [], []

    def add_box(lo, hi, mat):
        b = len(verts)
        for x in (lo[0], hi[0]):
            for y in (lo[1], hi[1]):
                for z in (lo[2], hi[2]):
                    verts.append((x, y, z))
        for f in ((0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)):
            faces.append(tuple(b + i for i in f))
            mats.append(mat)
            uvs.extend([(0, 0)] * 4)
    for i in range(len(FRUITS)):
        wx, wy, h = layout(i)
        add_box((wx - 3.4, wy - 3.5, 0), (wx + 3.4, wy + 3.5, h), 0)
        add_box((wx - 3.55, wy - 3.65, h), (wx + 3.55, wy + 3.65, h + 0.18), 1)
        r, c = divmod(i, cols)
        x0, y0 = c * LW / (LW * cols), (rows - 1 - r) * LH / (LH * rows)
        x1, y1 = x0 + 1.0 / cols, y0 + 1.0 / rows
        b, z = len(verts), h + 0.19
        verts.extend([(wx - 3.2, wy - 3.35, z), (wx + 3.2, wy - 3.35, z), (wx + 3.2, wy - 2.75, z), (wx - 3.2, wy - 2.75, z)])
        faces.append((b, b + 1, b + 2, b + 3))
        mats.append(2)
        uvs.extend([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    me = bpy.data.meshes.new("Presentoirs")
    me.from_pydata(verts, [], faces)
    me.polygons.foreach_set("material_index", mats)
    me.uv_layers.new(name="UVMap").data.foreach_set("uv", [t for uv in uvs for t in uv])
    me.update()
    return me


def build(dst):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.view_settings.view_transform = "Standard"

    label = label_array([n for n, _ in FRUITS])
    lmat = label_mat(image_from_array("Etiquettes", label[0]))
    wood = simple_material("Presentoir", (0.30, 0.17, 0.09))
    top = simple_material("Presentoir_dessus", (0.42, 0.25, 0.13), 0.6)
    stage = stage_mesh(label)
    for m in (wood, top, lmat):
        stage.materials.append(m)
    sc.collection.objects.link(bpy.data.objects.new("Presentoirs", stage))

    floor = bpy.data.meshes.new("Sol")
    floor.from_pydata([(-160, -90, 0), (160, -90, 0), (160, 130, 0), (-160, 130, 0)], [], [(0, 1, 2, 3)])
    floor.materials.append(wood_floor())
    sc.collection.objects.link(bpy.data.objects.new("Sol", floor))

    img, W, H = make_image("Spirales")
    cache = {}
    coll = bpy.data.collections.new("Fruits")
    sc.collection.children.link(coll)
    total = 0
    for i, (name, _) in enumerate(FRUITS):
        me = fruit_object(i, img, W, H, cache)
        total += len(me.polygons)
        ob = bpy.data.objects.new(f"Fruit_{name}", me)
        wx, wy, h = layout(i)
        zlow = min(v.co.z for v in me.vertices)
        ob.location = (wx, wy + 0.3, h + 0.18 - zlow)
        ob.rotation_euler = (0, 0, math.radians(((i * 37) % 25) - 12))
        coll.objects.link(ob)

    sun_d = bpy.data.lights.new("Soleil", "SUN")
    sun_d.energy = 3.0
    sun_d.color = (1.0, 0.92, 0.82)
    sun = bpy.data.objects.new("Soleil", sun_d)
    sun.rotation_euler = (math.radians(48), math.radians(6), math.radians(24))
    sc.collection.objects.link(sun)
    fill_d = bpy.data.lights.new("Lampe", "AREA")
    fill_d.energy = 4000
    fill_d.size = 50
    fill = bpy.data.objects.new("Lampe", fill_d)
    fill.location = (0, -34, 30)
    fill.rotation_euler = (math.radians(60), 0, 0)
    sc.collection.objects.link(fill)
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.48, 0.58, 0.78, 1)
    bg.inputs["Strength"].default_value = 0.9

    cam_d = bpy.data.cameras.new("Camera_Ensemble")
    cam_d.lens = 36
    cam = bpy.data.objects.new("Camera_Ensemble", cam_d)
    cam.location = (0, -57, 46)
    cam.rotation_euler = (math.radians(59.5), 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam2_d = bpy.data.cameras.new("Camera_GrosPlan")
    cam2_d.lens = 58
    cam2 = bpy.data.objects.new("Camera_GrosPlan", cam2_d)
    cam2.location = (-30, -13.0, 5.6)
    cam2.rotation_euler = (math.radians(88), 0, 0)
    sc.collection.objects.link(cam2)

    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print(f"OK: {dst} ({len(FRUITS)} fruits, {total} faces)")


if __name__ == "__main__":
    if "--stats" in sys.argv:
        tf = 0
        for n, nv, nf in mesh_stats():
            print(f"{n:26s} sommets {nv:6d}  faces {nf:6d}")
            tf += nf
        print(f"{'TOTAL':26s} faces {tf}")
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    build(args[-1])
