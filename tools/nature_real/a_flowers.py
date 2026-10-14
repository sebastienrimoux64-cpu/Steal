"""Fleurs et plantes réalistes : marguerites, tournesols, coquelicots, rosier, blé, agave, herbe de la pampa."""
import math
import random

from mathutils import Euler, Quaternion, Vector

import rmat
import scatter
from rgeo import RB, V, fbm

UP = V(0, 0, 1)


def _stem(b, mat, p0, p1, bend, r, rng, n=9, hairy=False):
    d = p1 - p0
    side = V(-d.y, d.x, 0).normalized() if (abs(d.x) + abs(d.y)) > 1e-6 else V(1, 0, 0)
    pts = []
    for i in range(n):
        t = i / (n - 1)
        pts.append(p0.lerp(p1, t) + side * bend * math.sin(math.pi * t * 0.5) ** 2 + V(0, 0, 0))
    b.tube(pts, lambda t: r * (1 - 0.3 * t), mat, sides=6 if r < 0.006 else 10, cap_b=True, noise_amp=0.05, uv_len=2.0)
    return pts


def _head(b, c, d, R, n_pet, pet_m, rng, w=0.22, cup=0.0, rows=1, len_var=0.1, curl=0.2, seg=3, rot0=0.0, shape="lance", thick=0.0):
    """Pétales rayonnants autour de c, dans le plan perpendiculaire à d."""
    d = V(d).normalized()
    ref = UP if abs(d.z) < 0.95 else V(1, 0, 0)
    u = ref.cross(d).normalized()
    v = d.cross(u).normalized()
    for r_ in range(rows):
        for i in range(n_pet):
            a = rot0 + 2 * math.pi * (i + 0.5 * r_) / n_pet + rng.uniform(-0.05, 0.05)
            rd = u * math.cos(a) + v * math.sin(a)
            dir_ = (rd * (1.0 - cup) + d * cup * (1.0 + 0.4 * r_)).normalized()
            L = R * (1 + rng.uniform(-len_var, len_var)) * (1 - 0.08 * r_)
            b.leaf(c + rd * R * 0.12 + d * (0.003 * r_), dir_, d, L, R * w * 2.0, pet_m, curl=curl + rng.uniform(-0.1, 0.1), twist=rng.uniform(-0.25, 0.25), rand=rng.random(), seg=seg, shape=shape, fold=0.1)


def a_fleurs_marguerites(b):
    rng = random.Random(61)
    petal = rmat.petal("PetaleMarguerite", (0.82, 0.80, 0.72), (0.99, 0.99, 0.97), 0.12, 0.5)
    pollen = rmat.seed_disc("CoeurMarguerite", (0.5, 0.32, 0.02), (0.85, 0.62, 0.05), (0.97, 0.80, 0.12), 160)
    stem = rmat.stem_green("TigeMarguerite", (0.16, 0.30, 0.08))
    leaf = rmat.leaf("FeuilleMarguerite", top=(0.08, 0.20, 0.04), top2=(0.14, 0.30, 0.06), under=(0.22, 0.38, 0.14), translucency=0.3)
    for i in range(11):
        a = i * 2.39996 + rng.uniform(-0.2, 0.2)
        rad = 0.05 + 0.2 * math.sqrt((i + 0.5) / 11)
        base = V(math.cos(a) * rad * 0.5, math.sin(a) * rad * 0.5, 0.0)
        h = rng.uniform(0.28, 0.5)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        pts = _stem(b, stem, base, tip, rng.uniform(0.03, 0.07), 0.0035, rng)
        d = (pts[-1] - pts[-2]).normalized() + V(rng.uniform(-0.2, 0.2), -0.4, 0.3)
        c = pts[-1] + d.normalized() * 0.008
        _head(b, c, d, 0.032 + rng.uniform(-0.004, 0.005), 21, petal, rng, w=0.11, curl=0.2, seg=3, shape="lance")
        b.rock(c + d.normalized() * 0.004, (0.0105, 0.0105, 0.006), pollen, seed=i, sub=3, planes=0, amp=0.08, ridge=0.0, detail=0.0, sharp=90, rot=d.normalized().to_track_quat("Z", "Y"))
        for k in range(2):
            ab = a + (k * 2 - 1) * 1.0
            lp = base + V(0, 0, 0.02 + 0.03 * k)
            b.leaf(lp, V(math.cos(ab), math.sin(ab), 0.5), UP, 0.1, 0.022, leaf, curl=0.4, droop=0.2, rand=rng.random(), seg=3, shape="lance", fold=0.3)
    for k in range(10):
        ab = k * 0.9 + rng.uniform(-0.2, 0.2)
        b.leaf(V(0, 0, 0.005), V(math.cos(ab), math.sin(ab), 0.25), UP, rng.uniform(0.09, 0.15), 0.03, leaf, curl=0.5, droop=0.2, rand=rng.random(), seg=3, shape="lance", fold=0.3)
    grass = rmat.grass_blade("HerbeMarguerite", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.45, 0.45), 40, rng, hmin=0.08, hmax=0.3)
    return b


def a_tournesols(b):
    rng = random.Random(63)
    petal = rmat.petal("PetaleTournesol", (0.90, 0.55, 0.04), (0.99, 0.82, 0.08), 0.3, 0.4, edge=(0.95, 0.70, 0.06))
    petal2 = rmat.petal("PetaleTournesolFonce", (0.82, 0.42, 0.03), (0.96, 0.66, 0.05), 0.3, 0.4)
    disc = rmat.seed_disc("DisqueTournesol", (0.09, 0.05, 0.02), (0.27, 0.14, 0.05), (0.48, 0.33, 0.10), 55)
    stem = rmat.stem_green("TigeTournesol", (0.18, 0.28, 0.07))
    leaf = rmat.leaf("FeuilleTournesol", top=(0.08, 0.20, 0.03), top2=(0.14, 0.30, 0.05), under=(0.25, 0.38, 0.12), translucency=0.35)
    sepal = rmat.fruit_simple("Sepale", (0.15, 0.28, 0.07), 0.6)
    for i in range(3):
        a = i * 2.1 + 0.4
        base = V(math.cos(a) * 0.26, math.sin(a) * 0.26, 0.0)
        h = [1.55, 1.3, 1.75][i]
        tip = V(base.x + 0.08, base.y - 0.1, h)
        n = 12
        pts = []
        for j in range(n):
            t = j / (n - 1)
            pts.append(base.lerp(tip, t) + V(0.0, -0.18 * math.sin(t * math.pi * 0.55) ** 2 * 0.0, 0) + V(-0.0, 0.0, 0))
        # nuque courbée : la tête regarde le soleil / la caméra (-Y)
        for j in range(n):
            t = j / (n - 1)
            pts[j] += V(0, -0.2 * max(0, t - 0.75) ** 1.0 * 3, -0.08 * max(0, t - 0.85) * 4)
        b.tube(pts, lambda t: 0.024 * (1 - 0.35 * t), stem, sides=10, cap_b=True, noise_amp=0.04, flute=0.06, flute_n=6, uv_len=2.0)
        head = pts[-1]
        d = (V(0.05, -1.0, 0.25)).normalized()
        R = 0.17 + 0.02 * i
        # disque central bombé + sépales
        b.rock(head + d * 0.01, (R * 0.58, R * 0.58, R * 0.17), disc, seed=i, sub=5, planes=0, amp=0.03, ridge=0.0, detail=0.0, sharp=90, rot=d.to_track_quat("Z", "Y"))
        _head(b, head, d, R, 38, petal, rng, w=0.125, curl=0.35, seg=3, shape="lance", rot0=0.05, len_var=0.15, cup=0.1)
        _head(b, head - d * 0.004, d, R * 0.92, 38, petal2, rng, w=0.125, curl=0.25, seg=3, shape="lance", rot0=0.09, len_var=0.15, cup=0.05)
        for k in range(14):
            aa = 2 * math.pi * k / 14
            ref = UP if abs(d.z) < 0.95 else V(1, 0, 0)
            u = ref.cross(d).normalized()
            v = d.cross(u).normalized()
            rd = u * math.cos(aa) + v * math.sin(aa)
            b.leaf(head - d * 0.012 + rd * R * 0.2, (rd * 0.9 - d * 0.4).normalized(), d, R * 0.33, R * 0.12, sepal, curl=0.5, seg=2, shape="lance", rand=rng.random())
        for kk in range(7):
            z = 0.28 + kk * 0.2 * (h / 1.6)
            j = min(n - 1, int(z / h * (n - 1)))
            ab = a + kk * 2.2
            lp = pts[j]
            b.leaf(lp, V(math.cos(ab), math.sin(ab), 0.15 - 0.03 * kk), UP, 0.3 - 0.01 * kk, 0.26, leaf, curl=0.55, droop=0.2, twist=0.2, rand=rng.random(), seg=6, shape="ovate", fold=0.2)
    grass = rmat.grass_blade("HerbeTournesol", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.8, 0.8), 40, rng, hmin=0.1, hmax=0.4, avoid=lambda x, y: math.hypot(x - 0.0, y) < 0.12)
    return b


def a_coquelicots(b):
    rng = random.Random(65)
    petal = rmat.petal("PetaleCoquelicot", (0.70, 0.02, 0.02), (0.93, 0.07, 0.04), 0.2, 0.5, dark_base=0.95, rough=0.35, sss=0.15)
    stem = rmat.stem_green("TigeCoquelicot", (0.20, 0.30, 0.09))
    leaf = rmat.leaf("FeuilleCoquelicot", top=(0.08, 0.20, 0.05), top2=(0.14, 0.28, 0.07), under=(0.22, 0.34, 0.14), translucency=0.3)
    pod = rmat.fruit_simple("CapsulePavot", (0.28, 0.34, 0.14), 0.45)
    dark = rmat.fruit_simple("EtaminesPavot", (0.02, 0.02, 0.03), 0.5)
    for i in range(8):
        a = i * 2.2 + rng.uniform(-.2, .2)
        rad = 0.07 + 0.2 * math.sqrt((i + 0.5) / 8)
        base = V(math.cos(a) * rad * 0.4, math.sin(a) * rad * 0.4, 0)
        h = rng.uniform(0.45, 0.8)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        pts = _stem(b, stem, base, tip, rng.uniform(0.05, 0.12), 0.0032, rng, n=10)
        end = pts[-1]
        dirn = (pts[-1] - pts[-2]).normalized()
        if i % 4 == 3:    # bouton
            hook = [end, end + V(0.0, 0.0, 0.015), end + V(0.012, 0.0, 0.03)]
            b.rock(end + V(0.01, 0, 0.032), (0.018, 0.018, 0.026), pod, seed=i, sub=3, planes=0, amp=0.05, ridge=0.0, detail=0.0, sharp=90)
        else:
            d = dirn + V(rng.uniform(-0.2, 0.2), -0.35, 0.5)
            R = 0.06 + rng.uniform(-0.008, 0.01)
            _head(b, end, d, R, 4, petal, rng, w=0.5, cup=0.55, curl=0.5, seg=5, shape="round", len_var=0.05, rot0=rng.uniform(0, 3), rows=2)
            b.rock(end + d.normalized() * 0.006, (0.012, 0.012, 0.016), pod, seed=i + 40, sub=3, planes=0, amp=0.05, ridge=0.0, detail=0.0, sharp=90, rot=d.normalized().to_track_quat("Z", "Y"))
            for k in range(14):
                aa = k * 0.9
                ref = UP if abs(d.z) < 0.9 else V(1, 0, 0)
                dn = d.normalized()
                uu = ref.cross(dn).normalized()
                vv = dn.cross(uu).normalized()
                p = end + (uu * math.cos(aa) + vv * math.sin(aa)) * 0.016 + dn * 0.004
                b.tube([p, p + (uu * math.cos(aa) + vv * math.sin(aa)) * 0.006 + dn * 0.012], [0.0008, 0.0014], dark, sides=3, cap_b=True)
        for k in range(2):
            ab = a + (k * 2 - 1) * 1.3
            lp = base + V(0, 0, 0.03 + 0.05 * k)
            b.leaf(lp, V(math.cos(ab), math.sin(ab), 0.4), UP, 0.14, 0.04, leaf, curl=0.4, droop=0.2, rand=rng.random(), seg=4, shape="lance", fold=0.3)
    for k in range(9):
        ab = k * 0.7 + rng.uniform(-.2, .2)
        b.leaf(V(0, 0, 0.005), V(math.cos(ab), math.sin(ab), 0.3), UP, rng.uniform(0.1, 0.18), 0.04, leaf, curl=0.5, droop=0.2, rand=rng.random(), seg=4, shape="lance", fold=0.3)
    grass = rmat.grass_blade("HerbeCoquelicot", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.5, 0.5), 45, rng, hmin=0.1, hmax=0.4)
    return b


def rose(b, c, R, rng, petal_m, tilt=0.0):
    """Rose : spirale de pétales qui s'élargissent (cœur en bouton fermé, couronne ouverte)."""
    n = 26
    for i in range(n):
        t = i / (n - 1)
        a = i * 2.399963
        rad = R * (0.12 + 0.88 * t ** 0.9)
        lift = R * (0.9 * (1 - t) ** 1.3)
        width = R * (0.55 + 0.4 * t)
        d = V(math.cos(a), math.sin(a), 0)
        up_open = 1.0 - 0.75 * (1 - t)
        dirn = (d * (0.25 + 0.9 * t) + V(0, 0, 1.0 - 0.7 * t)).normalized()
        pc = c + d * (rad * 0.55) + V(0, 0, lift * 0.5 - 0.0)
        b.leaf(pc - dirn * 0.0, dirn, -d, R * (0.5 + 0.6 * t), width, petal_m, curl=0.7 + 0.6 * t, droop=0.0, twist=0.0, rand=rng.random(), seg=4, shape="round", fold=-0.5 + 0.35 * t)


def a_rosier(b):
    from a_trees import grow, child_dir
    rng = random.Random(67)
    wood = rmat.bark("TigeRosier", "furrowed", dark=(0.04, 0.03, 0.02), mid=(0.20, 0.10, 0.06), light=(0.34, 0.20, 0.12), around=2.0, along=1.2)
    thorn = rmat.fruit_simple("Epine", (0.45, 0.12, 0.07), 0.5)
    leaf = rmat.leaf("FeuilleRosier", top=(0.06, 0.17, 0.035), top2=(0.12, 0.27, 0.05), under=(0.20, 0.32, 0.10), translucency=0.35, gloss=0.6)
    pet_a = rmat.petal("PetaleRose", (0.55, 0.02, 0.08), (0.88, 0.10, 0.20), 0.18, 0.4, sss=0.2)
    pet_b = rmat.petal("PetaleRosePale", (0.88, 0.45, 0.55), (0.99, 0.80, 0.84), 0.15, 0.45, sss=0.2)
    sp = dict(max_depth=3, kids=[3, 3, 3, 2], kid_from=[0.25, 0.2, 0.2, 0.2], kid_to=[0.9, 0.9, 0.9, 0.9], angle=[(35, 70), (30, 65), (30, 70), (30, 70)], len_ratio=[0.55, 0.55, 0.55, 0.55],
              rad_ratio=[0.6, 0.65, 0.65, 0.65], end_ratio=0.35, wob=0.15, up=0.03, droop=0.12, taper=0.9, seg=0.1, flute=0.0, bumps=0.1, phototropism=0.12)
    twigs = []
    for i in range(10):
        a = i * 2 * math.pi / 10 + rng.uniform(-0.2, 0.2)
        d0 = V(math.cos(a) * 0.5, math.sin(a) * 0.5, 1.0).normalized()
        grow(b, wood, V(math.cos(a) * 0.04, math.sin(a) * 0.04, -0.02), d0, rng.uniform(0.8, 1.1), 0.0125, 0.005, 0, sp, rng, twigs, seed=i)
    n = 0
    tips = []
    for pts, dirs, r in twigs:
        for j in range(1, len(pts)):
            p = pts[j]
            for k in range(3):
                ab = rng.uniform(0, 6.283)
                d0 = V(math.cos(ab), math.sin(ab), 0.4)
                for f in range(5):
                    off = (f - 2) * 0.32
                    d1 = V(math.cos(ab + off), math.sin(ab + off), 0.35 - abs(off) * 0.3)
                    b.leaf(p + d0.normalized() * (0.015 + 0.012 * f), d1.normalized(), UP, 0.058 - 0.005 * abs(f - 2), 0.036, leaf, curl=0.3, droop=0.25, rand=rng.random(), seg=3, shape="ovate", fold=0.4)
                    n += 1
        tips.append(pts[-1])
    tips.sort(key=lambda p: -p.z)
    chosen = []
    for p in tips:
        if all((p - q).length > 0.22 for q in chosen):
            chosen.append(p)
        if len(chosen) >= 10:
            break
    for k, p in enumerate(chosen):
        rose(b, p + V(0, 0, 0.02), 0.065 + 0.012 * rng.random(), rng, pet_a if k % 3 else pet_b)
    # épines
    for pts, dirs, r in twigs[:40]:
        for j in range(1, len(pts), 2):
            a = rng.uniform(0, 6.283)
            dd = V(math.cos(a), math.sin(a), -0.2).normalized()
            b.tube([pts[j], pts[j] + dd * 0.013], [0.0032, 0.0005], thorn, sides=4, cap_b=True)
    grass = rmat.grass_blade("HerbeRosier", base=(0.05, 0.12, 0.02), tip=(0.26, 0.38, 0.07))
    scatter.field(b, grass, (0, 0), (0.7, 0.7), 30, rng, hmin=0.1, hmax=0.35)
    print("rosier feuilles", n)
    return b


def a_ble(b):
    rng = random.Random(71)
    stem = rmat.wheat("PailleBle", (0.62, 0.52, 0.2))
    ear = rmat.wheat("EpiBle", (0.78, 0.58, 0.2))
    leaf = rmat.leaf("FeuilleBle", top=(0.30, 0.38, 0.08), top2=(0.46, 0.46, 0.12), under=(0.42, 0.44, 0.16), translucency=0.35)
    for i in range(34):
        a = i * 2.39996
        rad = 0.05 + 0.3 * math.sqrt((i + 0.5) / 34)
        base = V(math.cos(a) * rad * 0.8, math.sin(a) * rad * 0.8, 0)
        h = rng.uniform(0.75, 1.0)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        pts = []
        for j in range(10):
            t = j / 9
            pts.append(base.lerp(tip, t) + V(math.cos(a + 1.2), math.sin(a + 1.2), 0) * 0.07 * t ** 2.5 * rng.uniform(0.8, 1.2))
        b.tube(pts, lambda t: 0.0032 * (1 - 0.3 * t), stem, sides=5, cap_b=True, uv_len=1.0)
        end = pts[-1]
        dr = (pts[-1] - pts[-2]).normalized()
        rot = dr.to_track_quat("Z", "Y")
        # épillets : petits ellipsoïdes en spirale sur l'épi
        for k in range(18):
            tt = k / 17
            ang = k * 2.399963
            lat = rot.to_matrix() @ V(math.cos(ang) * 0.0075, math.sin(ang) * 0.0075, 0)
            pos = end + dr * (0.004 + 0.085 * tt) + lat
            b.rock(pos, (0.0045, 0.0045, 0.012), ear, seed=k + i * 18, sub=2, planes=0, amp=0.05, ridge=0.0, detail=0.0, sharp=90, rot=(dr + lat.normalized() * 0.5).normalized().to_track_quat("Z", "Y"))
            for s in (-1, 1):
                aw = rot.to_matrix() @ V(math.cos(ang + s) * 0.004, math.sin(ang + s) * 0.004, 0)
                b.tube([pos + dr * 0.006, pos + dr * 0.04 + aw * 2.5, pos + dr * 0.075 + aw * 3.5], [0.0005, 0.0004, 0.00025], ear, sides=3, cap_b=True)
        if i % 2 == 0:
            lp = pts[3]
            ab = a + 2
            b.leaf(lp, V(math.cos(ab), math.sin(ab), 0.6), UP, 0.34, 0.016, leaf, curl=0.7, droop=0.3, rand=rng.random(), seg=5, shape="grass", fold=0.6)
    grass = rmat.grass_blade("HerbeBle", base=(0.15, 0.20, 0.03), tip=(0.45, 0.42, 0.10), dry=(0.55, 0.45, 0.2))
    scatter.field(b, grass, (0, 0), (0.45, 0.45), 30, rng, hmin=0.1, hmax=0.4)
    return b


def a_agave(b):
    rng = random.Random(73)
    mat = rmat.agave_leaf()
    tooth = rmat.fruit_simple("DentAgave", (0.35, 0.18, 0.08), 0.5)
    spine = rmat.fruit_simple("EpineAgave", (0.10, 0.05, 0.03), 0.4)
    n = 24
    for i in range(n):
        ring = i // 8
        a = i * 2.399963
        out = 0.12 + 0.34 * (ring + 0.5) / 3 * 1.1
        L = 0.85 - 0.12 * ring
        raise_ = 1.15 - 0.4 * ring
        pts = []
        base = V(math.cos(a) * 0.03, math.sin(a) * 0.03, 0.05)
        for j in range(10):
            t = j / 9
            pts.append(base + V(math.cos(a), math.sin(a), 0) * (out * 2.2 * t) + V(0, 0, raise_ * 0.5 * L * math.sin(math.pi * 0.62 * t) - 0.1 * L * t ** 2.2))
        b.tube(pts, lambda t: (max(0.011, 0.085 * math.sin(math.pi * (0.16 + 0.84 * t)) ** 0.6 * (1 - 0.3 * t)), 0.018 * (1 - 0.5 * t) + 0.004), mat, sides=10, cap_a=True, uv_len=1.0 / L, twist=0.0, up=V(0, 0, 1))
        for j in range(2, 10):
            p = pts[j]
            side = V(-math.sin(a), math.cos(a), 0)
            w = max(0.011, 0.085 * math.sin(math.pi * (0.16 + 0.84 * j / 9)) ** 0.6 * (1 - 0.3 * j / 9))
            for s in (-1, 1):
                b.tube([p + side * s * w * 0.95, p + side * s * (w * 0.95 + 0.012) + V(0, 0, -0.004)], [0.004, 0.0008], tooth, sides=4, cap_b=True)
        d = (pts[-1] - pts[-2]).normalized()
        b.tube([pts[-1], pts[-1] + d * 0.05], [0.006, 0.0008], spine, sides=5, cap_b=True)
    return b


def a_herbe_pampa(b):
    rng = random.Random(79)
    blade = rmat.grass_blade("LamePampa", base=(0.10, 0.16, 0.04), tip=(0.50, 0.55, 0.20), dry=(0.62, 0.55, 0.28), translucency=0.5)
    plume_m = rmat.plume()
    stem = rmat.wheat("HampePampa", (0.60, 0.55, 0.30))
    for i in range(48):
        a = i * 2.399963
        rad = rng.uniform(0.0, 0.12)
        base = V(math.cos(a) * rad, math.sin(a) * rad, 0)
        L = rng.uniform(1.0, 1.75)
        reach = rng.uniform(0.5, 1.1)
        out = V(math.cos(a), math.sin(a), 0)
        pts = []
        for j in range(9):
            t = j / 8
            pts.append(base + out * (reach * t ** 2.0) + V(0, 0, L * (t - 0.4 * t * t)))
        d = (pts[-1] - pts[-2]).normalized()
        # lame = bande suivant la courbe (via leaf par segments)
        rings = []
        for j, p in enumerate(pts):
            t = j / 8
            tdir = ((pts[min(8, j + 1)] - pts[max(0, j - 1)])).normalized()
            side = tdir.cross(UP).normalized()
            wd = 0.0125 * (1 - t) ** 0.75 * (0.6 + 0.4 * min(1.0, t * 6))
            fold = 0.004 * (1 - t)
            rings.append([p + side * wd + UP * fold, p, p - side * wd + UP * fold])
        rr = rng.random()
        b.loft(rings, blade, uvfn=lambda u, v, co: (u, v / 1.0), closed=False, smooth=True, rand=rr)
    for i in range(7):
        a = i * 1.9 + 0.4
        rad = 0.08 + 0.07 * (i % 3)
        base = V(math.cos(a) * 0.03, math.sin(a) * 0.03, 0)
        Ht = rng.uniform(1.75, 2.2)
        tip = V(math.cos(a) * rad + 0.1, math.sin(a) * rad, Ht)
        pts = []
        for j in range(10):
            t = j / 9
            pts.append(base.lerp(tip, t) + V(math.cos(a), math.sin(a), 0) * 0.09 * math.sin(math.pi * t * 0.5) ** 2)
        b.tube(pts, lambda t: 0.0045 * (1 - 0.3 * t), stem, sides=5, cap_b=True)
        end = pts[-1]
        dr = (pts[-1] - pts[-2]).normalized()
        # plumeau : centaines de fils fins arqués
        side0 = dr.cross(UP).normalized() if abs(dr.z) < 0.99 else V(1, 0, 0)
        for k in range(130):
            tt = rng.random() ** 0.8
            ang = rng.uniform(0, 6.283)
            lat = (side0 * math.cos(ang) + side0.cross(dr) * math.sin(ang))
            radius = 0.045 * math.sin(math.pi * tt) ** 0.7 + 0.004
            p0 = end - dr * (0.38 * tt) + dr * 0.04
            p1 = p0 + lat * radius * 0.7 + dr * 0.06
            p2 = p0 + lat * radius * 1.0 + dr * 0.14 + V(0, 0, -0.03)
            b.tube([p0, p1, p2], [0.0011, 0.0009, 0.0004], plume_m, sides=3, cap_b=True)
    grass = rmat.grass_blade("HerbePampa2", base=(0.08, 0.14, 0.03), tip=(0.30, 0.40, 0.10), dry=(0.55, 0.5, 0.25))
    scatter.field(b, grass, (0, 0), (0.9, 0.9), 15, rng, hmin=0.15, hmax=0.5, avoid=lambda x, y: math.hypot(x, y) < 0.3)
    return b
