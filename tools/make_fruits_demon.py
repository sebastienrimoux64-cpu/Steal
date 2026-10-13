"""Fruits du démon (One Piece) en cubes : une forme par fruit, spirales fines, et un fichier LÉGER.

Usage :
    python tools/make_fruits_demon.py SORTIE.blend            # défaut : cubes de 27 cm (--k=3), ~15 000 faces
    python tools/make_fruits_demon.py SORTIE.blend --k=2      # cubes de 18 cm : plus fin, ~34 000 faces
    python tools/make_fruits_demon.py --stats                 # compte les faces, sans Blender

Les formes suivent les descriptions de l'œuvre (cœur, poire, fraise à cornes, tête de léopard, cactus,
framboise, yo-yo, régime de lames, ananas…).

Optimisation (tout est FUSIONNÉ) :
  * chaque fruit = UN SEUL maillage de gros cubes, dont toutes les faces coplanaires voisines sont fondues en
    grands rectangles (les faces cachées n'existent pas, les sommets sont partagés) ;
  * les détails fins (spirales, taches, nervures, côtes…) ne sont plus faits de milliers de petits cubes : ils
    sont peints sur UNE SEULE petite texture pixelisée partagée par les 26 fruits (« atlas ») ; chaque pixel de
    l'atlas est un cube fin (9 cm), pris par un rayon lancé dans le modèle détaillé ;
  * les 26 présentoirs, plateaux et étiquettes ne forment qu'un seul objet (étiquettes dans une seconde image).
Nécessite le module Pillow (pour les étiquettes) et numpy (fournis avec `pip install bpy`).

Sources : descriptions des wikis (One Piece Wiki et dérivés) retrouvées par recherche web. Certains fruits
ont des designs contradictoires selon les sources, ou non officiels (voir README) ; les couleurs varient
entre l'anime et le manga.
"""
import math
import random
import sys

def _scale_arg(default):
    for a in sys.argv[1:]:
        if a.startswith("--scale="):
            return float(a.split("=", 1)[1])
    return default


SCALE = _scale_arg(2.0)     # cubes par unité de forme : plus c'est grand, plus c'est fin (1 = cubes de 18 cm)
VOX = 0.18 / SCALE          # taille d'un cube (u) ; 1 u = 35 cm
RELIEF = 2                  # épaisseur (en cubes) du relief des spirales
SWIRL = 2.6                 # rayon d'une petite spirale de la peau (unités de forme ; fruit ~ 22 u de large)
TURNS_DENSE = 1.55          # nombre de tours d'une petite spirale
LIGHT = (-0.4, -0.6, 0.7)   # direction de lumière « cuite » dans les couleurs (3 niveaux)


# ======================================================================= primitives voxels
# Les formes sont décrites en unités « de forme » (flottantes) ; un cube est une clé entière (i, j, k)
# = coordonnées / SCALE.
def clamp(x, a, b):
    return max(a, min(b, x))


def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def grid(lo, hi):
    """Cubes dont le centre est dans la boîte [lo, hi] : renvoie (clé entière, coordonnées de forme)."""
    for i in range(int(math.floor(lo[0] * SCALE)), int(math.ceil(hi[0] * SCALE)) + 1):
        x = i / SCALE
        for j in range(int(math.floor(lo[1] * SCALE)), int(math.ceil(hi[1] * SCALE)) + 1):
            y = j / SCALE
            for k in range(int(math.floor(lo[2] * SCALE)), int(math.ceil(hi[2] * SCALE)) + 1):
                yield (i, j, k), (x, y, k / SCALE)


def bc(key):
    return (key[0] / SCALE, key[1] / SCALE, key[2] / SCALE)


def filt(S, pred):
    return {k for k in S if pred(*bc(k))}


def zmax(S):
    return max(k[2] for k in S) / SCALE


def zmin(S):
    return min(k[2] for k in S) / SCALE


def top_z(S, x=0.0, y=0.0):
    i, j = round(x * SCALE), round(y * SCALE)
    return max(k[2] for k in S if k[0] == i and k[1] == j) / SCALE


def ell(c, r):
    cx, cy, cz = c
    rx, ry, rz = r
    return {k for k, (x, y, z) in grid((cx - rx, cy - ry, cz - rz), (cx + rx, cy + ry, cz + rz))
            if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2 <= 1}


def capsule(p0, p1, r0, r1=None, sy=1.0):
    """Cylindre arrondi / effilé entre deux points ; sy > 1 l'aplatit en y (lames)."""
    r1 = r0 if r1 is None else r1
    d = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    L2 = dot(d, d) or 1.0
    m = max(r0, r1) + 1.0
    out = set()
    lo = (min(p0[0], p1[0]) - m, min(p0[1], p1[1]) - m, min(p0[2], p1[2]) - m)
    hi = (max(p0[0], p1[0]) + m, max(p0[1], p1[1]) + m, max(p0[2], p1[2]) + m)
    for k, (x, y, z) in grid(lo, hi):
        t = clamp(((x - p0[0]) * d[0] + (y - p0[1]) * d[1] + (z - p0[2]) * d[2]) / L2, 0.0, 1.0)
        cx, cy, cz = p0[0] + d[0] * t, p0[1] + d[1] * t, p0[2] + d[2] * t
        rr = r0 + (r1 - r0) * t
        if (x - cx) ** 2 + ((y - cy) * sy) ** 2 + (z - cz) ** 2 <= rr * rr:
            out.add(k)
    return out


def path(points, r0, r1=None, sy=1.0):
    r1 = r0 if r1 is None else r1
    out = set()
    n = len(points) - 1
    for i in range(n):
        a = r0 + (r1 - r0) * i / n
        b = r0 + (r1 - r0) * (i + 1) / n
        out |= capsule(points[i], points[i + 1], a, b, sy)
    return out


def box(lo, hi):
    return {k for k, _ in grid(lo, hi)}


def fib(n, zmin_=-1.0, zmax_=1.0):
    """n directions réparties sur la sphère (spirale de Fibonacci), z dans [zmin_, zmax_]."""
    out = []
    for i in range(n):
        z = zmax_ - (zmax_ - zmin_) * (i + 0.5) / n
        rr = math.sqrt(max(0.0, 1 - z * z))
        a = i * 2.399963
        out.append((rr * math.cos(a), rr * math.sin(a), z))
    return out


def pear(c, r_bulb, r_top, dz_top, thr=1.05):
    """Poire : deux sphères fondues (métaballes)."""
    cx, cy, cz = c
    zr = max(r_bulb, r_top + dz_top) * 1.35
    out = set()
    for k, (x, y, z) in grid((cx - r_bulb - 1, cy - r_bulb - 1, cz - zr), (cx + r_bulb + 1, cy + r_bulb + 1, cz + zr)):
        d1 = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz) ** 2
        d2 = (x - cx) ** 2 + (y - cy) ** 2 + (z - cz - dz_top) ** 2
        if r_bulb ** 2 / (d1 + 0.01) + r_top ** 2 / (d2 + 0.01) >= thr:
            out.add(k)
    return out


# ======================================================================= couleurs / parties
GREEN = (0.28, 0.50, 0.18)
LEAF = (0.36, 0.64, 0.22)
VEIN = (0.22, 0.42, 0.15)


class Part:
    """Une partie d'un fruit : un ensemble de cubes + la façon de la colorer.
    mode : « swirl » (peau à spirales en relief), « fn » (colorateur personnalisé), « plain » (uni)."""

    def __init__(self, vox, base, line=None, mode="swirl", center=(0, 0, 0), lf=None, nsw=7, rad=1.0, turns=None,
                 first=None, sw=SWIRL):
        # nsw > 1 : peau couverte de PETITES spirales (rayon sw, en unités de forme) ; nsw <= 1 : une seule spirale
        self.vox, self.base, self.line, self.mode = vox, base, line, mode
        self.center, self.lf, self.nsw, self.rad, self.first, self.sw = center, lf, nsw, rad, first, sw
        self.turns = turns if turns is not None else (TURNS_DENSE if nsw > 1 else 2.4)
        self.crack = None


def plain(vox, col):
    return Part(vox, col, None, "plain")


def leaf(c, r, color=LEAF):
    """Feuille : ellipsoïde aplati avec une nervure centrale plus sombre."""
    def lf(p, n, rng):
        return VEIN if abs(p[1] - c[1]) < 0.45 and n[2] > 0.35 else None
    return Part(ell(c, r), color, None, "fn", c, lf=lf)


def stem_T(base, h=3, half=4.5, right_curl=True, color=GREEN):
    x, y, z = base
    out = capsule((x, y, z - 1), (x, y, z + h), 1.1)
    out |= capsule((x - half, y, z + h), (x + half, y, z + h), 1.0)
    if right_curl:
        out |= path([(x + half, y, z + h), (x + half + 2, y, z + h + 1.5), (x + half + 3.5, y, z + h + 0.5)], 0.9, 0.7)
    return plain(out, color)


# ======================================================================= spirales
def _basis(c):
    up = (0.0, 0.0, 1.0) if abs(c[2]) < 0.9 else (1.0, 0.0, 0.0)
    u = unit(cross(c, up))
    return u, cross(c, u)


def swirl_centers(rng, nsw, rad, first=None, rho=11.0, sw=SWIRL):
    """Centres de volutes sur la sphère.
    nsw <= 1 : une seule grande spirale (face à la caméra, ou dirigée par `first`).
    nsw  > 1 : un semis régulier (spirale de Fibonacci, un peu secoué) de petites volutes de rayon `sw`,
    de sens alternés (voisines opposées) : leurs bras se rejoignent comme les « S » du motif karakusa."""
    if nsw <= 1:
        f = unit(first) if first else unit((rng.uniform(-0.25, 0.25), -1.0, rng.uniform(0.1, 0.4)))
        u, v = _basis(f)
        return [(f, 1, u, v)], 1.05 * rad
    ang = sw / rho                                                    # rayon angulaire d'une volute
    d = 1.75 * ang                                                    # écart entre deux centres
    n = max(8, int(4 * math.pi / (0.866 * d * d)))
    cs = []
    for c in fib(n):
        j = (rng.uniform(-0.2, 0.2) * d, rng.uniform(-0.2, 0.2) * d, rng.uniform(-0.2, 0.2) * d)
        cs.append(unit((c[0] + j[0], c[1] + j[1], c[2] + j[2])))
    hs = []
    for i, c in enumerate(cs):                                        # sens : l'opposé de la majorité des voisines déjà placées
        votes = sum(hs[j] for j in range(i) if dot(c, cs[j]) > math.cos(1.5 * d))
        hs.append(1 if votes < 0 else (-1 if votes > 0 else rng.choice((-1, 1))))
    out = []
    for c, h in zip(cs, hs):
        u, v = _basis(c)
        out.append((c, h, u, v))
    return out, ang


class SwirlField:
    """Les volutes d'une partie, rangées dans une grille pour retrouver vite les voisines d'un point."""

    def __init__(self, centers, ang, single, turns):
        self.single, self.turns, self.ang = single, turns, ang
        self.grid = {}
        for idx, (c, h, u, v) in enumerate(centers):
            key = tuple(int(math.floor((x + 1) * 2)) for x in c)
            self.grid.setdefault(key, []).append(idx)
        self.cs = centers

    def near(self, n):
        if self.single:
            return range(len(self.cs))
        k = [int(math.floor((x + 1) * 2)) for x in n]
        out = []
        for a in (-1, 0, 1):
            for b in (-1, 0, 1):
                for c in (-1, 0, 1):
                    out.extend(self.grid.get((k[0] + a, k[1] + b, k[2] + c), ()))
        return out

    def is_line(self, n, rho):
        """Vrai si la direction n (point à la distance rho du centre) tombe sur un bras de spirale."""
        rd = self.ang if self.single else clamp(self.ang * 11.0 / max(rho, 3.0), 0.7 * self.ang, 1.6 * self.ang)
        cosr = math.cos(rd)
        best = None
        for idx in self.near(n):
            c, h, u, v = self.cs[idx]
            dd = dot(n, c)
            if dd < cosr:
                continue
            rn = math.acos(clamp(dd, -1.0, 1.0)) / rd
            if best is None or rn < best[0]:
                best = (rn, h, math.atan2(dot(n, v), dot(n, u)))
        if best is None:
            return False
        rn, h, a = best
        if rn < 0.07 and self.single:
            return True
        s = rn * self.turns - h * a / (2 * math.pi)
        wd = WIDTH_SINGLE if self.single else WIDTH_DENSE
        return (s - math.floor(s)) < wd and rn > (0.09 if self.single else 0.12)


WIDTH_SINGLE, WIDTH_DENSE = 0.28, 0.42


def shade(c, k):
    return tuple(clamp(v * k, 0.0, 1.0) for v in c)


def lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def contrasted(base, line, gap=0.16):
    """Écarte le trait de la peau s'ils sont trop proches (fruits pâles) : même teinte, un ton plus soutenu."""
    if abs(lum(line) - lum(base)) >= gap:
        return line
    if lum(base) > 0.5:
        return tuple(clamp(v * 0.74, 0.0, 1.0) for v in base)
    return tuple(clamp(v * 1.35 + 0.12, 0.0, 1.0) for v in base)


def qcol(c):
    """Quantifie la couleur (6 bits par canal) : moins de teintes, texture plus propre."""
    return tuple(round(clamp(v, 0.0, 1.0) * 63) / 63 for v in c)


NEIGH = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
LU = unit(LIGHT)


def baked(n):
    """Éclairage cuit en 3 niveaux : le dessus est un peu plus clair, le dessous plus sombre."""
    d = dot(n, LU)
    return 1.09 if d > 0.62 else (0.86 if d < -0.15 else 1.0)


def paint(parts, seed):
    """Assemble les parties, colore la peau et ajoute le relief des spirales -> {cube: couleur}."""
    rng = random.Random(seed)
    occ = {}
    for pi, part in enumerate(parts):
        for k in part.vox:
            occ[k] = pi
    for part in parts:
        if part.mode == "swirl":
            pts = [bc(k) for k in list(part.vox)[:400]] or [(1.0, 0.0, 0.0)]
            rho = sum(math.dist(q, part.center) for q in pts) / len(pts)
            cs, ang = swirl_centers(rng, part.nsw, part.rad, part.first, max(rho, 4.0), part.sw)
            part.field = SwirlField(cs, ang, part.nsw <= 1, part.turns)
    out, raised = {}, {}
    patch = {}                                          # petite variation de teinte par plaques de 6 cubes

    def pj(k):
        key = (k[0] // 6, k[1] // 6, k[2] // 6)
        if key not in patch:
            patch[key] = 1 + rng.uniform(-0.035, 0.035)
        return patch[key]
    for k, pi in occ.items():
        if all((k[0] + d[0], k[1] + d[1], k[2] + d[2]) in occ for d in NEIGH):
            continue                                                     # intérieur : invisible
        part = parts[pi]
        p = bc(k)
        base = part.base(p) if callable(part.base) else part.base
        if part.mode == "plain":
            out[k] = qcol(shade(base, pj(k)))
            continue
        n = unit((p[0] - part.center[0], p[1] - part.center[1], p[2] - part.center[2]))
        lit = baked(n) * pj(k)
        if part.mode == "fn":
            col = part.lf(p, n, rng)
            out[k] = qcol(shade(col if col is not None else base, lit))
            continue
        if part.field.is_line(n, math.dist(p, part.center)):
            line = contrasted(base, part.line) if not part.field.single else part.line
            out[k] = qcol(shade(line, lit))
            ax = max(range(3), key=lambda i: abs(n[i]))                  # relief : des cubes en plus vers l'extérieur
            sg = 1 if n[ax] > 0 else -1
            q = list(k)
            for layer in range(RELIEF):
                q[ax] += sg
                if tuple(q) in occ:
                    break
                raised[tuple(q)] = qcol(shade(part.line, lit * (1.06 + 0.02 * layer)))
        else:
            out[k] = qcol(shade(base, lit))
    out.update(raised)
    solid = set(occ)
    for part in parts:                                                    # fissures, côtes, etc. appliquées après coup
        if part.crack:
            for k in list(out):
                if k in part.vox:
                    col = part.crack(bc(k))
                    if col is not None:
                        out[k] = qcol(col)
    return out, solid


def lumps_fn(centers, rl, base, ring, dot_col=None):
    """Colorateur « segments » : chaque bosse porte sa mini-spirale (sens alterné d'une bosse à l'autre)."""
    info = []
    for i, c in enumerate(centers):
        ax = unit(c)
        u, v = _basis(ax)
        info.append((ax, u, v, 1 if i % 2 else -1))

    def f(p, n, rng):
        best, bi = 1e9, None
        for i, c in enumerate(centers):
            d = math.sqrt((p[0] - c[0]) ** 2 + (p[1] - c[1]) ** 2 + (p[2] - c[2]) ** 2)
            if d < best:
                best, bi = d, i
        if best > rl * 1.15:
            return None
        ax, u, v, h = info[bi]
        c = centers[bi]
        dv = unit((p[0] - c[0], p[1] - c[1], p[2] - c[2]))
        ang = math.acos(clamp(dot(ax, dv), -1.0, 1.0))
        rn = ang / 1.15
        if rn > 1.0:
            return None
        if dot_col and rn < 0.1:
            return dot_col
        s = rn * 1.7 - h * math.atan2(dot(dv, v), dot(dv, u)) / (2 * math.pi)
        return ring if (s - math.floor(s)) < 0.42 and rn > 0.1 else None
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
               | capsule((0, 4.5, 3), (1, 6, 14), 4.0, 0.4) | capsule((-3, 3, 3), (-5, 4, 12), 3.2, 0.4)
               | capsule((3, -3, 3), (5, -4.5, 13), 3.2, 0.4))
    orange, yellow = (0.96, 0.44, 0.08), (1.0, 0.80, 0.18)

    def base(p):
        t = clamp((p[2] - 6) / 16.0, 0.0, 1.0)
        return tuple(a + (b - a) * t for a, b in zip(orange, yellow))
    return [Part(body | tongues, base, (0.80, 0.12, 0.05), center=(0, 0, 3), nsw=6)]


def heart_set(k_, rot=0.0, c=(0, 0, 0)):
    ca, sa = math.cos(rot), math.sin(rot)
    out = set()
    for key, (x, y, z) in grid((c[0] - 1.35 * k_, c[1] - k_, c[2] - 1.35 * k_), (c[0] + 1.35 * k_, c[1] + k_, c[2] + 1.5 * k_)):
        dx, dz = x - c[0], z - c[2]
        X, Z, Y = (dx * ca + dz * sa) / k_, (-dx * sa + dz * ca) / k_, (y - c[1]) / k_
        if (X * X + 2.25 * Y * Y + Z * Z - 1) ** 3 - X * X * Z ** 3 - 0.1125 * Y * Y * Z ** 3 <= 0:
            out.add(key)
    return out


def f_ope():
    """Un cœur rouge, tige verte en T."""
    S_ = heart_set(8.6)
    zt = zmax(S_) - 4
    stem = plain(capsule((0, 0, zt - 1), (0, 0, zt + 4), 1.1) | capsule((-4.5, 0, zt + 4), (4.5, 0, zt + 4), 1.0), GREEN)
    return [Part(S_, (0.80, 0.07, 0.12), (1.0, 0.50, 0.55), nsw=6), stem]


def f_mero():
    """Deux petits cœurs (un rouge, un violet) dont les tiges se rejoignent."""
    a = heart_set(6.4, rot=math.radians(-18), c=(-6.6, 0, 0))
    b = heart_set(6.4, rot=math.radians(18), c=(6.6, 0, 0))
    za = zmax(a)
    stems = (path([(-6.0, 0, za - 3), (-4.5, 0, za + 1), (-2, 0, za + 4), (0, 0, za + 6)], 0.9)
             | path([(6.0, 0, za - 3), (4.5, 0, za + 1), (2, 0, za + 4), (0, 0, za + 6)], 0.9)
             | capsule((0, 0, za + 6), (0, 0, za + 9), 1.0))
    return [Part(a, (0.88, 0.08, 0.14), (1.0, 0.55, 0.60), center=(-6.6, 0, 0), nsw=3, rad=0.9),
            Part(b, (0.55, 0.20, 0.66), (0.85, 0.60, 0.92), center=(6.6, 0, 0), nsw=3, rad=0.9),
            plain(stems, GREEN), leaf((1.8, 0, za + 8), (2.8, 1.0, 1.1))]


def f_ito():
    """Poire lilas à tige fuchsia en tire-bouchon."""
    S_ = pear((0, 0, 0), 11, 6.8, 9.5)
    zt = top_z(S_)
    pts = []
    for i in range(34):
        t = i / 33
        a = t * 2.6 * 2 * math.pi
        pts.append((2.4 * math.cos(a) * (1 - 0.3 * t), 2.4 * math.sin(a) * (1 - 0.3 * t), zt - 1 + 11 * t))
    return [Part(S_, (0.80, 0.68, 0.93), (0.96, 0.90, 1.0), center=(0, 0, 3)),
            plain(path(pts, 0.95, 0.7), (0.86, 0.12, 0.55))]


def f_doru():
    """Poire blanche dont le sommet fond comme une bougie : creux de cire, coulures, mèche."""
    S_ = pear((0, 0, 0), 11, 7.2, 9.0)
    ztop = top_z(S_) - 1
    S_ = filt(S_, lambda x, y, z: z <= ztop and not (z >= ztop - 1 and x * x + y * y <= 4.6 ** 2))
    rad_at = {}
    for k in S_:
        x, y, z = bc(k)
        rad_at[k[2]] = max(rad_at.get(k[2], 0.0), math.hypot(x, y))
    rng = random.Random(5)
    drips = set()
    for q in range(13):
        a = q * 2 * math.pi / 13 + rng.uniform(-0.2, 0.2)
        ln = rng.randint(4, 12)
        for j in range(int(ln * SCALE)):
            kz = round(ztop * SCALE) - j
            if kz in rad_at:
                rr = rad_at[kz] + 0.6
                drips |= ell((rr * math.cos(a), rr * math.sin(a), kz / SCALE), (1.3, 1.3, 0.8))
        kz = round(ztop * SCALE) - int(ln * SCALE)
        if kz in rad_at:
            rr = rad_at[kz] + 0.9
            drips |= ell((rr * math.cos(a), rr * math.sin(a), kz / SCALE), (1.8, 1.8, 1.6))
    wick = capsule((0, 0, ztop - 2), (0, 0, ztop + 3), 0.8)
    return [Part(S_, (0.97, 0.97, 0.95), (0.80, 0.82, 0.86), center=(0, 0, 3), nsw=6),
            plain(drips, (1.0, 0.86, 0.50)), plain(wick, (0.20, 0.12, 0.10))]


def f_ushi():
    """Fraise noire coiffée de deux cornes blanc cassé."""
    def inside(x, y, z):
        t = z / 13.0
        if abs(t) >= 1:
            return False
        rr = 12.0 * math.sqrt(1 - t * t) * (0.55 + 0.45 * clamp((z + 13) / 22.0, 0.0, 1.0))
        return x * x + y * y <= rr * rr
    S_ = {k for k, (x, y, z) in grid((-13, -13, -15), (13, 13, 15)) if inside(x, y, z)}
    zt = top_z(S_)
    horns = set()
    for s in (-1, 1):
        horns |= path([(s * 10, 0, zt - 6), (s * 14.5, 0, zt - 4), (s * 17, 0, zt + 1.5), (s * 15.5, 0, zt + 6.5)], 2.3, 0.5)
    calyx = set()
    for k in range(7):
        a = k * 2 * math.pi / 7
        calyx |= capsule((0, 0, zt), (5.5 * math.cos(a), 5.5 * math.sin(a), zt + 1.2), 1.7, 0.7)
    return [Part(S_, (0.07, 0.07, 0.10), (0.30, 0.30, 0.38), nsw=7),
            plain(horns, (0.95, 0.92, 0.82)), plain(calyx, LEAF), plain(capsule((0, 0, zt), (0, 0, zt + 4), 1.0), GREEN)]


def f_neko():
    """Tête de léopard : oreilles à spirales, taches en rosettes, museau, tige en T recourbée."""
    head = ell((0, 0, 0), (12.5, 9.5, 10))
    snout = ell((0, -8, -3.5), (5.5, 3.6, 3.6))
    rng = random.Random(21)
    spots = [(rng.uniform(-10, 10), rng.uniform(-9, 3), rng.uniform(-6, 8)) for _ in range(20)]
    sizes = [rng.uniform(1.7, 2.7) for _ in spots]

    def lf(p, n, r):
        for s_, sz in zip(spots, sizes):
            d2 = (p[0] - s_[0]) ** 2 + (p[1] - s_[1]) ** 2 + (p[2] - s_[2]) ** 2
            if d2 < sz * sz:
                return (0.30, 0.17, 0.08) if d2 > (0.45 * sz) ** 2 else (0.80, 0.52, 0.18)      # rosette : anneau + cœur
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
    S_ = ell((0, 0, 0), (12, 11, 11))
    lumps = ell((-7, 0, 10.5), (4.4, 4, 4)) | ell((0, 0, 13), (4.6, 4.2, 4.4)) | ell((7, 0, 10.5), (4.4, 4, 4))
    return [Part(S_, (0.97, 0.72, 0.66), (0.80, 0.42, 0.40), nsw=7),
            Part(lumps, (0.92, 0.55, 0.55), (0.70, 0.30, 0.34), center=(0, 0, 11), nsw=1, rad=1.2, turns=1.5),
            stem_T((0, 0, 16.5), h=3, half=4)]


def f_hana():
    """Fleur rose (dahlia) : cœur et couronnes de pétales, tige verte."""
    core = ell((0, 0, 0), (8.5, 8.5, 7.5))
    petals = set()
    for i, d in enumerate(fib(70, -0.35, 1.0)):
        ln = 15.5 if i % 2 == 0 else 13
        tip = (d[0] * ln, d[1] * ln, d[2] * ln * 0.9 + 1)
        petals |= capsule((d[0] * 6, d[1] * 6, d[2] * 5.5), tip, 2.7, 0.6)
    top = zmax(petals | core)
    return [Part(petals, lambda p: (0.96, 0.60, 0.76) if p[2] < 9 else (0.99, 0.72, 0.84), (0.78, 0.25, 0.50), nsw=5, turns=2.0),
            Part(core, (0.82, 0.22, 0.45), (1.0, 0.80, 0.50), nsw=3),
            plain(capsule((0, 0, top - 2), (0, 0, top + 4), 1.1), GREEN), leaf((2.5, 0, top + 2), (3.0, 1.0, 1.2))]


def f_suna():
    """Cactus tonneau beige à côtes et épines, avec deux petits bras dressés, tige verte en T."""
    def inside(x, y, z):
        phi = math.atan2(y, x)
        k = 1 - 0.12 * (0.5 + 0.5 * math.cos(8 * phi))
        return (x / (11.0 * k)) ** 2 + (y / (11.0 * k)) ** 2 + (z / 12.5) ** 2 <= 1
    body = {k for k, (x, y, z) in grid((-13, -13, -14), (13, 13, 14)) if inside(x, y, z)}
    arms = set()
    for s_ in (-1, 1):
        arms |= path([(s_ * 9.5, 0, -2), (s_ * 13.6, 0, 0), (s_ * 13.6, 0, 12)], 3.4, 3.2)
        arms |= ell((s_ * 13.6, 0, 12.5), (3.2, 3.2, 2.6))

    def ribs(p):
        if round(p[0] * SCALE) == 0 and round(p[1] * SCALE) == 0:
            return None
        c = math.cos(8 * math.atan2(p[1], p[0]))
        if c < -0.9 and abs(p[0]) < 11.5 and abs(p[2]) < 12:
            return (0.58, 0.44, 0.24)                                    # fond des côtes
        if c > 0.95 and round(p[2] * SCALE) % 6 == 0 and abs(p[2]) < 11 and math.hypot(p[0], p[1]) > 8:
            return (1.0, 0.97, 0.82)                                     # épines
        return None
    part = Part(body | arms, (0.86, 0.72, 0.46), (0.62, 0.46, 0.24), nsw=7)
    part.crack = ribs
    return [part, stem_T((0, 0, 12.2), h=3, half=4.5)]


def f_bara():
    """Ovale fait de petites boules (framboise / mini ananas), couronne de feuilles."""
    cs = [(d[0] * 7.8, d[1] * 7.8, d[2] * 10.8) for d in fib(96)]
    vox = ell((0, 0, 0), (8.5, 8.5, 11.5))
    for c in cs:
        vox |= ell(c, (3.1, 3.1, 3.1))
    orange = (0.92, 0.32, 0.14)
    crown = set()
    for k in range(6):
        a = k * 2 * math.pi / 6
        crown |= capsule((0, 0, 10), (4.5 * math.cos(a), 4.5 * math.sin(a), 15), 1.5, 0.5)
    return [Part(vox, orange, None, "fn", lf=lumps_fn(cs, 3.1, orange, (0.62, 0.12, 0.08), (0.99, 0.80, 0.30))),
            plain(crown, LEAF)]


def f_mochi():
    """Rond crème, étranglé en bas puis évasé en un pied plat de mochi."""
    bulb = ell((0, 0, 6), (10.8, 10.8, 9.5))
    neck = capsule((0, 0, -5), (0, 0, 0.5), 5.2)
    foot = filt(ell((0, 0, -7.5), (10, 10, 5)), lambda x, y, z: z >= -11)
    return [Part(bulb | neck | foot, (0.99, 0.94, 0.84), (0.95, 0.66, 0.60), center=(0, 0, 2), nsw=7),
            plain(path([(0, 0, 14), (0, 0, 16.5), (1.4, 0, 18.5), (3.2, 0, 19)], 1.2, 0.9), GREEN)]


def f_bomu():
    """Pomme violet foncé façon bombe : tige en corde jaune effilochée, mèche allumée."""
    S_ = filt(ell((0, 0, 0), (11.5, 11.5, 11)), lambda x, y, z: not (x * x + y * y + (z - 12.5) ** 2 <= 4.2 ** 2))
    rope = path([(0, 0, 8.5), (0, 0, 13), (1.6, 0, 16.5), (3.8, 0, 18.5)], 1.5, 1.2)
    rng = random.Random(8)
    frays = set()
    for _ in range(13):
        a = rng.uniform(0, 6.28)
        frays |= capsule((3.8, 0, 18.5), (3.8 + 2.4 * math.cos(a), 2.4 * math.sin(a), 20.5 + rng.uniform(0, 2.0)), 0.7, 0.2)
    spark = ell((4.6, 0, 21.2), (1.4, 1.4, 1.4)) | ell((3.2, 0, 22.2), (1.0, 1.0, 1.0)) | ell((5.6, 1.4, 22.8), (0.7, 0.7, 0.7))
    return [Part(S_, (0.30, 0.12, 0.40), (0.66, 0.40, 0.84), nsw=7),
            plain(rope | frays, (0.95, 0.80, 0.28)), plain(spark, (1.0, 0.45, 0.10))]


def f_gura():
    """Poire bleue fissurée dans sa moitié basse (comme les fissures de son pouvoir)."""
    S_ = pear((0, 0, -2), 11.5, 6.4, 11.5)
    zb = zmin(S_)
    zt = top_z(S_)
    rng = random.Random(3)
    cracks = []
    for k in range(5):
        ph = k * 2 * math.pi / 5 + rng.uniform(-0.3, 0.3)
        cr = []
        for j in range(26):
            ph += rng.uniform(-0.22, 0.22)
            cr.append((zb + 0.5 + j * 0.62, ph))
        cracks.append(cr)

    def crack(p):
        phi = math.atan2(p[1], p[0])
        rr = max(math.hypot(p[0], p[1]), 3)
        for cr in cracks:
            for z, ph in cr:
                if abs(p[2] - z) <= 0.62 and abs(math.atan2(math.sin(phi - ph), math.cos(phi - ph))) * rr < 1.45:
                    return (0.04, 0.08, 0.22)
        return None
    body = Part(S_, (0.30, 0.55, 0.95), (0.68, 0.84, 1.0), center=(0, 0, 3), nsw=7)
    body.crack = crack
    return [body, plain(capsule((0, 0, zt - 1), (0, 0, zt + 5), 1.1), GREEN), leaf((2.8, 0, zt + 3.2), (3.0, 1.0, 1.2))]


def f_goro():
    """Néflier jaune doré effilé vers la tige, hérissé de pointes d'éclair ; tige verte en zigzag."""
    body = ell((0, 0, -1.5), (10.5, 10.5, 11)) | capsule((0, 0, 5), (0, 0, 15.5), 8.0, 2.6)
    sparks = set()
    for d in fib(46, -0.5, 0.9):
        sparks |= capsule((d[0] * 9.5, d[1] * 9.5, d[2] * 10 - 1.5), (d[0] * 14, d[1] * 14, d[2] * 14 - 1.5), 1.4, 0.3)
    zt = top_z(body)
    zig = path([(0, 0, zt - 1), (2.2, 0, zt + 2), (-1.4, 0, zt + 4.5), (2.8, 0, zt + 7.5), (-0.6, 0, zt + 9.5)], 1.0, 0.8)
    bar = capsule((-3.5, 0, zt + 1.5), (3.5, 0, zt + 1.5), 0.9)
    return [Part(body, (0.99, 0.84, 0.22), (1.0, 0.97, 0.62), nsw=6),
            plain(sparks, (1.0, 0.98, 0.72)), plain(zig | bar, GREEN)]


def f_magu():
    """Boule rouge sombre faite de grosses bosses, chacune avec son tourbillon orange ; tige orange en vrille."""
    cs = [(d[0] * 8.2, d[1] * 8.2, d[2] * 8.2) for d in fib(38)]
    vox = ell((0, 0, 0), (9.5, 9.5, 9.5))
    for c in cs:
        vox |= ell(c, (4.6, 4.6, 4.6))
    dark = (0.42, 0.04, 0.04)
    helix = []
    for i in range(32):
        a = i / 31 * 2.2 * 2 * math.pi
        helix.append((2.2 * math.cos(a), 2.2 * math.sin(a), 13 + 9 * i / 31))
    return [Part(vox, dark, None, "fn", lf=lumps_fn(cs, 4.6, dark, (1.0, 0.52, 0.10), (1.0, 0.75, 0.2))),
            plain(path(helix, 1.0, 0.7), (0.95, 0.50, 0.10))]


def f_yami():
    """Grosse boule violet pâle faite de nombreuses gouttes pointues (grappe / ananas), feuilles vertes."""
    dirs = fib(84)
    centers = [(d[0] * 8.8, d[1] * 8.8, d[2] * 8.8) for d in dirs]
    vox = ell((0, 0, 0), (9.5, 9.5, 9.5))
    for c, d in zip(centers, dirs):
        vox |= ell(c, (3.1, 3.1, 3.1)) | capsule(c, (d[0] * 13.8, d[1] * 13.8, d[2] * 13.8), 2.9, 0.4)
    pale = (0.66, 0.56, 0.86)
    crown = set()
    for k in range(7):
        a = k * 2 * math.pi / 7
        crown |= capsule((0, 0, 11), (6 * math.cos(a), 6 * math.sin(a), 17), 1.8, 0.5)
    return [Part(vox, pale, None, "fn", lf=lumps_fn([tuple(v * 1.3 for v in c) for c in centers], 4.0, pale, (0.38, 0.28, 0.62))),
            plain(crown, LEAF)]


def f_tori():
    """Ananas vert à écailles pointues ; à la place de la tige, des lames bleues et jaunes comme des flammes."""
    body = ell((0, 0, 0), (9.8, 9.8, 13))
    green, light = (0.36, 0.66, 0.30), (0.58, 0.82, 0.42)

    def lf(p, n, r):
        u = math.atan2(p[1], p[0]) * 10.0 / 2.9
        v = p[2] / 2.9
        a, b = math.floor(u), math.floor(v)
        fu, fv = u - a, v - b
        if min(fu, 1 - fu, fv, 1 - fv) < 0.1:
            return (0.20, 0.45, 0.18)
        x, y = fu - 0.5, fv - 0.5
        r = math.hypot(x, y) * 2.0
        h = 1 if (a + b) % 2 else -1
        t = r * 1.6 - h * math.atan2(y, x) / (2 * math.pi)
        if r < 0.92 and (t - math.floor(t)) < 0.42 and r > 0.12:
            return (0.16, 0.38, 0.14)                                    # mini-spirale de l'écaille
        return light if (a + b) % 2 == 0 else green
    spikes = set()
    for ring, z in enumerate([-10.5 + 2.6 * i for i in range(9)]):
        rz = 9.4 * math.sqrt(max(0.0, 1 - (z / 13) ** 2))
        for k in range(13):
            a = (k + 0.5 * (ring % 2)) * 2 * math.pi / 13
            c = (math.cos(a) * rz, math.sin(a) * rz, z)
            spikes |= capsule(c, (c[0] * 1.2, c[1] * 1.2, c[2] + 0.5), 1.3, 0.3)
    parts = [Part(body | spikes, green, None, "fn", lf=lf)]
    for k in range(10):
        a = k * 2 * math.pi / 10
        col = (0.16, 0.50, 0.98) if k % 2 == 0 else (1.0, 0.85, 0.2)
        parts.append(plain(capsule((0.6 * math.cos(a), 0.6 * math.sin(a), 12),
                                   (6.5 * math.cos(a), 6.5 * math.sin(a), 24 + (k % 2) * 3), 1.9, 0.4), col))
    return parts


def f_yomi():
    """Rond doré à quatre petits pieds en bas (silhouette de crâne), tige verte."""
    feet = set()
    for sx in (-1, 1):
        for sy in (-1, 1):
            feet |= ell((sx * 6.4, sy * 6.4, -10), (3.8, 3.8, 3.4))
    return [Part(ell((0, 0, 0), (11.5, 11.5, 11)) | feet, (0.88, 0.66, 0.22), (0.55, 0.34, 0.08), nsw=7),
            plain(path([(0, 0, 9), (0, 0, 13), (1.4, 0, 15.5)], 1.2, 0.9), GREEN), leaf((-2.6, 0, 13.4), (3.0, 1.0, 1.2))]


def f_kage():
    """Rond tout noir à tige verte, avec des feuilles en bulbes d'oignon sur le côté (col de cape)."""
    leaves = set()
    for c, d in (((-9.5, 0, 6), (-1, 0, 0.9)), ((-11, -3, 2.5), (-1, -0.5, 0.2)), ((-11, 3, 2.5), (-1, 0.5, 0.2))):
        dd = unit(d)
        leaves |= ell(c, (3.2, 3.0, 3.0)) | capsule(c, (c[0] + dd[0] * 6, c[1] + dd[1] * 6, c[2] + dd[2] * 6), 3.0, 0.4)
    return [Part(ell((0, 0, 0), (11.5, 11.5, 11)), (0.05, 0.05, 0.07), (0.32, 0.32, 0.40), nsw=7),
            plain(path([(0, 0, 9), (0, 0, 13), (1.4, 0, 15.5), (3.4, 0, 16)], 1.2, 0.9), GREEN),
            plain(leaves, (0.30, 0.62, 0.25))]


def f_hobi():
    """Yo-yo : deux disques jaunes à noyau en spirale, enveloppe rouge, tige en huit couché (clé de remontage)."""
    discs_l = filt(box((-7.5, -11, -11), (-4.5, 11, 11)), lambda x, y, z: y * y + z * z <= 10.5 ** 2)
    discs_r = filt(box((4.5, -11, -11), (7.5, 11, 11)), lambda x, y, z: y * y + z * z <= 10.5 ** 2)
    rim = filt(box((-4, -12, -12), (4, 12, 12)), lambda x, y, z: y * y + z * z <= 11.8 ** 2)
    eight = []
    for i in range(53):
        t = i / 52 * 2 * math.pi
        den = 1 + math.sin(t) ** 2
        eight.append((4.8 * math.cos(t) / den, 0, 16.2 + 5.9 * math.sin(t) * math.cos(t) / den))
    return [Part(rim, (0.86, 0.10, 0.12), (0.55, 0.04, 0.06), nsw=7),
            Part(discs_l, (0.98, 0.95, 0.60), (0.88, 0.70, 0.18), center=(-6, 0, 0), nsw=0, rad=1.3, turns=2.2, first=(-1, 0, 0)),
            Part(discs_r, (0.98, 0.95, 0.60), (0.88, 0.70, 0.18), center=(6, 0, 0), nsw=0, rad=1.3, turns=2.2, first=(1, 0, 0)),
            plain(capsule((0, 0, 9), (0, 0, 14), 1.3), GREEN), plain(path(eight, 0.95), GREEN)]


def f_supa():
    """Régime de bananes dont chaque « banane » est une lame de sabre ; tranchant clair, lignes ondulées, spirales bleues."""
    blades = set()
    spine, edge = (0.36, 0.39, 0.47), (0.82, 0.85, 0.90)
    for dx in (-12, -6, 0, 6, 12):
        L = 22 - abs(dx) * 0.35
        blades |= path([(0, 0, -12), (dx * 0.35, 0, 0), (dx * 0.8, 0, L - 10), (dx * 1.05, 0, L - 1)], 4.4, 0.9, sy=1.2)

    def base(p):
        wave = 0.5 + 0.5 * math.sin(p[2] * 0.7 + p[0] * 0.35)
        return spine if wave > 0.78 else edge
    return [Part(blades, base, (0.14, 0.24, 0.56), center=(0, 0, 4), nsw=8, rad=0.75, turns=2.0),
            plain(capsule((0, 0, -15), (0, 0, -10), 1.8), (0.45, 0.60, 0.25))]


def f_sube():
    """Pêche rose brillante avec sa fente, spirales en S, tige verte et feuille."""
    def inside(x, y, z):
        k = 1 - 0.11 * math.exp(-(x / 2.4) ** 2) * (1 if y < 0 else 0.35)
        return (x / (11.5 * k)) ** 2 + (y / (11 * k)) ** 2 + (z / (11 * k)) ** 2 <= 1
    S_ = {k for k, (x, y, z) in grid((-13, -13, -13), (13, 13, 13)) if inside(x, y, z)}
    return [Part(S_, (0.98, 0.66, 0.72), (1.0, 0.90, 0.92), nsw=7),
            plain(path([(0, 0, 9), (0, 0, 12.5), (1.2, 0, 14.5)], 1.2, 0.9), GREEN), leaf((3.2, 0, 12), (3.6, 1.0, 1.3))]


def f_pika():
    """Cloche jaune (design le plus répandu) : col étroit, jupe très évasée, lèvre épaisse ; tige bleu clair."""
    def inside(x, y, z):
        if z > 9:
            t = (z - 9) / 5.0
            rr = 6.0 * math.sqrt(max(0.0, 1 - t * t)) if t < 1 else -1
        else:
            rr = 6.0 + 9.2 * (clamp(-z, 0, 11) / 11.0) ** 1.7
        return rr > 0 and x * x + y * y <= rr * rr
    vox = {k for k, (x, y, z) in grid((-16, -16, -12), (16, 16, 15)) if inside(x, y, z)}
    vox = filt(vox, lambda x, y, z: not (x * x + y * y + (z + 15.5) ** 2 <= 12.5 ** 2))
    return [Part(vox, (0.98, 0.85, 0.22), (1.0, 0.97, 0.66), nsw=7),
            plain(path([(0, 0, 13), (0, 0, 16.5), (1.4, 0, 18.5), (3.4, 0, 19), (4.8, 0, 17.7)], 1.2, 0.9), (0.55, 0.82, 0.98))]


def f_hie():
    """Pas de design officiel : ma version, un fruit bleu glacé hérissé d'éclats de glace, tige turquoise."""
    shards = set()
    for i, d in enumerate(fib(22, -0.7, 0.8)):
        ln = 15.5 if i % 2 == 0 else 13
        shards |= capsule((d[0] * 7, d[1] * 7, d[2] * 7), (d[0] * ln, d[1] * ln, d[2] * ln), 3.0, 0.4)
    return [Part(ell((0, 0, 0), (9.2, 9.2, 9.2)), (0.56, 0.80, 0.97), (0.90, 0.97, 1.0), nsw=6),
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
    """(cubes fins colorés, ensemble plein) du fruit i."""
    return paint(FRUITS[i][1](), seed=1000 + 17 * i)


# ======================================================================= fusion : maillage grossier + une texture
def _k_arg(default):
    for a in sys.argv[1:]:
        if a.startswith("--k="):
            return int(a.split("=", 1)[1])
    return default


K = _k_arg(3)               # cubes fins fusionnés dans un cube du maillage (K=3 : 27 cm ; K=2 : 18 cm, plus fin)


def coarse_solid(solid):
    """Maillage grossier : un gros cube est plein si assez de cubes fins le sont (les fines tiges survivent)."""
    cnt = {}
    for k in solid:
        c = (k[0] // K, k[1] // K, k[2] // K)
        cnt[c] = cnt.get(c, 0) + 1
    need = max(2, round(0.375 * K ** 3))
    return {c for c, n in cnt.items() if n >= need}


def greedy_quads(cells):
    """Rectangles de faces visibles, couleur ignorée (la couleur vient de la texture) :
    [(axe, signe, plan, u0, v0, largeur, hauteur)] en indices de gros cubes."""
    quads = []
    for axis in range(3):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        for sign in (1, -1):
            planes = {}
            for c in cells:
                nb = list(c)
                nb[axis] += sign
                if tuple(nb) not in cells:
                    planes.setdefault(c[axis], set()).add((c[u], c[v]))
            for s, cs in planes.items():
                done = set()
                for cu, cv in sorted(cs):
                    if (cu, cv) in done:
                        continue
                    w = 1
                    while (cu + w, cv) in cs and (cu + w, cv) not in done:
                        w += 1
                    h = 1
                    while all((cu + i, cv + h) in cs and (cu + i, cv + h) not in done for i in range(w)):
                        h += 1
                    for i in range(w):
                        for j in range(h):
                            done.add((cu + i, cv + j))
                    quads.append((axis, sign, s, cu, cv, w, h))
    return quads


def sample_patch(fine, q):
    """Couleurs d'un rectangle : pour chaque texel (un cube fin), on lance un rayon vers l'intérieur
    et on prend le premier cube fin coloré touché (relief des spirales compris)."""
    axis, sign, s, cu, cv, w, h = q
    u, v = (axis + 1) % 3, (axis + 2) % 3
    W, H = w * K, h * K
    outer = s * K + K if sign > 0 else s * K - 1
    steps = RELIEF + 2 * K + 1
    rows = []
    for j in range(H):
        fv = cv * K + j
        row = []
        for i in range(W):
            fu = cu * K + i
            col = None
            for d in range(steps):
                key = [0, 0, 0]
                key[axis] = outer + sign * (RELIEF - d)
                key[u], key[v] = fu, fv
                col = fine.get(tuple(key))
                if col is not None:
                    break
            row.append(col)
        last = None
        for i in range(W):                                    # trous (rares) : couleur du voisin
            if row[i] is None:
                row[i] = last
            else:
                last = row[i]
        for i in range(W - 1, -1, -1):
            if row[i] is None:
                row[i] = row[i + 1] if i + 1 < W and row[i + 1] is not None else (0.55, 0.55, 0.55)
        rows.append(row)
    return rows


def pack_patches(sizes):
    """Range des rectangles (largeur, hauteur) dans une texture : renvoie (positions, largeur, hauteur)."""
    order = sorted(range(len(sizes)), key=lambda i: -sizes[i][1])
    best = None
    for AW in (256, 512, 1024, 2048, 4096):
        if max(w for w, _ in sizes) > AW:
            continue
        pos = [None] * len(sizes)
        x = y = rowh = 0
        for i in order:
            w, h = sizes[i]
            if x + w > AW:
                x, y, rowh = 0, y + rowh, 0
            pos[i] = (x, y)
            x += w
            rowh = max(rowh, h)
        AH = 1
        while AH < y + rowh:
            AH *= 2
        if best is None or AW * AH < best[1] * best[2]:
            best = (pos, AW, AH)
    return best


def hc(c):
    """Coordonnée (en u) d'une arête de gros cube repérée en demi-cubes."""
    return (c * 0.5 * K + (K - 1) / 2) * VOX


def build_fruit_data():
    """Calcule, pour tous les fruits : maillage grossier fusionné, textures, atlas."""
    import numpy as np
    data = []
    for i, (name, _) in enumerate(FRUITS):
        fine, solid = make_fruit(i)
        quads = greedy_quads(coarse_solid(solid))
        patches = [sample_patch(fine, q) for q in quads]
        data.append((name, len(fine), quads, patches))
    sizes = [(len(p[0]), len(p)) for d in data for p in d[3]]
    pos, AW, AH = pack_patches(sizes)
    atlas = np.full((AH, AW, 4), 140, dtype=np.uint8)
    atlas[..., 3] = 255
    n = 0
    placed = []
    for name, nf, quads, patches in data:
        pp = []
        for p in patches:
            x, y = pos[n]
            n += 1
            arr = np.array([[[round(clamp(c, 0, 1) * 255) for c in px] for px in row] for row in p], dtype=np.uint8)
            atlas[y:y + arr.shape[0], x:x + arr.shape[1], :3] = arr
            pp.append((x, y))
        placed.append(pp)
    return data, placed, atlas, AW, AH


def fruit_mesh(name, quads, places, AW, AH):
    """Maillage d'un fruit : sommets partagés, un rectangle par plan fusionné, UV dans l'atlas."""
    import bpy
    verts, vid, faces, uvs = [], {}, [], []

    def vi(c):
        i = vid.get(c)
        if i is None:
            i = vid[c] = len(verts)
            verts.append(c)
        return i
    e = 0.002
    for (axis, sign, s, cu, cv, w, h), (ax, ay) in zip(quads, places):
        u, v = (axis + 1) % 3, (axis + 2) % 3
        a = 2 * s + sign
        u0, u1, v0, v1 = 2 * cu - 1, 2 * (cu + w - 1) + 1, 2 * cv - 1, 2 * (cv + h - 1) + 1
        W, H = w * K, h * K
        quad, uv = [], []
        for (pu, pv), (tu, tv) in zip(((u0, v0), (u1, v0), (u1, v1), (u0, v1)),
                                      ((ax + e, ay + e), (ax + W - e, ay + e), (ax + W - e, ay + H - e), (ax + e, ay + H - e))):
            c = [0, 0, 0]
            c[axis], c[u], c[v] = a, pu, pv
            quad.append(vi(tuple(c)))
            uv.append((tu / AW, tv / AH))
        if sign < 0:
            quad.reverse()
            uv.reverse()
        faces.append(quad)
        uvs.extend(uv)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(hc(c[0]), hc(c[1]), hc(c[2])) for c in verts], [], faces)
    layer = me.uv_layers.new(name="UVMap")
    layer.data.foreach_set("uv", [t for uv in uvs for t in uv])
    me.update()
    return me


def mesh_stats():
    data, placed, atlas, AW, AH = build_fruit_data()
    rows = [(n, nf, len(q)) for n, nf, q, _ in data]
    return rows, AW, AH


# ======================================================================= scène
def image_from_array(name, arr, interp_pack=True):
    import bpy
    AH, AW = arr.shape[0], arr.shape[1]
    img = bpy.data.images.new(name, AW, AH, alpha=False)
    img.pixels.foreach_set((arr.astype("float32") / 255.0).ravel())
    img.file_format = "PNG"
    img.pack()
    return img


def textured_material(name, img, closest=True, emission=0.0):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.55
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = img
    t.interpolation = "Closest" if closest else "Linear"
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if emission:
        nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
        b.inputs["Emission Strength"].default_value = emission
    return m


def simple_material(name, color, rough=0.7):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    return m


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


def label_array(names):
    """Étiquettes (texte doré sur fond brun) dans une petite image : une bande par fruit."""
    import numpy as np
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
    arr = np.flipud(np.array(img))                               # Blender : l'axe v monte
    rgba = np.concatenate([arr, np.full(arr.shape[:2] + (1,), 255, np.uint8)], axis=2)
    return rgba, LW, LH, cols, rows


COLS, DX, DY = 9, 7.9, 10.2


def layout(i):
    n_row = [9, 9, len(FRUITS) - 18]
    row, col = divmod(i, COLS)
    n = n_row[row]
    return (col - (n - 1) / 2) * DX, row * DY, 1.5 + 2.8 * row


def stage_mesh(label_info):
    """UN seul maillage pour les 26 présentoirs, leurs plateaux et leurs étiquettes."""
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

    data, placed, atlas, AW, AH = build_fruit_data()
    img = image_from_array("Fruits_atlas", atlas)
    fmat = textured_material("Fruits", img, closest=True)
    label = label_array([d[0] for d in data])
    limg = image_from_array("Etiquettes", label[0])
    lmat = textured_material("Etiquettes", limg, closest=False, emission=0.9)
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

    coll = bpy.data.collections.new("Fruits")
    sc.collection.children.link(coll)
    for i, (name, nf, quads, patches) in enumerate(data):
        me = fruit_mesh(f"Fruit_{name}", quads, placed[i], AW, AH)
        me.materials.append(fmat)
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
    faces = sum(len(d[2]) for d in data)
    print(f"OK: {dst} ({len(FRUITS)} fruits, {faces} faces, atlas {AW}x{AH})")


if __name__ == "__main__":
    if "--stats" in sys.argv:
        rows, AW, AH = mesh_stats()
        tf = 0
        for n, nf, nq in rows:
            print(f"{n:26s} cubes fins {nf:6d}  faces fusionnees {nq:5d}")
            tf += nq
        print(f"{'TOTAL':26s} faces {tf}  atlas {AW}x{AH}")
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    build(args[-1])
