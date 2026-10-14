"""Roches réalistes : arche de grès, pierres de gué, rocher à cristaux (base)."""
import math

from mathutils import Vector, Euler

import rmat
from rgeo import RB, fbm, ridged, smin, V


def sandstone(name="Gres"):
    return rmat.rock(name, dark=(0.13, 0.055, 0.03), mid=(0.47, 0.25, 0.13), light=(0.72, 0.48, 0.30), strata=1.5, strata_freq=3.4,
                     crack=0.45, lichen=0.06, scale=0.55, grain=1.2)


def a_arche(b, N=300, M=110, Rx=2.35, Rz=2.75, mat=None):
    mat = mat or sandstone()
    seed = 3.0

    def centre(s):
        if s < 0:
            return V(-Rx, 0.18 * math.sin(s * 2), Rz * s), V(0, 0, 1)
        if s > math.pi:
            return V(Rx, 0.18 * math.sin(s * 2), -Rz * (s - math.pi)), V(0, 0, -1)
        c = V(-Rx * math.cos(s), 0.22 * math.sin(s * 1.7 + 0.6), Rz * math.sin(s))
        t = V(Rx * math.sin(s), 0.0, Rz * math.cos(s)).normalized()
        return c, t

    rings = []
    s0, s1 = -0.85, math.pi + 0.85
    for i in range(N + 1):
        s = s0 + (s1 - s0) * i / N
        c, T = centre(s)
        Nr = V(-T.z, 0, T.x)
        Y = V(0, 1, 0)
        sc = min(max(s, 0.0), math.pi)
        top = math.sin(sc)
        # sections plus épaisses aux pieds, amincies au sommet ; élargissement au sol
        flare = 1.0 + 0.9 * max(0.0, min(1.0, (0.7 - c.z) / 1.6))
        a = (1.15 - 0.40 * top ** 1.3) * flare * (1 + 0.16 * fbm(V(s * 0.9, 0.3, 1.1), 3, seed=seed))
        bt = (0.95 - 0.40 * top ** 1.5) * (1 + 0.7 * (flare - 1.0)) * (1 + 0.14 * fbm(V(s * 0.9, 1.3, 4.1), 3, seed=seed + 2))
        ring = []
        for j in range(M):
            ph = 2 * math.pi * j / M
            cs, sn = math.cos(ph), math.sin(ph)
            ex = 2.0 / 2.7
            cx = math.copysign(abs(cs) ** ex, cs)
            sy = math.copysign(abs(sn) ** ex, sn)
            dirn = (Nr * cx * bt + Y * sy * a)
            p = c + dirn
            n = dirn.normalized()
            q = p * 1.0
            # relief : grandes masses, blocs, crêtes, grain
            d = 0.34 * fbm(q * 0.75, 4, seed=seed) + 0.11 * fbm(q * 2.6, 4, seed=seed + 1) + 0.07 * ridged(q * 6.0, 3, seed=seed + 2) * 0.6
            # strates : plateformes horizontales érodées
            ter = math.sin(q.z * 7.4 + 2.3 * fbm(q * 0.6, 2, seed=seed + 3))
            d += 0.045 * (ter - 0.6 * ter ** 3)
            # surplombs aux flancs
            d -= 0.10 * max(0.0, fbm(q * 1.4, 3, seed=seed + 5)) * (1 - abs(n.z))
            # blocs étagés (diaclases) et alvéoles d'érosion (tafoni)
            tt = 3.2 * fbm(q * 1.15, 3, seed=seed + 6) + 8.0
            fr = tt - math.floor(tt)
            d += 0.075 * (math.floor(tt) + fr * fr * (3 - 2 * fr) ** 1.0) * 0.5
            pit = max(0.0, fbm(q * 3.4, 3, seed=seed + 7) - 0.12) * 3.0
            d -= 0.09 * min(pit, 1.0) ** 1.5
            ring.append(p + n * d)
        rings.append(ring)
    faces = b.loft(rings, mat, uvfn=lambda u, v, co: (0.0, 0.0), closed=True, smooth=True, cap_a=True, cap_b=True)
    # blocs éboulés aux pieds et pierrailles
    r = b.rnd
    for k, (x, y, rr) in enumerate([(-Rx - 0.35, 0.25, (1.1, 0.95, 0.75)), (Rx + 0.45, -0.1, (1.25, 1.0, 0.8)), (-Rx + 0.5, -1.15, (0.7, 0.6, 0.45)), (Rx - 0.55, 1.2, (0.65, 0.6, 0.42)),
                                    (-Rx - 1.15, -0.6, (0.55, 0.5, 0.35)), (Rx + 1.3, 0.9, (0.5, 0.45, 0.32))]):
        b.rock(V(x, y, rr[2] * 0.35), rr, mat, seed=10 + k, sub=5, planes=8, amp=0.14, strata=0.5)
    for k in range(34):
        a = r.uniform(0, 6.28)
        d = r.uniform(1.4, 4.6)
        s = r.uniform(0.07, 0.34) * (1.5 - d / 6)
        b.rock(V(math.cos(a) * d * 1.2, math.sin(a) * d * 0.9, s * 0.25), (s * 1.2, s, s * 0.7), mat, seed=40 + k, sub=3 if s < 0.15 else 4, planes=6, amp=0.2, detail=0.03)
    import scatter
    dry = rmat.grass_blade("HerbeSeche", base=(0.20, 0.16, 0.06), tip=(0.62, 0.52, 0.24), dry=(0.7, 0.6, 0.3))
    scatter.field(b, dry, (0, 0), (5.2, 3.6), 70, r, hmin=0.15, hmax=0.5, avoid=None)
    return b


def a_pierres_de_gue(b, mat=None):
    """Pierres plates de gué : dalles de calcaire/grès irrégulières, arêtes chanfrénées, mousse et lichen, joints de terre."""
    mat = mat or rmat.rock("PierreGue", dark=(0.12, 0.115, 0.10), mid=(0.30, 0.285, 0.255), light=(0.50, 0.48, 0.43), strata=0.5, strata_freq=9.0, crack=0.55,
                           moss=0.3, lichen=0.12, scale=1.0, grain=1.2, wet=0.15)
    soil = rmat.ground("TerreGue", "dirt")
    r = b.rnd
    spots = [(-2.1, 0.1, 0.55), (-1.05, 0.38, 0.5), (0.0, -0.12, 0.62), (1.1, 0.30, 0.48), (2.15, 0.0, 0.54), (0.5, 1.0, 0.3), (-1.5, -0.95, 0.33)]
    for k, (x, y, R) in enumerate(spots):
        b.rock(V(x, y, 0.0), (R * 1.2, R * (0.95 + 0.1 * r.random()), 0.28 + 0.06 * r.random()), mat, seed=70 + k, sub=6, planes=10, depth=(0.7, 0.92), amp=0.12, kcut=0.05,
               freq=1.7, ridge=0.12, rot=Euler((0, 0, r.uniform(0, 3.1))).to_quaternion(), strata=0.0, detail=0.03,
               extra_planes=[((0.05, 0.03, 1.0), 0.74)])
        # petite terre autour
        b.rock(V(x, y, -0.03), (R * 1.55, R * 1.5, 0.07), soil, seed=90 + k, sub=4, planes=0, amp=0.18, ridge=0.0, detail=0.02)
    for k in range(18):
        x, y = r.uniform(-2.7, 2.7), r.uniform(-1.3, 1.5)
        s = r.uniform(0.04, 0.12)
        b.rock(V(x, y, 0.0), (s * 1.2, s, s * 0.6), mat, seed=120 + k, sub=3, planes=5, amp=0.2)
    import scatter
    grass = rmat.grass_blade("HerbeGue", base=(0.05, 0.12, 0.02), tip=(0.28, 0.40, 0.08))
    near = lambda x, y: any(math.hypot(x - sx, y - sy) < R * 1.1 for sx, sy, R in spots)
    scatter.field(b, grass, (0.0, 0.25), (3.2, 1.9), 190, r, hmin=0.12, hmax=0.42, avoid=near)
    return b


def a_cristaux(b):
    """Géode d'améthyste : socle rocheux sombre avec druse, amas de grands cristaux hexagonaux translucides (réfraction + absorption violette)."""
    import random
    base = rmat.rock("RocheGeode", dark=(0.025, 0.02, 0.02), mid=(0.10, 0.085, 0.08), light=(0.24, 0.21, 0.19), crack=0.5, scale=1.0, strata=0.3, strata_freq=7.0, grain=1.2)
    ame = rmat.amethyst("Amethyste")
    ame2 = rmat.amethyst("AmethysteClair", deep=(0.82, 0.45, 0.95), light=(0.95, 0.75, 1.0))
    r = random.Random(11)
    b.rock(V(0, 0, 0.0), (1.05, 0.9, 0.55), base, seed=5, sub=6, planes=8, depth=(0.62, 0.9), amp=0.2, kcut=0.1, freq=1.4, ridge=0.22, detail=0.05, flat_bottom=-0.12)
    b.rock(V(0.75, 0.35, 0.0), (0.5, 0.42, 0.3), base, seed=6, sub=5, planes=7, amp=0.2, detail=0.04)
    b.rock(V(-0.7, -0.4, 0.0), (0.45, 0.4, 0.28), base, seed=7, sub=5, planes=7, amp=0.2, detail=0.04)
    spots = []
    for k in range(34):
        a = r.uniform(0, 6.283)
        e = r.uniform(0.35, 1.25) if k < 22 else r.uniform(0.2, 0.9)
        d = V((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        rad = r.uniform(0.9, 1.0) if k < 22 else r.uniform(1.0, 1.1)
        spread = 0.55 if k < 22 else 0.9
        pos = V((d.x * 1.0 * 0.78, d.y * 0.7 * 0.78, d.z * 0.5 * 0.9 - 0.02))
        axis = V((d.x * 0.7 + r.gauss(0, spread * 0.35), d.y * 0.7 + r.gauss(0, spread * 0.35), d.z * 1.0 + 0.25))
        big = r.random() ** 1.6
        length = 0.22 + 0.68 * big if k < 22 else r.uniform(0.12, 0.3)
        radius = length * r.uniform(0.2, 0.3)
        spots.append((pos, axis, length, radius, k))
    for pos, axis, length, radius, k in spots:
        b.crystal(pos - axis.normalized() * 0.08, axis, length + 0.08, radius, ame if k % 3 else ame2, taper=0.9, tip=r.uniform(0.2, 0.32), seed=k, elong=r.uniform(0.9, 1.1), twist=r.uniform(-0.08, 0.08))
    # druse : petits cristaux serrés sur le socle
    for k in range(260):
        a = r.uniform(0, 6.283)
        e = r.uniform(0.05, 1.3)
        d = V((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        pos = V((d.x * 1.0 * 0.86, d.y * 0.88 * 0.86, d.z * 0.55 * 0.9 - 0.02))
        s = r.uniform(0.02, 0.07)
        axis = d + V(r.gauss(0, 0.3), r.gauss(0, 0.3), r.gauss(0, 0.3))
        b.crystal(pos, axis, s * 3, s, ame if k % 4 else ame2, taper=0.85, tip=0.3, seed=100 + k)
    return b
