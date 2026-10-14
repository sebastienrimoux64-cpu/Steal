"""Arbres réalistes : ramification récursive (troncs cannelés, racines, branches effilées), feuillage feuille par feuille, fruits."""
import math
import random

from mathutils import Vector, Euler, Quaternion

import rmat
from rgeo import RB, V, fbm

UP = V(0, 0, 1)


def perp_basis(d):
    d = V(d).normalized()
    ref = UP if abs(d.z) < 0.9 else V(1, 0, 0)
    u = ref.cross(d).normalized()
    w = d.cross(u).normalized()
    return u, w


def child_dir(d, azimuth, angle):
    u, w = perp_basis(d)
    return (d * math.cos(angle) + (u * math.cos(azimuth) + w * math.sin(azimuth)) * math.sin(angle)).normalized()


def grow(b, bark, p0, d0, L, r0, r1, depth, sp, rng, twigs, trunk=False, seed=0):
    """Une branche (tube) + ses enfants. twigs reçoit (points, directions, rayons) des dernières ramilles pour le feuillage."""
    seg = sp.get("seg", 0.25) if r0 > 0.06 else (0.14 if r0 > 0.02 else 0.08)
    n = max(3, int(L / seg))
    d = V(d0).normalized()
    pts = [V(p0)]
    dirs = [d.copy()]
    for i in range(n):
        t = i / n
        j = sp["wob"] * (1.0 if depth else 0.45)
        d = d + V(rng.gauss(0, j), rng.gauss(0, j), rng.gauss(0, j) * 0.6)
        d.z += sp["up"] * (1.0 if depth < 2 else 0.5)
        d.z -= sp["droop"] * t * (1 if depth else 0.0)
        if sp.get("lean") and depth == 0:
            d += V(sp["lean"][0], sp["lean"][1], 0) * 0.04
        d.normalize()
        pts.append(pts[-1] + d * (L / n))
        dirs.append(d.copy())
    tp = sp["taper"] if not trunk else sp.get("trunk_taper", sp["taper"])
    rf = lambda t: r1 + (r0 - r1) * (1 - t) ** tp

    if trunk and sp.get("trunk_profile"):
        rf = sp["trunk_profile"]
    sides = 44 if r0 > 1.0 else 20 if r0 > 0.3 else 16 if r0 > 0.15 else 12 if r0 > 0.06 else 8 if r0 > 0.02 else 5
    fl = sp.get("flute", 0.0) if trunk else sp.get("flute_b", 0.0)
    b.tube(pts, rf, bark, sides=sides, flute=fl, flute_n=sp.get("flute_n", 5), seed=seed, cap_a=False, cap_b=True,
           noise_amp=(sp.get("bumps", 0.05) if r0 > 0.04 else 0.0), noise_f=1.3, twist=(sp.get("twist", 0.0) if trunk else sp.get("twist_b", 0.0)), uv_len=1.0)
    if depth < sp["max_depth"]:
        kids = sp["kids"][depth]
        for k in range(kids):
            t = rng.uniform(sp["kid_from"][depth], sp["kid_to"][depth])
            idx = min(n - 1, max(1, int(t * n)))
            base = pts[idx]
            dpar = (pts[idx + 1] - pts[idx]).normalized()
            az = k * 2.399963 + rng.uniform(-0.5, 0.5) + depth
            ang = math.radians(rng.uniform(*sp["angle"][depth]))
            cd = child_dir(dpar, az, ang)
            if depth + 1 >= sp.get("flat_from", 99):
                cd = V(cd.x, cd.y, cd.z * 0.3).normalized()
            if sp.get("phototropism"):
                cd = (cd + UP * sp["phototropism"]).normalized()
            Lc = L * sp["len_ratio"][depth] * rng.uniform(0.75, 1.1) * (1.0 - 0.35 * (t if not trunk else 0.0))
            if trunk and sp.get("branch_len"):
                Lc = sp["branch_len"](t) * rng.uniform(0.85, 1.12)
            rc = rf(t) * sp["rad_ratio"][depth]
            grow(b, bark, base - cd * (rc * 0.8), cd, Lc, rc, max(rc * sp["end_ratio"], 0.004), depth + 1, sp, rng, twigs, seed=seed + k + 1)
    if depth >= sp["max_depth"] - 1 or r0 < 0.03:
        twigs.append((pts, dirs, r0))
    return pts


def scatter_leaves(b, mat, twigs, rng, per_twig=7, size=(0.07, 0.04), shape="ovate", frac=(0.35, 1.0), spread=0.05, curl=0.3, droop=0.25, fold=0.25, seg=3, max_r=0.03):
    cnt = 0
    for pts, dirs, r0 in twigs:
        if r0 > max_r * 3:
            continue
        n = len(pts)
        for k in range(per_twig):
            i = int(rng.uniform(frac[0], frac[1]) * (n - 1))
            p = pts[i]
            d = dirs[i]
            off = V(rng.gauss(0, spread), rng.gauss(0, spread), rng.gauss(0, spread))
            az = rng.uniform(0, 6.283)
            ld = child_dir(d, az, math.radians(rng.uniform(25, 75)))
            ld.z -= droop * rng.uniform(0, 1)
            ld.normalize()
            up = (UP + V(rng.gauss(0, 0.3), rng.gauss(0, 0.3), 0)).normalized()
            s = rng.uniform(0.8, 1.25)
            b.leaf(p + off, ld, up, size[0] * s, size[1] * s, mat, curl=curl * rng.uniform(0.5, 1.4), twist=rng.uniform(-0.4, 0.4), rand=rng.random(), seg=seg, shape=shape, fold=fold)
            cnt += 1
    return cnt


def roots(b, bark, r_trunk, n=6, spread=1.4, rng=None, z0=0.5):
    rng = rng or random.Random(3)
    for k in range(n):
        a = k * 2 * math.pi / n + rng.uniform(-0.3, 0.3)
        d = V(math.cos(a), math.sin(a), 0)
        path = [d * r_trunk * 0.5 + V(0, 0, z0), d * (r_trunk * 1.1) + V(0, 0, z0 * 0.35), d * (r_trunk + spread * 0.45) + V(0, 0, 0.05), d * (r_trunk + spread) + V(0, 0, -0.12)]
        # ondulation
        path = [p + V(-d.y, d.x, 0) * 0.12 * math.sin(i * 1.7 + k) for i, p in enumerate(path)]
        b.tube(path, lambda t, r=r_trunk: r * (0.42 * (1 - t) ** 1.2 + 0.05), bark, sides=10, noise_amp=0.1, flute=0.05, seed=k)


# ============================================================ POMMIER
def a_pommier(b):
    rng = random.Random(21)
    bark = rmat.bark("EcorcePommier", "furrowed", dark=(0.05, 0.04, 0.035), mid=(0.20, 0.17, 0.14), light=(0.40, 0.36, 0.31), around=3.0, along=0.4, lichen=0.35, moss=0.15)
    leaf = rmat.leaf("FeuillePommier", top=(0.09, 0.22, 0.035), top2=(0.17, 0.33, 0.06), under=(0.30, 0.42, 0.18), translucency=0.35)
    apple = rmat.apple("Pomme")
    stem_m = rmat.fruit_simple("QueuePomme", (0.25, 0.17, 0.08), 0.8)
    sp = dict(max_depth=3, kids=[11, 5, 5, 4], kid_from=[0.4, 0.2, 0.2, 0.2], kid_to=[0.97, 0.9, 0.9, 0.9], angle=[(48, 78), (35, 70), (30, 70), (30, 70)], len_ratio=[0.55, 0.6, 0.6, 0.6], rad_ratio=[0.46, 0.6, 0.6, 0.6],
              end_ratio=0.25, wob=0.12, up=0.03, droop=0.17, taper=0.9, seg=0.25, flute=0.05, flute_n=4, bumps=0.06, phototropism=0.1, trunk_taper=0.7, twist=0.6,
              lean=(0.3, 0.1), branch_len=lambda t: 2.9 * (1.0 - 0.35 * t))
    twigs = []
    grow(b, bark, V(0, 0, -0.1), V(0.06, 0.02, 1), 2.3, 0.27, 0.1, 0, sp, rng, twigs, trunk=True, seed=2)
    roots(b, bark, 0.27, 6, 0.9, rng)
    n = scatter_leaves(b, leaf, twigs, rng, per_twig=70, size=(0.1, 0.058), shape="ovate", frac=(0.05, 1.0), spread=0.08, curl=0.35, droop=0.3, seg=3, max_r=0.02)
    # pommes suspendues
    cands = [(pts, dirs) for pts, dirs, r in twigs if r < 0.03]
    for k in range(34):
        pts, dirs = cands[rng.randrange(len(cands))]
        i = rng.randrange(max(1, len(pts) // 2), len(pts))
        p = pts[i]
        L = rng.uniform(0.03, 0.05)
        b.tube([p, p + V(0.004, 0, -L * 0.6), p + V(0.006, 0.002, -L)], [0.0025, 0.0022, 0.002], stem_m, sides=4, cap_b=True)
        r_ = rng.uniform(0.036, 0.046)
        b.rock(p + V(0.006, 0.002, -L - r_ * 0.85), (r_, r_, r_ * 0.92), apple, seed=300 + k, sub=3, planes=0, amp=0.03, ridge=0.0, detail=0.0, freq=2.0, sharp=90, sph_uv=True)
    print("pommier feuilles", n)


# ============================================================ OLIVIER
def a_olivier(b):
    rng = random.Random(33)
    bark = rmat.bark("EcorceOlivier", "plates", dark=(0.04, 0.035, 0.03), mid=(0.19, 0.165, 0.135), light=(0.42, 0.38, 0.32), around=2.5, along=0.5, lichen=0.3, scale=0.9)
    leaf = rmat.leaf("FeuilleOlivier", top=(0.10, 0.19, 0.06), top2=(0.17, 0.27, 0.09), under=(0.55, 0.60, 0.50), translucency=0.25, silver=0.95, gloss=0.2)
    olive = rmat.fruit_simple("Olive", (0.12, 0.10, 0.05), 0.25)
    olive_g = rmat.fruit_simple("OliveVerte", (0.25, 0.32, 0.10), 0.25)
    sp = dict(max_depth=4, kids=[5, 5, 4, 4, 3], kid_from=[0.55, 0.2, 0.2, 0.2, 0.2], kid_to=[0.95, 0.9, 0.9, 0.9, 0.9], angle=[(30, 55), (30, 60), (30, 65), (30, 70), (30, 70)], len_ratio=[0.9, 0.62, 0.6, 0.6, 0.6],
              rad_ratio=[0.52, 0.62, 0.6, 0.6, 0.6], end_ratio=0.3, wob=0.22, up=0.03, droop=0.08, taper=0.9, seg=0.2, flute=0.20, flute_n=4, flute_b=0.08, bumps=0.1, phototropism=0.12,
              trunk_taper=0.6, twist=2.8, twist_b=1.6, lean=(0.3, -0.2), branch_len=lambda t: 1.7 * (1.0 - 0.3 * t))
    twigs = []
    grow(b, bark, V(0, 0, -0.1), V(0.1, -0.05, 1), 1.9, 0.34, 0.14, 0, sp, rng, twigs, trunk=True, seed=4)
    roots(b, bark, 0.34, 7, 0.8, rng, z0=0.35)
    n = scatter_leaves(b, leaf, twigs, rng, per_twig=44, size=(0.085, 0.016), shape="lance", frac=(0.05, 1.0), spread=0.05, curl=0.2, droop=0.15, seg=2, max_r=0.02, fold=0.4)
    cands = [(pts, dirs) for pts, dirs, r in twigs if r < 0.03]
    for k in range(60):
        pts, dirs = cands[rng.randrange(len(cands))]
        i = rng.randrange(max(1, len(pts) // 2), len(pts))
        p = pts[i] + V(rng.gauss(0, .02), rng.gauss(0, .02), -0.015)
        b.rock(p, (0.0105, 0.0105, 0.015), olive if k % 3 else olive_g, seed=400 + k, sub=2, planes=0, amp=0.02, ridge=0.0, detail=0.0, sharp=90)
    print("olivier feuilles", n)


# ============================================================ BAOBAB
def a_baobab(b):
    rng = random.Random(45)
    bark = rmat.bark("EcorceBaobab", "smooth", dark=(0.07, 0.05, 0.035), mid=(0.25, 0.185, 0.135), light=(0.45, 0.35, 0.26), around=2.2, along=0.3, scale=0.8, lichen=0.06)
    leaf = rmat.leaf("FeuilleBaobab", top=(0.10, 0.24, 0.05), top2=(0.18, 0.34, 0.07), under=(0.26, 0.38, 0.14), translucency=0.35)
    pod = rmat.velvet_pod()
    stem_m = rmat.fruit_simple("PedonculeBaobab", (0.3, 0.24, 0.16), 0.9)
    H = 4.9

    def prof(t):
        flare = 1.0 + 0.45 * math.exp(-t * 11.0)
        body = 0.92 + 0.2 * math.sin(math.pi * t ** 0.72) - 0.36 * t ** 2.2
        return 1.9 * flare * body
    sp = dict(max_depth=3, kids=[10, 3, 3, 3], kid_from=[0.84, 0.35, 0.3, 0.2], kid_to=[0.99, 0.92, 0.9, 0.9], angle=[(40, 70), (25, 60), (25, 65), (30, 70)], len_ratio=[0.5, 0.6, 0.62, 0.6],
              rad_ratio=[0.34, 0.6, 0.6, 0.6], end_ratio=0.2, wob=0.1, up=0.02, droop=0.05, taper=0.85, seg=0.3, flute=0.09, flute_n=11, bumps=0.11, trunk_profile=prof, twist=0.0,
              branch_len=lambda t: 4.6, phototropism=0.15)
    twigs = []
    grow(b, bark, V(0, 0, -0.4), V(0.015, 0.01, 1), H, 1.9, 1.1, 0, sp, rng, twigs, trunk=True, seed=6)
    n = 0
    for pts, dirs, r in twigs:
        if r > 0.06:
            continue
        for k in range(rng.randint(2, 5)):
            i = rng.randint(max(0, len(pts) - 4), len(pts) - 1)
            p = pts[i]
            ax = rng.uniform(0, 6.283)
            for j in range(5):
                a = ax + (j - 2) * 0.55
                d = child_dir(dirs[i], a, math.radians(70))
                d.z -= 0.15
                b.leaf(p, d.normalized(), UP, rng.uniform(0.2, 0.3), 0.06, leaf, curl=0.4, twist=0.2, rand=rng.random(), seg=3, shape="lance", fold=0.3)
                n += 1
    for k in range(8):
        pts, dirs, r = twigs[rng.randrange(len(twigs))]
        p = pts[-1]
        Ls = rng.uniform(0.4, 0.7)
        path = [p, p + V(0.02, 0, -Ls * 0.4), p + V(0.03, 0.01, -Ls)]
        b.tube(path, [0.014, 0.012, 0.011], stem_m, sides=6, cap_b=True)
        b.rock(p + V(0.03, 0.01, -Ls - 0.2), (0.085, 0.085, 0.22), pod, seed=500 + k, sub=4, planes=0, amp=0.04, ridge=0.0, detail=0.0, sharp=90)
    print("baobab feuilles", n)


# ============================================================ ACACIA
def compound_leaf(b, mat, p, d, length, pairs, ls, rng, wl=0.35, droop=0.15):
    """Feuille composée bipennée d'acacia : rachis + paires de petites folioles ovales."""
    d = V(d).normalized()
    side = d.cross(UP).normalized()
    for i in range(pairs):
        t = (i + 1) / (pairs + 1)
        q = p + d * (length * t)
        s = ls * (1.0 - 0.4 * abs(t - 0.5))
        for sg in (-1, 1):
            ld = (d * 0.55 + side * sg * 0.85)
            ld.z -= droop
            ld.normalize()
            b.leaf(q, ld, UP, s, s * wl, mat, curl=0.2, twist=0.0, rand=rng.random(), seg=1, shape="round", fold=0.15)


def a_acacia(b):
    rng = random.Random(57)
    bark = rmat.bark("EcorceAcacia", "plates", dark=(0.03, 0.025, 0.02), mid=(0.14, 0.11, 0.085), light=(0.30, 0.25, 0.20), around=2.2, along=0.5, scale=1.0, lichen=0.1)
    spray = rmat.leaflet_spray("RameauAcacia")
    sp = dict(max_depth=4, kids=[5, 5, 5, 5, 4], kid_from=[0.9, 0.4, 0.25, 0.2, 0.2], kid_to=[0.99, 0.95, 0.9, 0.9, 0.9], angle=[(32, 58), (30, 60), (55, 88), (55, 88), (55, 88)], len_ratio=[0.85, 0.55, 0.6, 0.6, 0.6],
              rad_ratio=[0.55, 0.6, 0.6, 0.6, 0.6], end_ratio=0.28, wob=0.1, up=0.02, droop=-0.03, taper=0.85, seg=0.22, flute=0.07, flute_n=4, bumps=0.06, phototropism=0.0, trunk_taper=0.8, twist=0.8,
              lean=(0.25, 0.05), branch_len=lambda t: 2.9, flat_from=3)
    twigs = []
    grow(b, bark, V(0, 0, -0.1), V(0.12, 0.03, 1), 3.3, 0.2, 0.1, 0, sp, rng, twigs, trunk=True, seed=8)
    roots(b, bark, 0.2, 5, 0.6, rng, z0=0.3)
    n = 0
    for pts, dirs, r in twigs:
        if r > 0.03:
            continue
        for i in range(1, len(pts)):
            p = pts[i]
            if p.z < 3.2:
                continue
            for k in range(8):
                az = rng.uniform(0, 6.283)
                d = V(math.cos(az), math.sin(az), rng.uniform(-0.05, 0.25))
                b.leaf(p + V(rng.gauss(0, .05), rng.gauss(0, .05), rng.gauss(0, .03)), d.normalized(), UP, rng.uniform(0.28, 0.4), rng.uniform(0.15, 0.22), spray, curl=0.15, droop=0.1,
                       twist=0.0, rand=rng.random(), seg=2, shape="rect", fold=0.08)
                n += 1
    print("acacia amas", n)


# ============================================================ SAPIN ENNEIGÉ
def a_sapin_enneige(b, snow=True):
    rng = random.Random(61)
    bark = rmat.bark("EcorceSapin", "scaly", dark=(0.03, 0.02, 0.018), mid=(0.16, 0.10, 0.07), light=(0.30, 0.20, 0.14), around=3.0, along=0.6, scale=1.1)
    needles = rmat.needles("RameauSapin", snow=0.5 if snow else 0.0)
    snow_m = rmat.ground("NeigeAmas", "snow")
    H = 9.0
    path = [V(0.05 * math.sin(i * 0.9), 0.04 * math.cos(i * 0.7), -0.2 + (H + 0.2) * i / 12) for i in range(13)]
    b.tube(path, lambda t: 0.30 * (1 - t) ** 0.95 * (1 + 0.5 * math.exp(-t * 12)) + 0.012, bark, sides=16, flute=0.05, flute_n=7, noise_amp=0.05, cap_b=True)
    trunk_r = lambda z: 0.30 * (1 - (z + 0.2) / (H + 0.2)) ** 0.95 + 0.012
    nw = 21
    cards = 0
    for w in range(nw):
        z = 1.2 + w * 0.36
        fr = (z - 1.2) / (H - 1.4)
        Lb = 2.7 * (1 - fr) ** 0.85 + 0.25
        nb = 7 if w % 2 == 0 else 6
        for k in range(nb):
            az = k * 2 * math.pi / nb + w * 0.9 + rng.uniform(-0.25, 0.25)
            dh = V(math.cos(az), math.sin(az), 0)
            Lk = Lb * rng.uniform(0.85, 1.1)
            base = V(path[min(12, int((z + 0.2) / (H + 0.2) * 12))].x, path[min(12, int((z + 0.2) / (H + 0.2) * 12))].y, z) + dh * trunk_r(z) * 0.8
            pts = []
            for i in range(9):
                s = i / 8
                pos = base + dh * (s * Lk)
                pos.z += -0.34 * Lk * (s ** 1.6) * (0.5 + 0.5 * (1 - fr)) + 0.28 * Lk * (s ** 3.2) + 0.02 * math.sin(s * 5 + k)
                pos += V(-dh.y, dh.x, 0) * 0.08 * math.sin(s * 3 + w + k)
                pts.append(pos)
            b.tube(pts, lambda t: 0.032 * (1 - t) ** 0.8 * (0.4 + 0.6 * (Lk / 2.5)) + 0.004, bark, sides=6, cap_b=True)
            # rameaux à aiguilles
            for i in range(1, 21):
                s = i / 21
                idx = min(7, int(s * 8))
                f2 = s * 8 - idx
                p = pts[idx].lerp(pts[idx + 1], f2)
                tdir = (pts[idx + 1] - pts[idx]).normalized()
                side = tdir.cross(UP).normalized()
                lc = (0.12 + 0.55 * math.sin(math.pi * (0.1 + 0.8 * s)) * min(1.0, Lk / 1.8)) * rng.uniform(0.85, 1.15)
                for sg in (-1, 1):
                    for layer in range(3):
                        d = (tdir * 0.5 + side * sg * 0.85 + V(0, 0, -0.28 + 0.16 * layer)).normalized()
                        wdt = 0.27 * (0.6 + 0.4 * min(1.0, Lk / 1.8))
                        b.leaf(p + V(0, 0, 0.012 * layer), d, UP, lc, wdt, needles, curl=0.25, droop=0.18, twist=0.0, rand=rng.random(), seg=2, shape="rect", fold=0.12)
                        cards += 1
            # neige : gros amas sur le dessus des branches
            if snow:
                for i in range(2, 8):
                    if rng.random() < 0.35:
                        p = pts[i] + V(rng.gauss(0, .05), rng.gauss(0, .05), 0.045)
                        rs = rng.uniform(0.08, 0.15) * min(1.0, 0.4 + Lk / 2.0)
                        b.rock(p, (rs * 1.4, rs, rs * 0.45), snow_m, seed=int(rng.random() * 1000), sub=2, planes=0, amp=0.25, ridge=0.0, detail=0.0, sharp=90)
    print("sapin cartes", cards)


# ============================================================ ARBRE DE LA JUNGLE (kapokier)
def a_arbre_jungle(b):
    rng = random.Random(83)
    bark = rmat.bark("EcorceKapokier", "scaly", dark=(0.05, 0.045, 0.04), mid=(0.20, 0.18, 0.15), light=(0.34, 0.31, 0.26), around=2.5, along=0.5, moss=0.55, lichen=0.1, scale=0.9)
    leaf = rmat.leaf("FeuilleKapokier", top=(0.05, 0.17, 0.03), top2=(0.10, 0.28, 0.05), under=(0.18, 0.32, 0.10), translucency=0.4, gloss=0.55)
    liane_m = rmat.bark("Liane", "furrowed", dark=(0.04, 0.03, 0.02), mid=(0.16, 0.12, 0.08), light=(0.30, 0.24, 0.16), around=2.0, along=1.5, moss=0.4)
    brom = rmat.leaf("Bromelie", top=(0.08, 0.22, 0.05), top2=(0.20, 0.38, 0.08), under=(0.22, 0.38, 0.12), translucency=0.3)
    H = 11.5
    # contreforts : ailerons verticaux minces
    for k in range(7):
        a = k * 2 * math.pi / 7 + rng.uniform(-0.2, 0.2)
        d = V(math.cos(a), math.sin(a), 0)
        t = V(-d.y, d.x, 0)
        Lr = rng.uniform(2.0, 3.0)
        Hf = rng.uniform(3.2, 4.4)
        rings = []
        for i in range(21):
            s = i / 20
            r = 0.45 + s * Lr
            h = Hf * (1 - s) ** 2.3 + 0.15 * (1 - s)
            th = 0.14 * (1 - 0.55 * s) + 0.03
            wob = 0.18 * math.sin(s * 5 + k)
            pts = [(-th, -0.5), (th, -0.5), (th * 1.05, h * 0.92), (th * 0.35, h), (-th * 0.35, h), (-th * 1.05, h * 0.92)]
            ring = [d * r + t * (x + wob) + V(0, 0, z) for x, z in pts]
            rings.append(ring)
        b.loft(rings, bark, uvfn=lambda u, v, co: (v, co.z), closed=True, smooth=True, cap_a=False, cap_b=True)
    # tronc
    path = [V(0.12 * math.sin(i * 0.6), 0.1 * math.cos(i * 0.5), -0.5 + (H + 0.5) * i / 14) for i in range(15)]
    b.tube(path, lambda t: 0.62 * (1 - 0.35 * t) * (1 + 0.28 * math.exp(-t * 10)), bark, sides=24, flute=0.04, flute_n=6, noise_amp=0.05, cap_b=True)
    # couronne en parasol
    sp = dict(max_depth=3, kids=[7, 6, 5, 3], kid_from=[0.2, 0.25, 0.2, 0.2], kid_to=[0.95, 0.9, 0.9, 0.9], angle=[(40, 70), (30, 65), (30, 70), (30, 70)], len_ratio=[0.6, 0.6, 0.6, 0.6],
              rad_ratio=[0.6, 0.65, 0.65, 0.65], end_ratio=0.3, wob=0.1, up=0.03, droop=0.06, taper=0.85, seg=0.3, flute_b=0.04, bumps=0.06, phototropism=0.2)
    twigs = []
    top = path[-1]
    for k in range(8):
        a = k * 2 * math.pi / 8 + 0.3
        d0 = child_dir(V(0, 0, 1), a, math.radians(rng.uniform(50, 68)))
        grow(b, bark, top + V(0, 0, -0.3 - 0.5 * (k % 3)), d0, rng.uniform(4.4, 6.0), 0.28, 0.08, 1, sp, rng, twigs, seed=k)
    n = 0
    for pts, dirs, r in twigs:
        if r > 0.04:
            continue
        for j in range(1, len(pts)):
            p = pts[j]
            for k in range(3):
                ab = rng.uniform(0, 6.283)
                for f in range(7):
                    off = (f - 3) * 0.42
                    d1 = V(math.cos(ab + off), math.sin(ab + off), 0.25 - abs(off) * 0.35)
                    b.leaf(p + d1.normalized() * 0.03, d1.normalized(), UP, 0.48 - 0.04 * abs(f - 3), 0.1, leaf, curl=0.4, droop=0.3, rand=rng.random(), seg=3, shape="lance", fold=0.3)
                    n += 1
    # lianes pendantes
    for k in range(11):
        pts0, dirs0, r0 = twigs[rng.randrange(len(twigs))]
        p = pts0[rng.randrange(1, len(pts0))]
        path_l = []
        for j in range(24):
            t = j / 23
            path_l.append(V(p.x * (1 - t) + 0.9 * math.cos(k) * t + 0.15 * math.sin(t * 9 + k), p.y * (1 - t) + 0.9 * math.sin(k) * t + 0.15 * math.cos(t * 7), p.z * (1 - t) + 0.05))
        b.tube(path_l, lambda t: 0.035 * (1 - 0.5 * t) + 0.01, liane_m, sides=8, flute=0.15, flute_n=4, twist=8.0, noise_amp=0.1, cap_b=True)
    # bromélias épiphytes sur les branches basses
    for k in range(8):
        pts0, dirs0, r0 = twigs[rng.randrange(len(twigs))]
        if r0 < 0.01:
            continue
        p = pts0[rng.randrange(1, max(2, len(pts0) // 2))]
        for j in range(14):
            ab = j * 0.9
            b.leaf(p + V(0, 0, 0.05), V(math.cos(ab), math.sin(ab), 0.9), UP, rng.uniform(0.22, 0.38), 0.05, brom, curl=0.6, droop=0.2, rand=rng.random(), seg=4, shape="lance", fold=0.4)
    print("jungle feuilles", n)
