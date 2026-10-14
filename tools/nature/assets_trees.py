"""Nouveaux arbres du NaturePack : pommier, olivier, baobab, acacia, sapin enneigé."""
import math

from mathutils import Vector

from natlib import pal, grad, tex

def V(*a):
    return Vector(a) if len(a) > 1 else Vector(a[0])


def trunk_path(h, lean=(0, 0), wob=0.05, n=9, seed=0, z0=0.0):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        pts.append(V(lean[0] * t * t + wob * math.sin(t * 4 + seed), lean[1] * t * t + wob * math.cos(t * 3.3 + seed), z0 + h * t))
    return pts


def flare(r0, k=0.55):
    return lambda t: r0 * (1 - k * t) * (1 + 0.55 * math.exp(-t * 12))


def a_pommier(b):
    r = b.rnd
    H = 1.9
    lean = (0.18, 0.06)
    path = trunk_path(H, lean, 0.05, 9, 1.0)
    top = path[-1]
    b.chain("tronc", V(0, 0, 0.25), top, 3, names=["tronc1", "tronc2", "cime"], amp=0.35)
    branches = []
    for i in range(4):
        a = i * math.pi / 2 + 0.5 + r.uniform(-0.25, 0.25)
        zb = 1.25 + 0.12 * i
        p0 = path[int(zb / H * 8)]
        tip = V(p0.x + math.cos(a) * 1.15, p0.y + math.sin(a) * 1.15, 2.55 + r.uniform(-.1, .2))
        pts = [p0.lerp(tip, t) + V(0, 0, 0.3 * math.sin(t * 2.2)) for t in [k / 6 for k in range(7)]]
        nm = b.chain(f"branche{i + 1}", p0, tip, 1, parent="tronc2", amp=0.5)
        branches.append((nm, pts, tip))
    bark = tex("bark", 2, 0.8)
    b.tube(path, flare(0.26), bark, sides=10, ex=1.0, part="tronc")
    for nm, pts, tip in branches:
        b.tube(pts, lambda t: 0.1 * (1 - 0.6 * t), bark, sides=7, part=nm)
    leaf = grad("A", "fresh", 1.2, 5.0)
    blobs = []
    cands = ["tronc"] + [n for n, _, _ in branches]
    centers = [(top.x, top.y, 3.25, 1.05)]
    for i in range(7):
        a = i * 2 * math.pi / 7 + r.uniform(-.2, .2)
        centers.append((top.x + math.cos(a) * 1.25, top.y + math.sin(a) * 1.25, 2.55 + r.uniform(0, 0.75), r.uniform(0.7, 0.95)))
    centers.append((top.x + 0.3, top.y - 0.2, 3.75, 0.8))
    for k, (x, y, z, R) in enumerate(centers):
        part = b.nearest_part((x, y, z), cands)
        b.blob((x, y, z), R, leaf, amp=0.2, freq=1.5, squash=(1, 1, 0.82), seed=k + 1, part=part)
        blobs.append((V(x, y, z), R, part))
    apples = pal("red")
    for k in range(24):
        c, R, part = blobs[r.randrange(len(blobs))]
        a = r.uniform(0, 6.28)
        el = r.uniform(-0.75, 0.15)
        d = V(math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))
        pos = c + V(d.x * R, d.y * R, d.z * R * 0.82) * 1.0
        b.blob(pos, 0.135, apples, amp=0.05, sub=2, seed=k, part=part, squash=(1, 1, 0.92))


def a_olivier(b):
    r = b.rnd
    H = 1.1
    path = trunk_path(H, (0.15, -0.05), 0.1, 10, 2.0)
    top = path[-1]
    b.chain("tronc", V(0, 0, 0.25), top, 3, names=["tronc1", "tronc2", "cime"], amp=0.35)
    bark = tex("bark", 2, 0.7)
    b.tube(path, lambda t: 0.3 * (1 - 0.5 * t) * (1 + 0.5 * math.exp(-t * 10)), bark, sides=10, ex=1.45, twist=2 * math.pi * 1.3, part="tronc")
    limbs = []
    for i in range(3):
        a = i * 2 * math.pi / 3 + 0.4
        tip = V(top.x + math.cos(a) * 1.35, top.y + math.sin(a) * 1.35, 2.5 + r.uniform(0, 0.35))
        pts = []
        for k in range(8):
            t = k / 7
            p = top.lerp(tip, t)
            pts.append(p + V(-math.sin(a) * 0.18 * math.sin(t * 6), math.cos(a) * 0.18 * math.sin(t * 6), 0.35 * math.sin(t * 1.6)))
        nm = b.chain(f"branche{i + 1}", top, tip, 1, parent="tronc2", amp=0.5)
        b.tube(pts, lambda t: 0.16 * (1 - 0.65 * t), bark, sides=7, ex=1.3, twist=4, part=nm)
        limbs.append((nm, tip))
    leaf = grad("A", "olive", 1.6, 3.6)
    cands = ["tronc"] + [n for n, _ in limbs]
    cs = [(top.x, top.y, 2.9, 1.0)] + [(t.x * 0.9 + top.x * 0.1, t.y * 0.9 + top.y * 0.1, t.z + 0.1, 0.95) for _, t in limbs]
    for k in range(5):
        a = k * 1.26 + 0.2
        cs.append((top.x + math.cos(a) * 1.0, top.y + math.sin(a) * 1.0, 2.35 + r.uniform(0, 0.5), 0.7))
    cs.append((top.x, top.y, 3.35, 0.7))
    blobs = []
    for k, (x, y, z, R) in enumerate(cs):
        part = b.nearest_part((x, y, z), cands)
        b.blob((x, y, z), R, leaf, amp=0.25, freq=1.8, squash=(1.18, 1.18, 0.6), seed=k + 3, part=part)
        blobs.append((V(x, y, z), R, part))
    olive = pal("purple")
    green_olive = pal("moss")
    for k in range(18):
        c, R, part = blobs[r.randrange(len(blobs))]
        a = r.uniform(0, 6.28)
        el = r.uniform(-0.8, 0.0)
        d = V(math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))
        b.blob(c + V(d.x * R * 1.15, d.y * R * 1.15, d.z * R * 0.65), 0.08, olive if k % 3 else green_olive, amp=0.0, sub=2, seed=k, part=part, squash=(0.8, 0.8, 1.15))


def a_baobab(b):
    r = b.rnd
    zs = [0, 0.25, 1.0, 2.0, 3.0, 3.7, 4.15]
    rs = [1.55, 1.25, 1.4, 1.45, 1.22, 0.95, 0.72]
    prof = [(0.001, -0.02)] + [(rr, z) for rr, z in zip(rs, zs)] + [(0.45, 4.3), (0.001, 4.36)]
    b.chain("tronc", V(0, 0, 0.3), V(0, 0, 4.3), 3, names=["tronc1", "tronc2", "cime"], amp=0.25)
    stone = tex("stone", 2, 2.2)
    b.lathe(prof, stone, sides=22, mod=lambda a, t: 1 + 0.07 * math.sin(5 * a + 3 * t) + 0.04 * math.sin(11 * a + 9 * t), part="tronc", spline=5)
    leaf = grad("B", "green", 4.0, 6.4)
    cands = []
    for i in range(6):
        a = i * math.pi / 3 + 0.3
        z0 = 4.0
        tip = V(math.cos(a) * 1.55, math.sin(a) * 1.55, 5.05 + r.uniform(0, 0.5))
        p0 = V(math.cos(a) * 0.55, math.sin(a) * 0.55, z0)
        nm = b.chain(f"branche{i + 1}", p0, tip, 1, parent="cime", amp=0.5)
        pts = [p0.lerp(tip, t / 5) + V(0, 0, 0.25 * math.sin(t / 5 * 2.2)) for t in range(6)]
        b.tube(pts, lambda t: 0.26 * (1 - 0.6 * t), stone, sides=7, part=nm)
        b.blob(tip + V(0, 0, 0.18), 0.85, leaf, amp=0.22, squash=(1.1, 1.1, 0.62), seed=i + 5, part=nm)
        for j in range(2):
            o = V(math.cos(a + 0.9 - j * 1.8) * 0.5, math.sin(a + 0.9 - j * 1.8) * 0.5, 0.1 + 0.12 * j)
            b.blob(tip + o, 0.55, leaf, amp=0.2, squash=(1, 1, 0.65), seed=i * 3 + j, part=nm)
    b.blob(V(0, 0, 5.45), 0.8, leaf, amp=0.2, squash=(1.1, 1.1, 0.6), seed=9, part="tronc")


def a_acacia(b):
    r = b.rnd
    H = 2.6
    path = trunk_path(H, (0.55, 0.1), 0.05, 9, 0.5)
    top = path[-1]
    b.chain("tronc", V(0, 0, 0.25), top, 3, names=["tronc1", "tronc2", "cime"], amp=0.35)
    bark = tex("bark", 2, 0.9)
    b.tube(path, flare(0.2, 0.45), bark, sides=9, part="tronc")
    leaf = grad("A", "lime", 3.4, 5.0)
    cands = ["tronc"]
    forks = []
    for i, a in enumerate((0.3, 2.4, 4.4)):
        tip = V(top.x + math.cos(a) * 1.9, top.y + math.sin(a) * 1.9, 4.05 + r.uniform(-0.1, 0.25))
        nm = b.chain(f"branche{i + 1}", top, tip, 1, parent="tronc2", amp=0.5)
        pts = [top.lerp(tip, t / 6) + V(0, 0, 0.5 * math.sin(t / 6 * 1.7)) for t in range(7)]
        b.tube(pts, lambda t: 0.12 * (1 - 0.6 * t), bark, sides=6, part=nm)
        forks.append((nm, tip))
        cands.append(nm)
    for k, (nm, tip) in enumerate(forks):
        b.blob(tip + V(0, 0, 0.25), 1.35, leaf, amp=0.14, squash=(1, 1, 0.26), seed=k, part=nm)
        b.blob(tip + V(0.5, 0.3, 0.38), 1.0, leaf, amp=0.14, squash=(1, 1, 0.24), seed=k + 4, part=nm)
    b.blob(V(top.x, top.y, 4.15), 1.7, leaf, amp=0.12, squash=(1, 1, 0.2), seed=11, part="tronc")
    b.blob(V(top.x - 0.5, top.y + 0.4, 4.45), 1.2, leaf, amp=0.12, squash=(1, 1, 0.22), seed=12, part="tronc")


def a_sapin_enneige(b):
    r = b.rnd
    H = 8.6
    b.chain("tronc", V(0, 0, 0.25), V(0.04, 0.02, H), 3, names=["tronc1", "tronc2", "cime"], amp=0.3)
    bark = tex("bark", 2, 1.0)
    b.tube([V(0, 0, 0), V(0.02, 0.01, 2.0), V(0.04, 0.02, 4.0)], lambda t: 0.22 * (1 - 0.6 * t) * (1 + 0.6 * math.exp(-t * 9)), bark, sides=9, part="tronc")
    dark = grad("A", "pine", 1.2, 8.8)
    snow = pal("white")
    snow2 = pal("cream")
    tiers = 7
    for i in range(tiers):
        f = i / (tiers - 1)
        z = 1.3 + i * 1.02
        R = 2.1 * (1 - f) ** 0.85 + 0.3
        h = 1.55 - 0.1 * i
        ph = i * 1.3
        prof = [(0.001, z + h), (R * 0.32, z + h * 0.62), (R * 0.72, z + h * 0.22), (R, z - 0.05), (R * 0.82, z - 0.2), (0.12, z - 0.12)]
        scallop = lambda a, t, ph=ph: 1 + 0.07 * math.sin(8 * a + ph) * t + 0.04 * math.sin(13 * a + ph)
        b.lathe(prof, dark, sides=26, mod=scallop, part="tronc")
        sprof = [(0.001, z + h + 0.07), (R * 0.33, z + h * 0.62 + 0.07), (R * 0.68, z + h * 0.24 + 0.05), (R * 0.9, z + 0.02), (R * 0.78, z - 0.06), (R * 0.4, z + h * 0.2)]
        smod = lambda a, t, ph=ph: 1 + 0.12 * math.sin(7 * a + ph * 1.7) * t + 0.06 * math.sin(15 * a)
        b.lathe(sprof, snow if i % 2 == 0 else snow2, sides=26, mod=smod, part="tronc", smooth=True)
    b.lathe([(0.001, 8.75), (0.07, 8.45), (0.2, 8.05), (0.05, 8.0)], dark, sides=10, part="tronc")
