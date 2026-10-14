"""Accessoires réalistes : citrouilles, pomme de pin, branche, bûches empilées, tas de feuilles, amanites, clôture, panneau, panier d'osier, motte d'herbe, mousse."""
import math
import random

from mathutils import Euler, Vector

import rmat
import scatter
from rgeo import RB, V, fbm
from a_wood import birch_peel  # noqa: F401

UP = V(0, 0, 1)


def _rings_pumpkin(c, R, H, lobes, tilt, seed, N_lat=46, N_az=96):
    M = Euler(tilt).to_matrix()
    rings = []
    for i in range(N_lat + 1):
        t = i / N_lat
        th = math.pi * t
        z = H * 0.5 * (1 - math.cos(th))
        rr = R * max(math.sin(th), 0.0) ** 0.6
        if t > 0.8:
            z -= H * 0.14 * math.sin(math.pi * (t - 0.8) / 0.2)
        if t < 0.12:
            z += H * 0.035 * math.sin(math.pi * t / 0.12)
        ring = []
        for j in range(N_az):
            a = 2 * math.pi * j / N_az
            k = 1 + 0.078 * math.cos(lobes * a) * (math.sin(th) ** 0.7) + 0.02 * fbm(V((math.cos(a) * 1.3 + seed, math.sin(a) * 1.3, t * 2.0)), 3)
            p = V((math.cos(a) * max(rr * k, 0.0008), math.sin(a) * max(rr * k, 0.0008), z))
            ring.append(V(c) + M @ p)
        rings.append(ring)
    return rings, M


def pumpkin(b, c, R, H, mat, stem_m, lobes=10, tilt=(0, 0, 0), seed=0):
    rings, M = _rings_pumpkin(c, R, H, lobes, tilt, seed)
    cz = V(c).z
    b.loft(rings, mat, uvfn=lambda u, v, co: (v, (M.inverted() @ (co - V(c))).z), closed=True, smooth=True, cap_a=False, cap_b=False)
    top = V(c) + M @ V(0, 0, H * 0.86)
    path = [top + M @ V(0, 0, -0.02), top + M @ V(0.004, 0, 0.04), top + M @ V(0.02, 0.006, 0.09), top + M @ V(0.05, 0.015, 0.115), top + M @ V(0.075, 0.02, 0.1)]
    b.tube(path, lambda t: 0.034 * (1 - 0.35 * t) * (1 + 0.5 * math.exp(-t * 7)), stem_m, sides=10, flute=0.12, flute_n=5, twist=1.2, cap_b=True, noise_amp=0.05)


def a_citrouille(b):
    mat = rmat.pumpkin("Citrouille")
    stem = rmat.stem_green("QueueCitrouille", (0.20, 0.27, 0.09))
    pumpkin(b, V(0, 0, 0), 0.42, 0.62, mat, stem, 10, (0.02, 0.03, 0), 1.0)
    grass = rmat.grass_blade("HerbePotager", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0.0, 0.0), (1.1, 1.1), 40, random.Random(2), hmin=0.1, hmax=0.3, avoid=lambda x, y: math.hypot(x, y) < 0.42)
    return b


def a_citrouilles_groupe(b):
    rng = random.Random(9)
    mat = rmat.pumpkin("Citrouille")
    mat2 = rmat.pumpkin("CitrouillePale", color=(0.86, 0.45, 0.10), lobes=12)
    stem = rmat.stem_green("QueueCitrouille", (0.20, 0.27, 0.09))
    leaf = rmat.leaf("FeuilleCourge", top=(0.10, 0.24, 0.045), top2=(0.17, 0.34, 0.07), under=(0.28, 0.42, 0.16), translucency=0.3)
    vine_m = rmat.stem_green("LianeCourge", (0.18, 0.25, 0.08))
    pumpkin(b, V(0, 0, 0), 0.4, 0.58, mat, stem, 10, (0.02, 0.0, 0.3), 1)
    pumpkin(b, V(0.74, 0.3, 0), 0.3, 0.42, mat2, stem, 12, (0.12, 0.05, 0.9), 2)
    pumpkin(b, V(-0.2, 0.78, 0), 0.24, 0.34, mat, stem, 9, (-0.15, 0.1, 2.0), 3)
    pumpkin(b, V(-0.78, -0.3, 0), 0.2, 0.28, mat2, stem, 11, (0.1, -0.1, 4.0), 4)
    vine = [V(0.5, 0.35, 0.03), V(0.2, 0.62, 0.035), V(-0.1, 0.5, 0.03), V(-0.5, 0.25, 0.03), V(-0.9, 0.4, 0.035), V(-1.3, 0.2, 0.03)]
    b.tube(vine, lambda t: 0.014 * (1 - 0.6 * t) + 0.004, vine_m, sides=7, noise_amp=0.08, flute=0.1, flute_n=5)
    for p, a in [(V(0.2, 0.62, 0.05), 1.0), (V(-0.5, 0.25, 0.05), -0.6), (V(-0.9, 0.4, 0.05), 2.4), (V(0.55, -0.15, 0.05), 0.5), (V(-0.1, 0.5, 0.05), 3.0)]:
        stalk = [p, p + V(0.03, 0.02, 0.12), p + V(0.1, 0.06, 0.22)]
        b.tube(stalk, [0.01, 0.009, 0.008], vine_m, sides=6, cap_b=True)
        d = V(math.cos(a), math.sin(a), 0.1)
        b.leaf(stalk[-1], d.normalized(), UP, 0.34, 0.36, leaf, curl=0.3, droop=0.3, twist=0.0, rand=rng.random(), seg=6, shape="round", fold=0.18)
    grass = rmat.grass_blade("HerbePotager", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (-0.1, 0.1), (1.7, 1.2), 70, rng, hmin=0.1, hmax=0.3, avoid=lambda x, y: min(math.hypot(x - cx, y - cy) for cx, cy in [(0, 0), (0.74, 0.3), (-0.2, 0.78), (-0.78, -0.3)]) < 0.4)
    return b


def scale_cone(b, c, Lc, Rm, tilt, mat, mat_in, seed):
    """Pomme de pin faite de vraies écailles (phyllotaxie 137,5°), chaque écaille = losange épais dirigé vers le haut et l'extérieur."""
    rng = random.Random(seed)
    M = Euler(tilt).to_matrix()
    n = 120
    for k in range(n):
        t = k / (n - 1)
        a = math.radians(137.5) * k
        z = Lc * (0.04 + 0.92 * t)
        rr = Rm * math.sin(math.pi * (0.12 + 0.88 * t)) ** 0.8 * (1 - 0.25 * t)
        out = V(math.cos(a), math.sin(a), 0)
        side = V(-math.sin(a), math.cos(a), 0)
        w = (0.034 + 0.1 * Rm) * (0.7 + 0.5 * math.sin(math.pi * t)) * 0.5
        h = Lc * 0.085
        base = out * (rr * 0.45) + V(0, 0, z)
        tip = out * (rr + 0.006) + V(0, 0, z + h * 0.5)
        mid = out * (rr * 0.85) + V(0, 0, z + h * 0.25)
        th = 0.0045 + 0.004 * (1 - t)
        pts = [base, mid, tip]
        # losange : 3 colonnes (gauche, centre, droite) x 3 rangées
        rows = []
        for q, wf in ((base, 0.35), (mid, 1.0), (tip, 0.55)):
            rows.append([c + M @ (q - side * w * wf), c + M @ (q + out * th * 0.4), c + M @ (q + side * w * wf)])
        b.loft(rows, mat, uvfn=lambda u, v, co: (v, u), closed=False, smooth=True)
        # tranche (épaisseur) sombre
        rows2 = [[c + M @ (q - side * w * wf - out * th), c + M @ (q - out * th), c + M @ (q + side * w * wf - out * th)] for q, wf in ((base, 0.35), (mid, 1.0), (tip, 0.55))]
        b.loft(rows2, mat_in, uvfn=lambda u, v, co: (v, u), closed=False, smooth=True)


def a_pomme_de_pin(b):
    rng = random.Random(4)
    mat = rmat.pine_scale("EcailleDePin", (0.34, 0.20, 0.09), (0.55, 0.40, 0.22))
    mat_in = rmat.pine_scale("EcailleDePinFond", (0.08, 0.05, 0.03), (0.16, 0.10, 0.05))
    for k, (c, tilt, s) in enumerate([(V(0, 0, 0.07), (1.5, 0, 0.3), 1.0), (V(0.3, 0.2, 0.065), (1.45, 0, 2.0), 0.85), (V(-0.22, 0.28, 0.06), (1.4, 0, 3.8), 0.7)]):
        scale_cone(b, c, 0.2 * s, 0.075 * s, tilt, mat, mat_in, 10 + k)
    needles = rmat.dead_leaf("AiguilleSeche")
    for k in range(70):
        a = rng.uniform(0, 6.283)
        r = math.sqrt(rng.random()) * 0.7
        d = V(math.cos(rng.uniform(0, 6.283)), math.sin(rng.uniform(0, 6.283)), 0.0)
        p = V(math.cos(a) * r, math.sin(a) * r, 0.01)
        b.tube([p, p + d * 0.06, p + d * 0.12 + V(0, 0, 0.003)], [0.0016, 0.0015, 0.001], needles, sides=3, cap_b=True)
    grass = rmat.grass_blade("HerbePin", base=(0.05, 0.11, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.8, 0.7), 20, rng, hmin=0.08, hmax=0.25, avoid=lambda x, y: math.hypot(x, y) < 0.3)
    return b


def a_branche(b):
    rng = random.Random(15)
    bark = rmat.bark("EcorceBranche", "furrowed", dark=(0.05, 0.04, 0.03), mid=(0.2, 0.16, 0.12), light=(0.38, 0.32, 0.25), around=2.5, along=0.6, moss=0.1, lichen=0.3)
    endg = rmat.end_grain("BoutBranche", light=(0.74, 0.60, 0.42), dark=(0.50, 0.36, 0.22), bark_ring=(0.3, 0.24, 0.18), rings=14)
    main = []
    for i in range(14):
        t = i / 13
        main.append(V(-1.0 + 2.0 * t, 0.06 * math.sin(t * 5), 0.09 + 0.045 * math.sin(t * 4 + 1) + 0.04 * (1 - abs(2 * t - 1))))
    b.tube(main, lambda t: 0.075 * (1 - 0.5 * t) + 0.012, bark, sides=16, noise_amp=0.08, noise_f=1.3, flute=0.04, flute_n=3, cap_a=True, cap_b=True, cap_mat=endg, cap_disc=True, seed=3)
    for t, d, L, r in [(0.22, V(0.6, 0.8, 0.35), 0.7, 0.04), (0.5, V(0.4, -0.85, 0.4), 0.8, 0.045), (0.75, V(0.7, 0.55, 0.5), 0.55, 0.032)]:
        i = int(t * 13)
        p0 = main[i].lerp(main[i + 1], t * 13 - i)
        dd = d.normalized()
        pts = [p0 - dd * 0.02, p0 + dd * L * 0.4 + V(0, 0, 0.03), p0 + dd * L * 0.8 + V(0, 0, 0.02), p0 + dd * L]
        b.tube(pts, lambda tt, r=r: r * (1 - 0.7 * tt) + 0.006, bark, sides=10, noise_amp=0.08, cap_b=True, cap_mat=endg, cap_disc=True, seed=int(t * 10))
        for j in range(2):
            e = pts[2]
            d2 = (dd + V(0.4 * (j * 2 - 1), 0.6 * (j * 2 - 1), 0.3)).normalized()
            b.tube([e, e + d2 * 0.14], [0.012, 0.007], bark, sides=6, cap_b=True, cap_mat=endg, cap_disc=True)
    grass = rmat.grass_blade("HerbeBranche", base=(0.05, 0.11, 0.02), tip=(0.28, 0.38, 0.08))
    dead = rmat.dead_leaf()
    scatter.field(b, grass, (0, 0), (1.3, 0.7), 45, rng, hmin=0.1, hmax=0.3, avoid=lambda x, y: abs(y) < 0.14)
    scatter.leaf_litter(b, dead, (0, 0), (1.3, 0.7), 70, rng)
    return b


def a_buches_empilees(b):
    rng = random.Random(17)
    bark = rmat.bark("EcorceChene", "furrowed", dark=(0.04, 0.03, 0.025), mid=(0.17, 0.13, 0.10), light=(0.36, 0.30, 0.23), around=3.0, along=0.5, lichen=0.15)
    endg = rmat.end_grain("BoutChene", light=(0.76, 0.58, 0.36), dark=(0.52, 0.34, 0.18), bark_ring=(0.26, 0.2, 0.15), rings=18, cracks=1.0)
    rows = [5, 4, 3, 2]
    for ri, cnt in enumerate(rows):
        for k in range(cnt):
            r = rng.uniform(0.09, 0.125)
            x = (k - (cnt - 1) / 2) * 0.2
            z = 0.11 + ri * 0.177
            L = 0.95 + rng.uniform(-0.06, 0.06)
            yo = rng.uniform(-0.05, 0.05)
            path = [V(x + rng.uniform(-.005, .005), -L / 2 + yo + L * i / 8, z + 0.005 * math.sin(i)) for i in range(9)]
            b.tube(path, [r * (1 + 0.03 * math.sin(i * 1.7 + k)) for i in range(9)], bark, sides=18, noise_amp=0.05, noise_f=1.4, cap_a=True, cap_b=True, cap_mat=endg, cap_disc=True, seed=ri * 7 + k, flute=0.03, flute_n=3)
    grass = rmat.grass_blade("HerbeTas", base=(0.05, 0.11, 0.02), tip=(0.28, 0.38, 0.08))
    scatter.field(b, grass, (0, 0), (1.0, 0.9), 50, rng, hmin=0.1, hmax=0.3, avoid=lambda x, y: abs(x) < 0.55 and abs(y) < 0.55)
    return b


def a_tas_de_feuilles(b):
    rng = random.Random(23)
    dead = rmat.dead_leaf()
    leaf2 = rmat.leaf("FeuilleAutomne", top=(0.55, 0.22, 0.04), top2=(0.78, 0.45, 0.07), under=(0.45, 0.25, 0.08), translucency=0.35)
    grass = rmat.grass_blade("HerbeAutomne", base=(0.08, 0.10, 0.02), tip=(0.45, 0.40, 0.12), dry=(0.55, 0.45, 0.2))

    def height(r):
        return max(0.0, 0.26 * (1 - (r / 0.62) ** 2)) ** 1.0
    for i in range(1700):
        a = rng.uniform(0, 6.283)
        r = 0.78 * math.sqrt(rng.random())
        z = height(r) * rng.uniform(0.7, 1.0) + 0.012
        az = rng.uniform(0, 6.283)
        slope = V(math.cos(a), math.sin(a), 0) * 0.35
        d = V(math.cos(az), math.sin(az), 0.0) + slope * rng.uniform(0, 1)
        L = rng.uniform(0.06, 0.12)
        mat = leaf2 if rng.random() < 0.35 else dead
        b.leaf(V(math.cos(a) * r, math.sin(a) * r, z), d.normalized(), UP, L, L * rng.uniform(0.5, 0.75), mat, curl=rng.uniform(0.0, 0.7), twist=rng.uniform(-0.6, 0.6), rand=rng.random(), seg=3, shape="ovate", fold=0.4)
    scatter.field(b, grass, (0, 0), (1.1, 1.1), 40, rng, hmin=0.1, hmax=0.3, avoid=lambda x, y: math.hypot(x, y) < 0.7)
    return b


def mushroom(b, c, s, tilt, cap_m, flesh_m, gills_m, wart_m, rng, seed):
    M = Euler(tilt).to_matrix()
    H = 0.26 * s
    # pied : bulbe à la base, effilé, collerette
    path = [V(c) + M @ V(0, 0, H * i / 8) for i in range(9)]
    b.tube(path, lambda t: s * (0.034 + 0.02 * math.exp(-t * 9) - 0.007 * t), flesh_m, sides=16, noise_amp=0.05, flute=0.04, flute_n=7, cap_a=True, cap_b=True)
    # collerette
    rings = []
    zc = H * 0.62
    for i, (rr, z) in enumerate([(0.034 * s, zc + 0.01 * s), (0.07 * s, zc - 0.002 * s), (0.078 * s, zc - 0.02 * s), (0.03 * s, zc - 0.012 * s)]):
        rings.append([V(c) + M @ V(math.cos(2 * math.pi * j / 40) * rr * (1 + 0.1 * math.sin(7 * 2 * math.pi * j / 40)), math.sin(2 * math.pi * j / 40) * rr * (1 + 0.1 * math.sin(7 * 2 * math.pi * j / 40)), z) for j in range(40)])
    b.loft(rings, flesh_m, uvfn=lambda u, v, co: (u, v), closed=True, smooth=True, cap_a=False, cap_b=False)
    # chapeau
    capR, capH = 0.17 * s, 0.12 * s
    rings = []
    N = 26
    for i in range(N + 1):
        t = i / N
        th = (math.pi / 2) * t
        rr = capR * math.sin(th) ** 0.9 * (1 + 0.04 * math.sin(3 * th))
        z = H + capH * math.cos(th) ** 0.9
        rings.append([V(c) + M @ V(math.cos(2 * math.pi * j / 60) * max(rr, 0.001) * (1 + 0.03 * fbm(V((j * 0.4 + seed, i * 0.2, 0)), 2)), math.sin(2 * math.pi * j / 60) * max(rr, 0.001) * (1 + 0.03 * fbm(V((j * 0.4 + seed, i * 0.2, 0)), 2)), z) for j in range(60)])
    # bord retroussé puis dessous (lamelles)
    rim = rings[-1]
    under = []
    for k in range(7):
        t = k / 6
        rr = capR * (1.0 - 0.9 * t)
        z = H - 0.012 * s * (1 - t) + 0.005 * s * t
        under.append([V(c) + M @ V(math.cos(2 * math.pi * j / 60) * rr, math.sin(2 * math.pi * j / 60) * rr, z) for j in range(60)])
    b.loft(rings, cap_m, uvfn=lambda u, v, co: (u, v), closed=True, smooth=True, cap_a=False, cap_b=False)
    b.loft(under, gills_m, uvfn=lambda u, v, co: (v, u), closed=True, smooth=True, cap_a=False, cap_b=True)
    # verrues blanches
    for k in range(int(26 * s ** 0.6) + 5):
        th = rng.uniform(0.05, 1.25)
        a = rng.uniform(0, 6.283)
        rr = capR * math.sin(th) ** 0.9
        z = H + capH * math.cos(th) ** 0.9
        pos = V(c) + M @ V(math.cos(a) * rr, math.sin(a) * rr, z)
        nrm = (M @ V(math.cos(a) * math.sin(th), math.sin(a) * math.sin(th), math.cos(th))).normalized()
        w = rng.uniform(0.013, 0.03) * s
        from mathutils import Quaternion
        b.rock(pos, (w, w, w * 0.4), wart_m, seed=int(rng.random() * 999), sub=2, planes=0, amp=0.18, ridge=0.0, detail=0.0, sharp=90, rot=nrm.to_track_quat("Z", "Y"))


def a_amanite(b):
    rng = random.Random(31)
    cap = rmat.mushroom_cap("ChapeauAmanite")
    flesh = rmat.mushroom_flesh("PiedAmanite", (0.90, 0.86, 0.76))
    gills = rmat.mushroom_flesh("LamellesAmanite", (0.93, 0.89, 0.78), gills=True)
    wart = rmat.fruit_simple("Verrue", (0.93, 0.9, 0.82), 0.6, 0.15)
    for k, (c, s, tilt) in enumerate([(V(0, 0, 0), 1.0, (0.0, 0.0, 0)), (V(0.34, 0.2, 0), 0.62, (0.2, 0.1, 0)), (V(-0.24, 0.3, 0), 0.42, (-0.22, 0.12, 0)), (V(0.12, -0.28, 0), 0.5, (0.1, -0.2, 0))]):
        mushroom(b, c, s, tilt, cap, flesh, gills, wart, rng, k)
    moss = rmat.moss("MousseAmanite")
    for k in range(18):
        a = rng.uniform(0, 6.283)
        d = math.sqrt(rng.random()) * 0.55
        r = rng.uniform(0.04, 0.09)
        b.rock(V(math.cos(a) * d, math.sin(a) * d, 0.0), (r, r, r * 0.55), moss, seed=k + 5, sub=3, planes=0, amp=0.3, ridge=0.0, detail=0.01, sharp=90)
    grass = rmat.grass_blade("HerbeChamp", base=(0.05, 0.11, 0.02), tip=(0.26, 0.38, 0.07))
    dead = rmat.dead_leaf()
    scatter.field(b, grass, (0.05, 0.05), (0.9, 0.8), 30, rng, hmin=0.08, hmax=0.25, avoid=lambda x, y: math.hypot(x, y) < 0.22)
    scatter.leaf_litter(b, dead, (0.05, 0.05), (0.8, 0.7), 40, rng)
    return b


def a_cloture(b):
    rng = random.Random(41)
    post = rmat.bark("EcorcePoteau", "furrowed", dark=(0.04, 0.03, 0.025), mid=(0.16, 0.12, 0.09), light=(0.34, 0.28, 0.22), around=2.5, along=0.5, moss=0.25, lichen=0.25)
    wood = rmat.plank_wood("BoisCloture", tone=((0.07, 0.05, 0.035), (0.30, 0.22, 0.15), (0.52, 0.42, 0.31)), gray=0.45, cracks=1.0, rough=0.9)
    endg = rmat.end_grain("BoutPoteau", light=(0.70, 0.56, 0.38), dark=(0.46, 0.33, 0.20), bark_ring=(0.25, 0.19, 0.14), rings=10)
    iron = rmat.iron("ClouCloture")
    xs = [-1.5, -0.5, 0.5, 1.5]
    for k, x in enumerate(xs):
        h = 1.1 + rng.uniform(-0.05, 0.05)
        path = [V(x + 0.005 * math.sin(i), 0.0, -0.2 + (h + 0.2) * i / 6) for i in range(7)]
        b.tube(path, [0.068 + 0.004 * math.sin(i + k) for i in range(7)], post, sides=14, noise_amp=0.06, cap_b=True, cap_mat=endg, cap_disc=True, seed=k, flute=0.03, flute_n=3)
    for z in (0.42, 0.85):
        for sy, th in ((0.08, 0.05), (-0.08, 0.05)):
            pts = [V(-1.65 + 3.3 * i / 5, sy, z + rng.uniform(-0.012, 0.012)) for i in range(6)]
            for i in range(5):
                a, c = pts[i], pts[i + 1]
                mid = (a + c) / 2
                L = (c - a).length
                ang = math.atan2(c.z - a.z, c.x - a.x)
                b.plank(mid, (L * 1.01, 0.12, th), wood, rot=Euler((0, -ang, 0)).to_quaternion(), bevel=0.006, seed=int(z * 10) + i + int(sy * 10), warp=0.004, uv_off=(rng.uniform(0, 8), rng.uniform(0, 8)))
            for x in xs:
                b.tube([V(x, sy * 1.35, z + 0.0), V(x, sy * 1.35 + (0.012 if sy > 0 else -0.012), z)], [0.008, 0.008], iron, sides=6, cap_a=True, cap_b=True)
    grass = rmat.grass_blade("HerbeCloture", base=(0.05, 0.11, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (1.9, 0.5), 80, rng, hmin=0.1, hmax=0.4, avoid=lambda x, y: False)
    return b


def a_panneau(b):
    rng = random.Random(43)
    post = rmat.bark("EcorcePanneau", "furrowed", dark=(0.04, 0.03, 0.025), mid=(0.17, 0.13, 0.1), light=(0.36, 0.3, 0.23), around=2.5, along=0.5, moss=0.2)
    wood = rmat.plank_wood("BoisPanneau", tone=((0.08, 0.06, 0.04), (0.34, 0.25, 0.16), (0.56, 0.45, 0.33)), gray=0.5, cracks=0.8)
    endg = rmat.end_grain("BoutPanneau", light=(0.72, 0.58, 0.4), dark=(0.48, 0.34, 0.2), bark_ring=(0.25, 0.19, 0.14), rings=9)
    iron = rmat.iron("ClouPanneau")
    path = [V(0.004 * math.sin(i * 1.3), 0.003 * math.cos(i), -0.25 + 2.3 * i / 8) for i in range(9)]
    b.tube(path, [0.075 - 0.01 * i / 8 + 0.003 * math.sin(i * 2) for i in range(9)], post, sides=14, noise_amp=0.05, cap_b=True, cap_mat=endg, cap_disc=True, flute=0.03, flute_n=3, seed=2)
    for z, d, ang, Lb in [(1.72, 1, 0.06, 1.0), (1.36, -1, -0.05, 0.9), (1.02, 1, 0.02, 0.8)]:
        poly = [(-0.3 * d, -0.11), (Lb * 0.78 * d, -0.11), (Lb * d, 0.0), (Lb * 0.78 * d, 0.11), (-0.3 * d, 0.11)]
        if d < 0:
            poly = list(reversed(poly))
        b.prism(poly, -0.1, -0.06, wood, rot=Euler((0, ang, 0)).to_quaternion(), c=(0, 0, z), uvscale=1.0, uv_off=(rng.uniform(0, 5), rng.uniform(0, 5)))
        for sx in (0.0, 0.25 * d):
            b.tube([V(sx, -0.103, z + sx * ang * -1), V(sx, -0.115, z + sx * ang * -1)], [0.009, 0.009], iron, sides=6, cap_b=True)
    grass = rmat.grass_blade("HerbePanneau", base=(0.05, 0.11, 0.02), tip=(0.28, 0.38, 0.08))
    scatter.field(b, grass, (0, 0), (0.7, 0.7), 40, rng, hmin=0.1, hmax=0.4, avoid=lambda x, y: math.hypot(x, y) < 0.09)
    return b


def a_panier_osier(b):
    rng = random.Random(47)
    wick = rmat.wicker("Osier")
    apple = rmat.apple("Pomme", red=0.8)
    cloth = rmat.fruit_simple("Torchon", (0.78, 0.74, 0.66), 0.9)
    rings = []
    prof = [(0.001, 0.0), (0.2, 0.0), (0.245, 0.04), (0.29, 0.14), (0.315, 0.24), (0.32, 0.31)]
    for r_, z in prof:
        rings.append([V(math.cos(2 * math.pi * j / 72) * r_ * (1 + 0.01 * math.sin(9 * j)), math.sin(2 * math.pi * j / 72) * r_ * (1 + 0.01 * math.sin(9 * j)), z) for j in range(72)])
    b.loft(rings, wick, uvfn=lambda u, v, co: (v, co.z), closed=True, smooth=True, cap_a=True)
    inner = []
    for r_, z in [(0.32, 0.31), (0.3, 0.3), (0.28, 0.2), (0.2, 0.04), (0.001, 0.03)]:
        inner.append([V(math.cos(2 * math.pi * j / 72) * r_, math.sin(2 * math.pi * j / 72) * r_, z) for j in range(72)])
    b.loft(inner, wick, uvfn=lambda u, v, co: (v, co.z), closed=True, smooth=True)
    # bord tressé
    rim = [V(math.cos(2 * math.pi * j / 72) * 0.318, math.sin(2 * math.pi * j / 72) * 0.318, 0.315) for j in range(73)]
    b.tube(rim, [0.016] * 73, wick, sides=8, cap_a=False, cap_b=False, uv_len=6.0)
    # anse
    handle = [V(-0.31 * math.cos(a), 0.0, 0.31 + 0.42 * math.sin(a)) for a in [math.pi * k / 16 for k in range(17)]]
    b.tube(handle, [0.024] * 17, wick, sides=10, cap_a=True, cap_b=True, uv_len=6.0, twist=3.0)
    handle2 = [V(-0.3 * math.cos(a), 0.012, 0.31 + 0.4 * math.sin(a)) for a in [math.pi * k / 16 for k in range(17)]]
    b.tube(handle2, [0.016] * 17, wick, sides=8, cap_a=True, cap_b=True, uv_len=6.0)
    # torchon + pommes
    b.rock(V(0, 0, 0.19), (0.27, 0.27, 0.06), cloth, seed=3, sub=4, planes=0, amp=0.2, ridge=0.0, detail=0.01, sharp=90)
    for k in range(9):
        a = rng.uniform(0, 6.283)
        d = rng.uniform(0.0, 0.17)
        r_ = rng.uniform(0.052, 0.062)
        b.rock(V(math.cos(a) * d, math.sin(a) * d, 0.27 + rng.uniform(0, 0.06)), (r_, r_, r_ * 0.92), apple, seed=700 + k, sub=3, planes=0, amp=0.03, ridge=0.0, detail=0.0, sharp=90, sph_uv=True,
               rot=Euler((rng.uniform(-.3, .3), rng.uniform(-.3, .3), rng.uniform(0, 6))).to_quaternion())
    grass = rmat.grass_blade("HerbePanier", base=(0.05, 0.11, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.7, 0.7), 40, rng, hmin=0.08, hmax=0.3, avoid=lambda x, y: math.hypot(x, y) < 0.33)
    return b


def a_motte_herbe(b):
    rng = random.Random(53)
    soil = rmat.ground("TerreMotte", "dirt")
    grass = rmat.grass_blade("HerbeMotte", base=(0.05, 0.12, 0.02), tip=(0.28, 0.40, 0.08))
    top = rmat.ground("DessusMotte", "grass")
    b.rock(V(0, 0, 0.0), (0.72, 0.62, 0.3), soil, seed=4, sub=6, planes=0, amp=0.15, ridge=0.1, detail=0.02, flat_bottom=-0.05)
    b.rock(V(0, 0, 0.17), (0.7, 0.6, 0.12), top, seed=5, sub=6, planes=0, amp=0.08, ridge=0.0, detail=0.01)
    for k in range(4):
        a = rng.uniform(0, 6.283)
        b.rock(V(math.cos(a) * 0.52, math.sin(a) * 0.46, 0.0), (0.2, 0.18, 0.12), soil, seed=k + 9, sub=4, planes=0, amp=0.25, ridge=0.1, detail=0.02)
    # racines pendantes + herbe dense
    root_m = rmat.bark("RacinesMotte", "furrowed", dark=(0.08, 0.06, 0.04), mid=(0.3, 0.24, 0.16), light=(0.5, 0.42, 0.3), around=1.5, along=1.5)
    for k in range(10):
        a = rng.uniform(0, 6.283)
        p = V(math.cos(a) * 0.55, math.sin(a) * 0.5, 0.06)
        b.tube([p, p + V(math.cos(a) * 0.03, math.sin(a) * 0.03, -0.1), p + V(math.cos(a) * 0.05, math.sin(a) * 0.05, -0.18)], [0.01, 0.007, 0.003], root_m, sides=5, cap_b=True)
    scatter.field(b, grass, (0, 0), (0.62, 0.55), 170, rng, hmin=0.1, hmax=0.35, spread=0.4, zfn=lambda x, y: 0.17 + 0.12 * math.sqrt(max(0.0, 1 - (x / 0.7) ** 2 - (y / 0.6) ** 2)) - 0.03)
    return b


def a_mousse(b):
    rng = random.Random(59)
    moss = rmat.moss("MousseTapis")
    grass = rmat.grass_blade("PousseMousse", base=(0.04, 0.12, 0.02), tip=(0.20, 0.38, 0.06), dry=(0.3, 0.36, 0.1))
    for i in range(70):
        a = rng.uniform(0, 6.283)
        d = math.sqrt(rng.random()) * 0.6
        r = rng.uniform(0.05, 0.14)
        b.rock(V(math.cos(a) * d, math.sin(a) * d * 0.9, 0.0), (r, r, r * 0.55), moss, seed=i, sub=3, planes=0, amp=0.3, freq=2.2, ridge=0.1, detail=0.01, sharp=90)
    scatter.field(b, grass, (0, 0), (0.62, 0.55), 220, rng, hmin=0.03, hmax=0.09, spread=0.2)
    for k in range(14):
        a = rng.uniform(0, 6.283)
        d = math.sqrt(rng.random()) * 0.5
        p = V(math.cos(a) * d, math.sin(a) * d * 0.9, 0.04)
        stalk = [p, p + V(0, 0, 0.05), p + V(0.01, 0, 0.09)]
        b.tube(stalk, [0.0025, 0.002, 0.002], rmat.fruit_simple("PiedSpore", (0.4, 0.3, 0.12), 0.6), sides=4, cap_b=True)
        b.rock(stalk[-1] + V(0.0, 0, 0.012), (0.007, 0.007, 0.012), rmat.fruit_simple("Spore", (0.55, 0.4, 0.15), 0.5), seed=k, sub=2, planes=0, amp=0.05, ridge=0.0, detail=0.0, sharp=90)
    return b
