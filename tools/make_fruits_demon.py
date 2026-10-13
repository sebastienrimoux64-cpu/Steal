"""Fruits du démon (One Piece) en cubes : chaque fruit a SA forme, et ses spirales en relief.

Usage :
    python tools/make_fruits_demon.py SORTIE.blend [SORTIE.glb]

Les formes suivent les descriptions de l'œuvre (cœur, poire, fraise à cornes, tête de léopard, cactus,
framboise, yo-yo, régime de lames, ananas…). Chaque fruit est un seul maillage de cubes de 18 cm : seules les
faces visibles sont créées, les couleurs sont stockées dans l'attribut de couleur « Col ». Les spirales
(motif de peau de tous les fruits) sont de vrais reliefs : les cubes de la spirale sont recolorés ET
surélevés d'un cube.

Sources : descriptions des wikis (One Piece Wiki et dérivés) retrouvées par recherche web. Certains fruits
ont des designs contradictoires selon les sources, ou non officiels (voir README) ; les couleurs varient
entre l'anime et le manga.
"""
import math
import random
import sys

VOX = 0.18            # taille d'un cube (u)


# ======================================================================= primitives voxels
def clamp(x, a, b):
    return max(a, min(b, x))


def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def region(lo, hi):
    for x in range(int(math.floor(lo[0])), int(math.ceil(hi[0])) + 1):
        for y in range(int(math.floor(lo[1])), int(math.ceil(hi[1])) + 1):
            for z in range(int(math.floor(lo[2])), int(math.ceil(hi[2])) + 1):
                yield x, y, z


def ell(c, r):
    """Ellipsoïde de centre c et de demi-axes r."""
    cx, cy, cz = c
    rx, ry, rz = r
    return {(x, y, z) for x, y, z in region((cx - rx, cy - ry, cz - rz), (cx + rx, cy + ry, cz + rz))
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1}


def capsule(p0, p1, r0, r1=None, sy=1.0):
    """Cylindre arrondi / effilé entre deux points ; sy > 1 l'aplatit en y (lames)."""
    r1 = r0 if r1 is None else r1
    d = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    L2 = dot(d, d) or 1.0
    m = max(r0, r1) + 1.5
    S = set()
    lo = (min(p0[0], p1[0]) - m, min(p0[1], p1[1]) - m, min(p0[2], p1[2]) - m)
    hi = (max(p0[0], p1[0]) + m, max(p0[1], p1[1]) + m, max(p0[2], p1[2]) + m)
    for x, y, z in region(lo, hi):
        t = clamp(((x - p0[0]) * d[0] + (y - p0[1]) * d[1] + (z - p0[2]) * d[2]) / L2, 0.0, 1.0)
        cx, cy, cz = p0[0] + d[0] * t, p0[1] + d[1] * t, p0[2] + d[2] * t
        rr = r0 + (r1 - r0) * t
        if (x - cx) ** 2 + ((y - cy) * sy) ** 2 + (z - cz) ** 2 <= rr * rr:
            S.add((x, y, z))
    return S


def path(points, r0, r1=None, sy=1.0):
    r1 = r0 if r1 is None else r1
    S = set()
    n = len(points) - 1
    for i in range(n):
        a = r0 + (r1 - r0) * i / n
        b = r0 + (r1 - r0) * (i + 1) / n
        S |= capsule(points[i], points[i + 1], a, b, sy)
    return S


def box(lo, hi):
    return {(x, y, z) for x, y, z in region(lo, hi)}


def fib(n, zmin=-1.0, zmax=1.0):
    """n directions réparties sur la sphère (spirale de Fibonacci), z dans [zmin, zmax]."""
    out = []
    for i in range(n):
        z = zmax - (zmax - zmin) * (i + 0.5) / n
        rr = math.sqrt(max(0.0, 1 - z * z))
        a = i * 2.399963
        out.append((rr * math.cos(a), rr * math.sin(a), z))
    return out


def top_z(S, x=0, y=0):
    return max(z for (a, b, z) in S if a == x and b == y)


def pear(c, r_bulb, r_top, dz_top, thr=1.05):
    """Poire : deux sphères fondues (métaballes)."""
    cx, cy, cz = c
    S = set()
    zr = max(r_bulb, r_top + dz_top) * 1.35
    for x, y, z in region((cx - r_bulb - 2, cy - r_bulb - 2, cz - zr), (cx + r_bulb + 2, cy + r_bulb + 2, cz + zr)):
        d1 = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2
        d2 = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz - dz_top) ** 2
        if r_bulb ** 2 / (d1 + 0.01) + r_top ** 2 / (d2 + 0.01) >= thr:
            S.add((x, y, z))
    return S


# ======================================================================= couleurs / parties
GREEN = (0.28, 0.50, 0.18)
LEAF = (0.36, 0.64, 0.22)


class Part:
    """Une partie d'un fruit : un ensemble de cubes + la façon de la colorer.
    mode : « swirl » (peau à spirales en relief), « fn » (colorateur personnalisé), « plain » (uni)."""

    def __init__(self, vox, base, line=None, mode="swirl", center=(0, 0, 0), lf=None, nsw=6, rad=1.0, turns=2.4,
                 first=None):
        self.vox, self.base, self.line, self.mode = vox, base, line, mode
        self.center, self.lf, self.nsw, self.rad, self.turns, self.first = center, lf, nsw, rad, turns, first
        self.crack = None


def plain(vox, col):
    return Part(vox, col, None, "plain")


def stem_T(base, h=3, half=4.5, right_curl=True, color=GREEN):
    x, y, z = base
    S = capsule((x, y, z - 1), (x, y, z + h), 1.1)
    S |= capsule((x - half, y, z + h), (x + half, y, z + h), 1.0)
    if right_curl:
        S |= path([(x + half, y, z + h), (x + half + 2, y, z + h + 1.5), (x + half + 3.5, y, z + h + 0.5)], 0.9, 0.7)
    return plain(S, color)


def leaf(c, r, color=LEAF):
    return plain(ell(c, r), color)


# ======================================================================= spirales
def swirl_centers(rng, n, rad, first=None):
    """Centres de tourbillon sur la sphère ; le premier fait face à la caméra (-Y) sauf indication."""
    f = unit(first) if first else unit((rng.uniform(-0.25, 0.25), -1.0, rng.uniform(0.1, 0.4)))
    cs = [(f, 1.05 * rad, 1)]
    off = rng.random() * 6.28
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        a = i * 2.39996 + off
        rr = math.sqrt(max(0.0, 1 - z * z))
        d = unit((rr * math.cos(a), rr * math.sin(a), z))
        if dot(d, f) > 0.55:
            continue
        cs.append((d, rng.uniform(0.62, 0.9) * rad, rng.choice((-1, 1))))
    out = []
    for c, rd, h in cs:
        up = (0.0, 0.0, 1.0) if abs(c[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = unit(cross(c, up))
        v = cross(c, u)
        out.append((c, rd, h, u, v))
    return out


WIDTH = 0.30


def in_spiral(n, centers, turns):
    best = None
    for c, rd, h, u, v in centers:
        r = math.acos(clamp(dot(n, c), -1.0, 1.0))
        if r < rd:
            rn = r / rd
            if best is None or rn < best[0]:
                best = (rn, h, math.atan2(dot(n, v), dot(n, u)))
    if best is None:
        return False
    rn, h, a = best
    if rn < 0.07:
        return True
    s = rn * turns - h * a / (2 * math.pi)
    return (s - math.floor(s)) < WIDTH and rn > 0.10


def shade(c, k):
    return tuple(clamp(v * k, 0.0, 1.0) for v in c)


NEIGH = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


def paint(parts, seed):
    """Assemble les parties, colore la peau et ajoute le relief des spirales -> {cube: couleur}."""
    rng = random.Random(seed)
    occ = {}
    for pi, part in enumerate(parts):
        for p in part.vox:
            occ[p] = pi
    for part in parts:
        if part.mode == "swirl":
            part.cs = swirl_centers(rng, part.nsw, part.rad, part.first)
    out, raised = {}, {}
    for p, pi in occ.items():
        if all((p[0] + d[0], p[1] + d[1], p[2] + d[2]) in occ for d in NEIGH):
            continue                                                     # intérieur : invisible
        part = parts[pi]
        jit = 1 + rng.uniform(-0.05, 0.05)
        base = part.base(p) if callable(part.base) else part.base
        if part.mode == "plain":
            out[p] = shade(base, jit)
            continue
        n = unit((p[0] - part.center[0], p[1] - part.center[1], p[2] - part.center[2]))
        if part.mode == "fn":
            col = part.lf(p, n, rng)
            out[p] = shade(col if col is not None else base, jit)
            continue
        if in_spiral(n, part.cs, part.turns):
            out[p] = shade(part.line, jit)
            ax = max(range(3), key=lambda i: abs(n[i]))                  # relief : un cube de plus vers l'extérieur
            q = list(p)
            q[ax] += 1 if n[ax] > 0 else -1
            q = tuple(q)
            if q not in occ:
                raised[q] = shade(part.line, jit * 1.08)
        else:
            out[p] = shade(base, jit)
    out.update(raised)
    for part in parts:                                                    # fissures, etc. appliquées après coup
        if part.crack:
            for p in list(out):
                if p in part.vox:
                    col = part.crack(p)
                    if col is not None:
                        out[p] = col
    return out


def lumps_fn(centers, rl, base, ring, dot_col=None):
    """Colorateur « segments » : un point au sommet de chaque bosse et un anneau autour."""
    def f(p, n, rng):
        best, bc = 1e9, None
        for c in centers:
            d = math.sqrt((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2)
            if d < best:
                best, bc = d, c
        if best > rl * 1.15:
            return None
        ax = unit(bc)
        dv = unit((p[0] - bc[0], p[1] - bc[1], p[2] - bc[2]))
        ang = math.acos(clamp(dot(ax, dv), -1.0, 1.0))
        if dot_col and ang < 0.34:
            return dot_col
        if 0.72 < ang < 0.98 and (ang * 9) % 1 < 0.7:
            return ring
        return None
    return f


# ======================================================================= les fruits
def f_gomu():
    """Melon violet (type Yubari), tige en pousse avec deux petites feuilles, spirales en S."""
    return [Part(ell((0, 0, 0), (12, 12, 11.5)), (0.45, 0.17, 0.55), (0.80, 0.47, 0.88)),
            plain(path([(0, 0, 10), (0, 0, 13.5), (1.2, 0, 15.5), (3.2, 0, 16.5), (4.6, 0, 15.5)], 1.2, 0.8), GREEN),
            leaf((-2.2, 0, 14.6), (2.8, 1.0, 1.2)), leaf((2.6, 0, 13.3), (2.6, 1.0, 1.1))]


def f_mera():
    """En forme de flamme : un corps rond et plusieurs langues de feu, de l'orange au jaune."""
    body = ell((0, 0, -1), (10, 10, 9))
    tongues = (capsule((0, 0, 4), (1.5, 0, 22), 6.0, 0.4) | capsule((-5, 0, 3), (-9.5, 0, 15), 4.6, 0.4)
               | capsule((5, 0, 3), (8.5, 0, 17), 4.6, 0.4) | capsule((0, -4.5, 2), (-0.5, -6, 12), 4.0, 0.4)
               | capsule((0, 4.5, 3), (1, 6, 14), 4.0, 0.4))
    orange, yellow = (0.96, 0.44, 0.08), (1.0, 0.80, 0.18)

    def base(p):
        t = clamp((p[2] - 6) / 16.0, 0.0, 1.0)
        return tuple(a + (b - a) * t for a, b in zip(orange, yellow))
    return [Part(body | tongues, base, (0.80, 0.12, 0.05), center=(0, 0, 3), nsw=5)]


def heart_set(k, rot=0.0, c=(0, 0, 0)):
    S = set()
    ca, sa = math.cos(rot), math.sin(rot)
    for x, y, z in region((c[0] - 1.35 * k, c[1] - k, c[2] - 1.35 * k), (c[0] + 1.35 * k, c[1] + k, c[2] + 1.5 * k)):
        dx, dz = x - c[0], z - c[2]
        X, Z, Y = (dx * ca + dz * sa) / k, (-dx * sa + dz * ca) / k, (y - c[1]) / k
        if (X * X + 2.25 * Y * Y + Z * Z - 1) ** 3 - X * X * Z ** 3 - 0.1125 * Y * Y * Z ** 3 <= 0:
            S.add((x, y, z))
    return S


def f_ope():
    """Un cœur rouge, tige verte en T."""
    S = heart_set(8.6)
    zt = max(z for (x, y, z) in S) - 4
    stem = plain(capsule((0, 0, zt - 1), (0, 0, zt + 4), 1.1) | capsule((-4.5, 0, zt + 4), (4.5, 0, zt + 4), 1.0), GREEN)
    return [Part(S, (0.80, 0.07, 0.12), (1.0, 0.50, 0.55), nsw=5), stem]


def f_mero():
    """Deux petits cœurs (un rouge, un violet) dont les tiges se rejoignent."""
    a = heart_set(6.4, rot=math.radians(-18), c=(-6.6, 0, 0))
    b = heart_set(6.4, rot=math.radians(18), c=(6.6, 0, 0))
    za = max(z for (x, y, z) in a)
    stems = (path([(-6.0, 0, za - 3), (-4.5, 0, za + 1), (-2, 0, za + 4), (0, 0, za + 6)], 0.9)
             | path([(6.0, 0, za - 3), (4.5, 0, za + 1), (2, 0, za + 4), (0, 0, za + 6)], 0.9)
             | capsule((0, 0, za + 6), (0, 0, za + 9), 1.0))
    return [Part(a, (0.88, 0.08, 0.14), (1.0, 0.55, 0.60), center=(-6.6, 0, 0), nsw=3, rad=0.9),
            Part(b, (0.55, 0.20, 0.66), (0.85, 0.60, 0.92), center=(6.6, 0, 0), nsw=3, rad=0.9),
            plain(stems, GREEN)]


def f_ito():
    """Poire lilas à tige fuchsia en tire-bouchon."""
    S = pear((0, 0, 0), 11, 6.8, 9.5)
    zt = top_z(S)
    pts = []
    for i in range(26):
        t = i / 25
        a = t * 2.6 * 2 * math.pi
        pts.append((2.4 * math.cos(a) * (1 - 0.3 * t), 2.4 * math.sin(a) * (1 - 0.3 * t), zt - 1 + 11 * t))
    return [Part(S, (0.80, 0.68, 0.93), (0.96, 0.90, 1.0), center=(0, 0, 3)),
            plain(path(pts, 0.95, 0.7), (0.86, 0.12, 0.55))]


def f_doru():
    """Poire blanche dont le sommet fond comme une bougie : creux de cire, coulures, mèche."""
    S = pear((0, 0, 0), 11, 7.2, 9.0)
    ztop = top_z(S) - 1
    S = {p for p in S if p[2] <= ztop}
    for p in list(S):
        if p[2] >= ztop - 1 and p[0] ** 2 + p[1] ** 2 <= 4.6 ** 2:
            S.discard(p)
    rad_at = {}
    for (x, y, z) in S:
        rad_at[z] = max(rad_at.get(z, 0.0), math.hypot(x, y))
    rng = random.Random(5)
    drips = set()
    for k in range(11):
        a = k * 2 * math.pi / 11 + rng.uniform(-0.2, 0.2)
        ln = rng.randint(4, 12)
        for j in range(ln):
            z = ztop - j
            if z in rad_at:
                rr = rad_at[z] + 0.6
                drips |= ell((rr * math.cos(a), rr * math.sin(a), z), (1.3, 1.3, 0.8))
        if ztop - ln in rad_at:
            rr = rad_at[ztop - ln] + 0.9
            drips |= ell((rr * math.cos(a), rr * math.sin(a), ztop - ln), (1.8, 1.8, 1.6))
    wick = capsule((0, 0, ztop - 2), (0, 0, ztop + 3), 0.8)
    return [Part(S, (0.97, 0.97, 0.95), (0.80, 0.82, 0.86), center=(0, 0, 3), nsw=5),
            plain(drips, (1.0, 0.86, 0.50)), plain(wick, (0.20, 0.12, 0.10))]


def f_ushi():
    """Fraise noire coiffée de deux cornes blanc cassé."""
    S = set()
    for x, y, z in region((-13, -13, -15), (13, 13, 15)):
        t = z / 13.0
        if abs(t) >= 1:
            continue
        rr = 12.0 * math.sqrt(1 - t * t) * (0.55 + 0.45 * clamp((z + 13) / 22.0, 0.0, 1.0))
        if x * x + y * y <= rr * rr:
            S.add((x, y, z))
    zt = top_z(S)
    horns = set()
    for s in (-1, 1):
        horns |= path([(s * 10, 0, zt - 6), (s * 14.5, 0, zt - 4), (s * 17, 0, zt + 1.5), (s * 15.5, 0, zt + 6.5)], 2.3, 0.5)
    calyx = set()
    for k in range(6):
        a = k * math.pi / 3
        calyx |= capsule((0, 0, zt), (5.5 * math.cos(a), 5.5 * math.sin(a), zt + 1.2), 1.7, 0.7)
    return [Part(S, (0.07, 0.07, 0.10), (0.30, 0.30, 0.38), nsw=6),
            plain(horns, (0.95, 0.92, 0.82)), plain(calyx, LEAF), plain(capsule((0, 0, zt), (0, 0, zt + 4), 1.0), GREEN)]


def f_neko():
    """Tête de léopard : oreilles à spirales, taches, museau, tige en T recourbée."""
    head = ell((0, 0, 0), (12.5, 9.5, 10))
    snout = ell((0, -8, -3.5), (5.5, 3.6, 3.6))
    rng = random.Random(21)
    spots = [(rng.uniform(-10, 10), rng.uniform(-9, 3), rng.uniform(-6, 8)) for _ in range(16)]
    sizes = [rng.uniform(1.9, 2.8) for _ in spots]

    def lf(p, n, r):
        for s, sz in zip(spots, sizes):
            if (p[0] - s[0]) ** 2 + (p[1] - s[1]) ** 2 + (p[2] - s[2]) ** 2 < sz * sz:
                return (0.30, 0.17, 0.08)
        return None
    parts = [Part(head, (0.95, 0.76, 0.30), None, "fn", (0, 0, 0), lf=lf), plain(snout, (0.99, 0.90, 0.68))]
    for s in (-1, 1):
        parts.append(Part(ell((s * 8.2, 0, 9), (4.4, 3.2, 4.4)), (0.95, 0.76, 0.30), (0.30, 0.17, 0.08),
                          center=(s * 8.2, 0, 9), nsw=1, turns=1.6))
    parts.append(plain(ell((0, -11.2, -1.5), (1.5, 1.0, 1.1)), (0.16, 0.08, 0.08)))
    parts.append(stem_T((0, 0, 9.4), h=3, half=4))
    return parts


def f_nikyu():
    """Fruit rose chair avec trois bosses au sommet (patte), tige en T."""
    S = ell((0, 0, 0), (12, 11, 11))
    lumps = ell((-7, 0, 10.5), (4.4, 4, 4)) | ell((0, 0, 13), (4.6, 4.2, 4.4)) | ell((7, 0, 10.5), (4.4, 4, 4))
    return [Part(S, (0.97, 0.72, 0.66), (0.80, 0.42, 0.40), nsw=6),
            Part(lumps, (0.92, 0.55, 0.55), (0.70, 0.30, 0.34), center=(0, 0, 11), nsw=1, rad=1.2, turns=1.5),
            stem_T((0, 0, 16.5), h=3, half=4)]


def f_hana():
    """Fleur rose (dahlia) : cœur et couronnes de pétales, tige verte."""
    core = ell((0, 0, 0), (8.5, 8.5, 7.5))
    petals = set()
    for i, d in enumerate(fib(54, -0.35, 1.0)):
        ln = 15.5 if i % 2 == 0 else 13
        tip = (d[0] * ln, d[1] * ln, d[2] * ln * 0.9 + 1)
        petals |= capsule((d[0] * 6, d[1] * 6, d[2] * 5.5), tip, 3.0, 0.7)
    top = max(z for (_, _, z) in petals | core)
    return [Part(petals, lambda p: (0.96, 0.60, 0.76) if p[2] < 9 else (0.99, 0.72, 0.84), (0.78, 0.25, 0.50), nsw=4, turns=2.0),
            Part(core, (0.82, 0.22, 0.45), (1.0, 0.80, 0.50), nsw=3),
            plain(capsule((0, 0, top - 2), (0, 0, top + 4), 1.1), GREEN), leaf((2.5, 0, top + 2), (3.0, 1.0, 1.2))]


def f_suna():
    """Cactus tonneau beige à côtes et épines, avec deux petits bras dressés, tige verte en T."""
    body = set()
    for x, y, z in region((-13, -13, -14), (13, 13, 14)):
        phi = math.atan2(y, x)
        k = 1 - 0.12 * (0.5 + 0.5 * math.cos(8 * phi))
        if (x / (11.0 * k)) ** 2 + (y / (11.0 * k)) ** 2 + (z / 12.5) ** 2 <= 1:
            body.add((x, y, z))
    arms = set()
    for s_ in (-1, 1):
        arms |= path([(s_ * 9.5, 0, -2), (s_ * 13.6, 0, 0), (s_ * 13.6, 0, 12)], 3.4, 3.2)
        arms |= ell((s_ * 13.6, 0, 12.5), (3.2, 3.2, 2.6))

    def ribs(p):
        if p not in body:
            return None
        c = math.cos(8 * math.atan2(p[1], p[0]))
        if c < -0.9:
            return (0.58, 0.44, 0.24)                                    # fond des côtes
        if c > 0.93 and p[2] % 3 == 0:
            return (1.0, 0.97, 0.82)                                     # épines
        return None
    part = Part(body | arms, (0.86, 0.72, 0.46), (0.62, 0.46, 0.24), nsw=6)
    part.crack = ribs
    return [part, stem_T((0, 0, 12.2), h=3, half=4.5)]


def f_bara():
    """Ovale fait de petites boules (framboise / mini ananas), couronne de feuilles."""
    cs = [(d[0] * 7.6, d[1] * 7.6, d[2] * 10.6) for d in fib(64)]
    vox = ell((0, 0, 0), (8.5, 8.5, 11.5))
    for c in cs:
        vox |= ell(c, (3.5, 3.5, 3.5))
    orange = (0.92, 0.32, 0.14)
    crown = set()
    for k in range(5):
        a = k * 2 * math.pi / 5
        crown |= capsule((0, 0, 10), (4.5 * math.cos(a), 4.5 * math.sin(a), 15), 1.6, 0.5)
    return [Part(vox, orange, None, "fn", lf=lumps_fn(cs, 3.5, orange, (0.62, 0.12, 0.08), (0.99, 0.80, 0.30))),
            plain(crown, LEAF)]


def f_mochi():
    """Rond crème, étranglé en bas puis évasé en un pied plat de mochi."""
    bulb = ell((0, 0, 6), (10.8, 10.8, 9.5))
    neck = capsule((0, 0, -5), (0, 0, 0.5), 5.2)
    foot = {p for p in ell((0, 0, -7.5), (10, 10, 5)) if p[2] >= -11}
    return [Part(bulb | neck | foot, (0.99, 0.94, 0.84), (0.95, 0.66, 0.60), center=(0, 0, 2), nsw=6),
            plain(path([(0, 0, 14), (0, 0, 16.5), (1.4, 0, 18.5), (3.2, 0, 19)], 1.2, 0.9), GREEN)]


def f_bomu():
    """Pomme violet foncé façon bombe : tige en corde jaune effilochée, mèche allumée."""
    S = {p for p in ell((0, 0, 0), (11.5, 11.5, 11)) if not (p[0] ** 2 + p[1] ** 2 + (p[2] - 12.5) ** 2 <= 4.2 ** 2)}
    rope = path([(0, 0, 8.5), (0, 0, 13), (1.6, 0, 16.5), (3.8, 0, 18.5)], 1.5, 1.2)
    rng = random.Random(8)
    frays = set()
    for _ in range(9):
        a = rng.uniform(0, 6.28)
        frays |= capsule((3.8, 0, 18.5), (3.8 + 2.2 * math.cos(a), 2.2 * math.sin(a), 20.5 + rng.uniform(0, 1.8)), 0.7, 0.2)
    spark = ell((4.6, 0, 21.2), (1.4, 1.4, 1.4)) | ell((3.2, 0, 22.2), (1.0, 1.0, 1.0))
    return [Part(S, (0.30, 0.12, 0.40), (0.66, 0.40, 0.84), nsw=6),
            plain(rope | frays, (0.95, 0.80, 0.28)), plain(spark, (1.0, 0.45, 0.10))]


def f_gura():
    """Poire bleue fissurée dans sa moitié basse (comme les fissures de son pouvoir)."""
    S = pear((0, 0, -2), 11.5, 6.4, 11.5)
    zb = min(z for (_, _, z) in S)
    zt = top_z(S)
    rng = random.Random(3)
    cracks = []
    for k in range(5):
        ph = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
        cr = []
        for j in range(20):
            ph += rng.uniform(-0.22, 0.22)
            cr.append((zb + 0.5 + j * 0.8, ph))
        cracks.append(cr)

    def crack(p):
        phi = math.atan2(p[1], p[0])
        rr = max(math.hypot(p[0], p[1]), 3)
        for cr in cracks:
            for z, ph in cr:
                if abs(p[2] - z) <= 0.75 and abs(math.atan2(math.sin(phi - ph), math.cos(phi - ph))) * rr < 1.7:
                    return (0.04, 0.08, 0.22)
        return None
    body = Part(S, (0.30, 0.55, 0.95), (0.68, 0.84, 1.0), center=(0, 0, 3), nsw=6)
    body.crack = crack
    return [body, plain(capsule((0, 0, zt - 1), (0, 0, zt + 5), 1.1), GREEN), leaf((2.8, 0, zt + 3.2), (3.0, 1.0, 1.2))]


def f_goro():
    """Néflier jaune doré effilé vers la tige, hérissé de pointes d'éclair ; tige verte en zigzag."""
    body = ell((0, 0, -1.5), (10.5, 10.5, 11)) | capsule((0, 0, 5), (0, 0, 15.5), 8.0, 2.6)
    sparks = set()
    for d in fib(34, -0.5, 0.9):
        sparks |= capsule((d[0] * 9.5, d[1] * 9.5, d[2] * 10 - 1.5), (d[0] * 14, d[1] * 14, d[2] * 14 - 1.5), 1.5, 0.3)
    zt = top_z(body)
    zig = path([(0, 0, zt - 1), (2.2, 0, zt + 2), (-1.4, 0, zt + 4.5), (2.8, 0, zt + 7.5), (-0.6, 0, zt + 9.5)], 1.0, 0.8)
    bar = capsule((-3.5, 0, zt + 1.5), (3.5, 0, zt + 1.5), 0.9)
    return [Part(body, (0.99, 0.84, 0.22), (1.0, 0.97, 0.62), nsw=5),
            plain(sparks, (1.0, 0.98, 0.72)), plain(zig | bar, GREEN)]


def f_magu():
    """Boule rouge sombre faite de grosses bosses, chacune avec son tourbillon orange ; tige orange en vrille."""
    cs = [(d[0] * 8.2, d[1] * 8.2, d[2] * 8.2) for d in fib(28)]
    vox = ell((0, 0, 0), (9.5, 9.5, 9.5))
    for c in cs:
        vox |= ell(c, (5.2, 5.2, 5.2))
    dark = (0.42, 0.04, 0.04)
    helix = []
    for i in range(24):
        a = i / 23 * 2.2 * 2 * math.pi
        helix.append((2.2 * math.cos(a), 2.2 * math.sin(a), 13 + 9 * i / 23))
    return [Part(vox, dark, None, "fn", lf=lumps_fn(cs, 5.2, dark, (1.0, 0.52, 0.10), (1.0, 0.75, 0.2))),
            plain(path(helix, 1.0, 0.7), (0.95, 0.50, 0.10))]


def f_yami():
    """Grosse boule violet pâle faite de nombreuses gouttes pointues (grappe / ananas), feuilles vertes."""
    dirs = fib(60)
    centers = [(d[0] * 8.8, d[1] * 8.8, d[2] * 8.8) for d in dirs]
    vox = ell((0, 0, 0), (9.5, 9.5, 9.5))
    for c, d in zip(centers, dirs):
        vox |= ell(c, (3.6, 3.6, 3.6)) | capsule(c, (d[0] * 14.2, d[1] * 14.2, d[2] * 14.2), 3.4, 0.5)
    pale = (0.66, 0.56, 0.86)
    crown = set()
    for k in range(6):
        a = k * math.pi / 3
        crown |= capsule((0, 0, 11), (6 * math.cos(a), 6 * math.sin(a), 17), 1.9, 0.5)
    return [Part(vox, pale, None, "fn", lf=lumps_fn([tuple(v * 1.3 for v in c) for c in centers], 4.6, pale, (0.38, 0.28, 0.62))),
            plain(crown, LEAF)]


def f_tori():
    """Ananas vert à écailles pointues ; à la place de la tige, des lames bleues et jaunes comme des flammes."""
    body = ell((0, 0, 0), (9.8, 9.8, 13))
    green, light = (0.36, 0.66, 0.30), (0.58, 0.82, 0.42)

    def lf(p, n, r):
        u = math.atan2(p[1], p[0]) * 10.0 / 3.4
        v = p[2] / 3.4
        a, b = math.floor(u), math.floor(v)
        fu, fv = u - a, v - b
        if min(fu, 1 - fu, fv, 1 - fv) < 0.14:
            return (0.20, 0.45, 0.18)
        return light if (a + b) % 2 == 0 else green
    spikes = set()
    for ring, z in enumerate(range(-10, 12, 3)):
        rz = 9.4 * math.sqrt(max(0.0, 1 - (z / 13) ** 2))
        for k in range(11):
            a = (k + 0.5 * (ring % 2)) * 2 * math.pi / 11
            c = (math.cos(a) * rz, math.sin(a) * rz, z)
            spikes |= capsule(c, (c[0] * 1.22, c[1] * 1.22, c[2] + 0.5), 1.5, 0.3)
    parts = [Part(body | spikes, green, None, "fn", lf=lf)]
    for k in range(8):
        a = k * 2 * math.pi / 8
        col = (0.16, 0.50, 0.98) if k % 2 == 0 else (1.0, 0.85, 0.2)
        parts.append(plain(capsule((0.6 * math.cos(a), 0.6 * math.sin(a), 12),
                                   (6.5 * math.cos(a), 6.5 * math.sin(a), 24 + (k % 2) * 3), 2.0, 0.4), col))
    return parts


def f_yomi():
    """Rond doré à quatre petits pieds en bas (silhouette de crâne), tige verte."""
    feet = set()
    for sx in (-1, 1):
        for sy in (-1, 1):
            feet |= ell((sx * 6.4, sy * 6.4, -10), (3.8, 3.8, 3.4))
    return [Part(ell((0, 0, 0), (11.5, 11.5, 11)) | feet, (0.88, 0.66, 0.22), (0.55, 0.34, 0.08), nsw=6),
            plain(path([(0, 0, 9), (0, 0, 13), (1.4, 0, 15.5)], 1.2, 0.9), GREEN), leaf((-2.6, 0, 13.4), (3.0, 1.0, 1.2))]


def f_kage():
    """Rond tout noir à tige verte, avec des feuilles en bulbes d'oignon sur le côté (col de cape)."""
    leaves = set()
    for c, d in (((-9.5, 0, 6), (-1, 0, 0.9)), ((-11, -3, 2.5), (-1, -0.5, 0.2)), ((-11, 3, 2.5), (-1, 0.5, 0.2))):
        dd = unit(d)
        leaves |= ell(c, (3.2, 3.0, 3.0)) | capsule(c, (c[0] + dd[0] * 6, c[1] + dd[1] * 6, c[2] + dd[2] * 6), 3.0, 0.4)
    return [Part(ell((0, 0, 0), (11.5, 11.5, 11)), (0.05, 0.05, 0.07), (0.32, 0.32, 0.40), nsw=6),
            plain(path([(0, 0, 9), (0, 0, 13), (1.4, 0, 15.5), (3.4, 0, 16)], 1.2, 0.9), GREEN),
            plain(leaves, (0.30, 0.62, 0.25))]


def f_hobi():
    """Yo-yo : deux disques jaunes à noyau en spirale, enveloppe rouge, tige en huit couché (clé de remontage)."""
    discs_l = {p for p in box((-7.5, -11, -11), (-4.5, 11, 11)) if p[1] ** 2 + p[2] ** 2 <= 10.5 ** 2}
    discs_r = {p for p in box((4.5, -11, -11), (7.5, 11, 11)) if p[1] ** 2 + p[2] ** 2 <= 10.5 ** 2}
    rim = {p for p in box((-4, -12, -12), (4, 12, 12)) if p[1] ** 2 + p[2] ** 2 <= 11.8 ** 2}
    eight = []
    for i in range(41):
        t = i / 40 * 2 * math.pi
        den = 1 + math.sin(t) ** 2
        eight.append((4.8 * math.cos(t) / den, 0, 16.2 + 5.9 * math.sin(t) * math.cos(t) / den))
    return [Part(rim, (0.86, 0.10, 0.12), (0.55, 0.04, 0.06), nsw=6),
            Part(discs_l, (0.98, 0.95, 0.60), (0.88, 0.70, 0.18), center=(-6, 0, 0), nsw=0, rad=1.3, turns=2.2, first=(-1, 0, 0)),
            Part(discs_r, (0.98, 0.95, 0.60), (0.88, 0.70, 0.18), center=(6, 0, 0), nsw=0, rad=1.3, turns=2.2, first=(1, 0, 0)),
            plain(capsule((0, 0, 9), (0, 0, 14), 1.3), GREEN), plain(path(eight, 0.95), GREEN)]


def f_supa():
    """Régime de bananes dont chaque « banane » est une lame de sabre ; dos émoussé à spirales, tranchant clair."""
    blades = set()
    spine, edge = (0.36, 0.39, 0.47), (0.82, 0.85, 0.90)
    for dx in (-12, -6, 0, 6, 12):
        L = 22 - abs(dx) * 0.35
        blades |= path([(0, 0, -12), (dx * 0.35, 0, 0), (dx * 0.8, 0, L - 10), (dx * 1.05, 0, L - 1)], 4.4, 0.9, sy=1.2)

    def base(p):
        wave = 0.5 + 0.5 * math.sin(p[2] * 0.7 + p[0] * 0.35)
        return spine if wave > 0.78 else edge
    return [Part(blades, base, (0.14, 0.24, 0.56), center=(0, 0, 4), nsw=7, rad=0.75, turns=2.0),
            plain(capsule((0, 0, -15), (0, 0, -10), 1.8), (0.45, 0.60, 0.25))]


def f_sube():
    """Pêche rose brillante avec sa fente, spirales en S, tige verte et feuille."""
    S = set()
    for x, y, z in region((-13, -13, -13), (13, 13, 13)):
        k = 1 - 0.11 * math.exp(-(x / 2.4) ** 2) * (1 if y < 0 else 0.35)
        if (x / (11.5 * k)) ** 2 + (y / (11 * k)) ** 2 + (z / (11 * k)) ** 2 <= 1:
            S.add((x, y, z))
    return [Part(S, (0.98, 0.66, 0.72), (1.0, 0.90, 0.92), nsw=6),
            plain(path([(0, 0, 9), (0, 0, 12.5), (1.2, 0, 14.5)], 1.2, 0.9), GREEN), leaf((3.2, 0, 12), (3.6, 1.0, 1.3))]


def f_pika():
    """Cloche jaune (design le plus répandu) : col étroit, jupe très évasée, lèvre épaisse ; tige bleu clair."""
    vox = set()
    for x, y, z in region((-16, -16, -12), (16, 16, 15)):
        if z > 9:
            t = (z - 9) / 5.0
            rr = 6.0 * math.sqrt(max(0.0, 1 - t * t)) if t < 1 else -1
        else:
            rr = 6.0 + 9.2 * (clamp(-z, 0, 11) / 11.0) ** 1.7
        if rr > 0 and x * x + y * y <= rr * rr:
            vox.add((x, y, z))
    vox = {p for p in vox if not (p[0] ** 2 + p[1] ** 2 + (p[2] + 15.5) ** 2 <= 12.5 ** 2)}
    return [Part(vox, (0.98, 0.85, 0.22), (1.0, 0.97, 0.66), center=(0, 0, 0), nsw=6),
            plain(path([(0, 0, 13), (0, 0, 16.5), (1.4, 0, 18.5), (3.4, 0, 19), (4.8, 0, 17.7)], 1.2, 0.9), (0.55, 0.82, 0.98))]


def f_hie():
    """Pas de design officiel : ma version, un fruit bleu glacé hérissé d'éclats de glace, tige turquoise."""
    shards = set()
    for d in fib(16, -0.7, 0.8):
        shards |= capsule((d[0] * 7, d[1] * 7, d[2] * 7), (d[0] * 15.5, d[1] * 15.5, d[2] * 15.5), 3.4, 0.4)
    return [Part(ell((0, 0, 0), (9.2, 9.2, 9.2)), (0.56, 0.80, 0.97), (0.90, 0.97, 1.0), nsw=5),
            plain(shards, (0.83, 0.93, 1.0)),
            plain(path([(0, 0, 8), (0, 0, 12), (1.4, 0, 14), (3.2, 0, 14.5)], 1.2, 0.9), (0.30, 0.78, 0.78))]


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


def make_fruit(i):
    return paint(FRUITS[i][1](), seed=1000 + 17 * i)


# ======================================================================= maillage
FACES = {
    (1, 0, 0): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (-1, 0, 0): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
    (0, 1, 0): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    (0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    (0, 0, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
}


def voxel_mesh(name, vox):
    """Maillage de cubes : uniquement les faces exposées ; couleur par face (attribut « Col »)."""
    import bmesh
    import bpy
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")
    for (x, y, z), c in vox.items():
        for d, quad in FACES.items():
            if (x + d[0], y + d[1], z + d[2]) in vox:
                continue
            vs = [bm.verts.new(((x + a - 0.5) * VOX, (y + b - 0.5) * VOX, (z + e - 0.5) * VOX)) for a, b, e in quad]
            f = bm.faces.new(vs)
            for loop in f.loops:
                loop[col] = (*c, 1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def vertex_color_material():
    import bpy
    m = bpy.data.materials.new("Fruit_voxel")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.5
    a = nt.nodes.new("ShaderNodeVertexColor")
    a.layer_name = "Col"
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    return m


def simple_material(name, color, rough=0.7, emission=0.0):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def add_box(name, lo, hi, mat):
    import bpy
    verts = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


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


# ======================================================================= scène
COLS, DX, DY = 9, 7.9, 10.2


def layout(i):
    n_row = [9, 9, len(FRUITS) - 18]
    row, col = divmod(i, COLS)
    n = n_row[row]
    return (col - (n - 1) / 2) * DX, row * DY, 1.5 + 2.8 * row


def build(dst, glb=None):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.view_settings.view_transform = "Standard"

    fmat = vertex_color_material()
    wood = simple_material("Presentoir", (0.30, 0.17, 0.09), 0.7)
    top = simple_material("Presentoir_dessus", (0.42, 0.25, 0.13), 0.6)
    gold = simple_material("Or", (1.0, 0.78, 0.30), 0.35, emission=0.6)

    floor = bpy.data.meshes.new("Sol")
    floor.from_pydata([(-160, -90, 0), (160, -90, 0), (160, 130, 0), (-160, 130, 0)], [], [(0, 1, 2, 3)])
    floor.materials.append(wood_floor())
    sc.collection.objects.link(bpy.data.objects.new("Sol", floor))

    coll = bpy.data.collections.new("Fruits")
    sc.collection.children.link(coll)
    fruit_objs = []
    for i, (name, _) in enumerate(FRUITS):
        wx, wy, h = layout(i)
        add_box(f"Presentoir_{i + 1:02d}", (wx - 3.4, wy - 3.5, 0), (wx + 3.4, wy + 3.5, h), wood)
        add_box(f"Plateau_{i + 1:02d}", (wx - 3.55, wy - 3.65, h), (wx + 3.55, wy + 3.65, h + 0.18), top)
        vox = make_fruit(i)
        me = voxel_mesh(f"Fruit_{name}", vox)
        me.materials.append(fmat)
        ob = bpy.data.objects.new(f"Fruit_{name}", me)
        zmin = min(z for (_, _, z) in vox) - 0.5
        ob.location = (wx, wy + 0.3, h + 0.18 - zmin * VOX)
        ob.rotation_euler = (0, 0, math.radians(((i * 37) % 25) - 12))
        coll.objects.link(ob)
        fruit_objs.append(ob)
        cu = bpy.data.curves.new(f"Nom_{i + 1:02d}", "FONT")
        cu.body = name
        cu.size = 0.50 if len(name) <= 17 else 0.40
        cu.extrude = 0.04
        cu.align_x = "CENTER"
        cu.materials.append(gold)
        txt = bpy.data.objects.new(f"Nom_{i + 1:02d}", cu)
        txt.location = (wx, wy - 3.1, h + 0.2)              # à plat sur le plateau, devant le fruit
        sc.collection.objects.link(txt)

    sun_d = bpy.data.lights.new("Soleil", "SUN")
    sun_d.energy = 4.0
    sun_d.color = (1.0, 0.92, 0.82)
    sun = bpy.data.objects.new("Soleil", sun_d)
    sun.rotation_euler = (math.radians(48), math.radians(6), math.radians(24))
    sc.collection.objects.link(sun)
    fill_d = bpy.data.lights.new("Lampe", "AREA")
    fill_d.energy = 5000
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

    bpy.ops.wm.save_as_mainfile(filepath=dst)
    print(f"OK: {dst} ({len(FRUITS)} fruits)")
    if glb:
        try:
            for o in bpy.data.objects:
                o.select_set(False)
            for o in fruit_objs:
                o.select_set(True)
            bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_apply=True,
                                      export_vertex_color="ACTIVE", export_format="GLB")
            print(f"OK: {glb}")
        except Exception as e:
            print("glb non exporte :", e)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    build(args[-2] if len(args) > 1 else args[-1], args[-1] if len(args) > 1 else None)
