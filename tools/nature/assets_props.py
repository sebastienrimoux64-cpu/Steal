"""Nouveaux accessoires du NaturePack : citrouilles, pomme de pin, branche, bûches, feuilles, amanite, gué, feu de camp, clôture, panneau, pont, cristaux, arche."""
import math

from mathutils import Quaternion, Euler, Vector

from common import V, arc, blade, leaf_profile
from natlib import pal, grad, tex


def pumpkin(b, c, R, H, seed=0, part=None, tilt=0.0, stem=True):
    r = b.rnd
    n = 14
    prof = []
    for i in range(n + 1):
        t = i / n
        ang = math.pi * t
        rr = R * math.sin(ang) ** 0.62
        z = H * (0.5 - 0.5 * math.cos(ang))
        if t > 0.86:                       # creux autour de la queue
            z -= H * 0.1 * math.sin(math.pi * (t - 0.86) / 0.14)
        prof.append((max(rr, 0.001), z))
    paint = grad("A", "autumn", c[2] - 0.5 * H, c[2] + 1.5 * H)
    ribs = lambda a, t: 1 + 0.085 * math.cos(10 * a + seed) * math.sin(math.pi * t) ** 0.6
    q = Euler((tilt, 0, 0)).to_quaternion()
    b.lathe(prof, paint, center=c, sides=30, mod=ribs, spline=2, part=part, tilt=q)
    if stem:
        top = Vector(c) + q @ V(0, 0, H * 0.93)
        path = [top, top + q @ V(0.01, 0, 0.05), top + q @ V(0.035, 0.01, 0.1), top + q @ V(0.06, 0.02, 0.12)]
        b.tube(path, [0.032, 0.026, 0.022, 0.018], pal("moss"), sides=6, part=part)


def a_citrouille(b):
    pumpkin(b, V(0, 0, 0), 0.42, 0.62, 1.0)


def a_citrouilles_groupe(b):
    pumpkin(b, V(0, 0, 0), 0.4, 0.58, 0.5)
    pumpkin(b, V(0.66, 0.25, 0), 0.3, 0.42, 1.7, tilt=0.12)
    pumpkin(b, V(-0.2, 0.7, 0), 0.24, 0.34, 2.9, tilt=-0.15)
    vine = [V(0.35, 0.3, 0.02), V(0.1, 0.5, 0.03), V(-0.1, 0.35, 0.03), V(-0.45, 0.2, 0.025), V(-0.75, 0.38, 0.03)]
    b.tube(vine, lambda t: 0.013 * (1 - 0.5 * t), pal("moss"), sides=5)
    lp = grad("B", "green", 0.0, 0.3)
    for k, (pos, a) in enumerate([(V(0.0, 0.5, 0.05), 1.2), (V(-0.45, 0.2, 0.05), -0.6), (V(-0.75, 0.38, 0.05), 2.4), (V(0.45, -0.2, 0.05), 0.4)]):
        for j in range(3):
            aa = a + (j - 1) * 0.9
            blade(b, pos, pos + V(math.cos(aa) * 0.32, math.sin(aa) * 0.32, 0.1 + 0.03 * j), 0.1, lp, bend=-0.06, th=0.006, bend_dir=V(0, 0, 1), start=0.25, pw=0.7, n=5)


def a_pomme_de_pin(b):
    cone = pal("chestnut")
    cone2 = pal("bark")
    for k, (c, tilt, s) in enumerate([(V(0, 0, 0.07), (1.5, 0, 0.3), 1.0), (V(0.3, 0.22, 0.06), (1.45, 0, 2.0), 0.85), (V(-0.2, 0.3, 0.065), (1.4, 0, 3.8), 0.75)]):
        n = 12
        prof = []
        for i in range(n + 1):
            t = i / n
            rr = 0.075 * s * math.sin(math.pi * (0.12 + 0.88 * t)) ** 0.8 * (1 - 0.2 * t)
            if i == 0:
                rr = 0.018 * s
            prof.append((max(rr, 0.001), 0.2 * s * t))
        prof[-1] = (0.001, prof[-1][1])
        mod = lambda a, t, k=k: 1 + 0.16 * math.cos(6 * a - 20 * t + k) * math.sin(math.pi * min(1, t * 1.1)) ** 0.5
        q = Euler(tilt).to_quaternion()
        b.lathe(prof, cone if k % 2 == 0 else cone2, center=c, sides=14, mod=mod, spline=3, tilt=q)
    for k in range(4):
        a = k * 1.7 + 0.5
        pts = [V(0.5 * math.cos(a) * 0.9, 0.5 * math.sin(a) * 0.9, 0.012), V(0.5 * math.cos(a) * 0.9 + 0.1, 0.5 * math.sin(a) * 0.9 + 0.04, 0.012)]
        b.tube(pts, [0.006, 0.0035], pal("chestnut"), sides=4)


def a_branche(b):
    bark = tex("bark", 2, 0.4)
    main = [V(-0.95, 0.0, 0.07), V(-0.5, 0.06, 0.095), V(0.0, 0.0, 0.1), V(0.5, -0.07, 0.085), V(0.95, -0.02, 0.1)]
    b.tube(main, lambda t: 0.065 * (1 - 0.55 * t), bark, sides=9, cap_log=True)
    for k, (t, d, L) in enumerate([(0.3, V(0.6, 0.8, 0.4), 0.55), (0.55, V(0.5, -0.8, 0.5), 0.6), (0.78, V(0.7, 0.5, 0.7), 0.4)]):
        i = int(t * 4)
        p0 = main[i].lerp(main[min(4, i + 1)], t * 4 - i)
        dd = d.normalized()
        p1 = p0 + dd * L
        b.tube([p0 - dd * 0.02, p0 + dd * L * 0.5 + V(0, 0, 0.02), p1], lambda tt: 0.032 * (1 - 0.6 * tt), bark, sides=7, cap_log=True)
        for j in range(2):
            e = p0 + dd * L * (0.55 + 0.25 * j)
            dd2 = (dd + V(0.3 * (j * 2 - 1), 0.5 * (j * 2 - 1), 0.4)).normalized()
            b.tube([e, e + dd2 * 0.16], [0.014, 0.008], bark, sides=5, cap_log=True)


def a_buches_empilees(b):
    bark = tex("bark", 2, 0.4)
    r = b.rnd
    rows = [4, 3, 2]
    R = 0.115
    for ri, cnt in enumerate(rows):
        for k in range(cnt):
            x = (k - (cnt - 1) / 2) * R * 2.05
            z = R + ri * R * 1.78
            L = 0.8 + r.uniform(-0.04, 0.04)
            yo = r.uniform(-0.04, 0.04)
            rr = R * r.uniform(0.9, 1.05)
            b.tube([V(x, -L / 2 + yo, z), V(x + 0.005, yo, z + 0.004), V(x, L / 2 + yo, z)], [rr] * 3, bark, sides=11, cap_log=True)
    b.tube([V(0.0, -0.4, 0.045), V(0.0, 0.4, 0.045)], [0.04, 0.04], pal("darkwood"), sides=5, cap_a=True)


def a_tas_de_feuilles(b):
    r = b.rnd
    cols = [grad("A", "autumn", 0.0, 0.5), pal("orange"), pal("rust"), pal("yellow"), pal("amber"), pal("chestnut")]
    for i in range(16):
        a = r.uniform(0, 6.28)
        d = math.sqrt(r.random()) * 0.42
        R = r.uniform(0.18, 0.32) * (1 - d)
        b.blob(V(math.cos(a) * d, math.sin(a) * d, 0.0), max(R, 0.14), cols[i % 2 if i < 6 else r.randrange(len(cols))], amp=0.3, freq=2.4, squash=(1, 1, 0.6), seed=i, sub=2)
    for i in range(40):
        a = r.uniform(0, 6.28)
        d = math.sqrt(r.random()) * 0.75
        h = max(0.0, 0.2 * (1 - d / 0.45)) if d < 0.45 else 0.0
        p = V(math.cos(a) * d, math.sin(a) * d, h * 0.9 + 0.025)
        aa = r.uniform(0, 6.28)
        p1 = p + V(math.cos(aa) * 0.1, math.sin(aa) * 0.1, 0.0)
        b.tube([p, p.lerp(p1, 0.5) + V(0, 0, 0.012), p1], leaf_profile(0.045, 0.003, 0.9, 0.25), cols[2 + i % 4], sides=4)


def a_amanite(b):
    r = b.rnd
    for k, (c, s, tilt) in enumerate([(V(0, 0, 0), 1.0, (0.0, 0.0)), (V(0.34, 0.2, 0), 0.62, (0.18, 0.1)), (V(-0.22, 0.3, 0), 0.4, (-0.2, 0.1))]):
        q = Euler((tilt[0], tilt[1], 0)).to_quaternion()
        H = 0.26 * s
        stem = [(0.001, 0.0), (0.045 * s, 0.0), (0.036 * s, H * 0.4), (0.028 * s, H * 0.8), (0.026 * s, H)]
        b.lathe(stem, pal("ivory"), center=c, sides=12, tilt=q, spline=2)
        # collerette
        z = H * 0.62
        b.lathe([(0.03 * s, z + 0.02 * s), (0.07 * s, z), (0.06 * s, z - 0.025 * s), (0.03 * s, z - 0.01 * s)], pal("white"), center=c, sides=14, tilt=q)
        capR, capH = 0.17 * s, 0.13 * s
        prof = [(0.001, H + capH)]
        for i in range(1, 9):
            ang = math.pi / 2 * i / 8
            prof.append((capR * math.sin(ang), H + capH * math.cos(ang) ** 0.8 - 0.0))
        prof += [(capR * 0.9, H - 0.012 * s), (0.04 * s, H - 0.0)]
        b.lathe(prof, pal("red"), center=c, sides=20, tilt=q, spline=2)
        b.lathe([(0.001, H - 0.003 * s), (capR * 0.88, H - 0.01 * s)], pal("cream"), center=c, sides=20, tilt=q, cap_a=True) if False else None
        for j in range(11):
            aa = r.uniform(0, 6.28)
            el = r.uniform(0.15, 1.2)
            pr = capR * math.sin(math.pi / 2 - el)
            zz = H + capH * math.cos(math.pi / 2 - el) ** 0.8
            pos = c + q @ V(math.cos(aa) * pr * 0.96, math.sin(aa) * pr * 0.96, zz - 0.002)
            b.blob(pos, 0.026 * s * r.uniform(0.7, 1.1), pal("white"), amp=0.1, sub=2, squash=(1, 1, 0.5), rot=Euler((tilt[0], tilt[1], 0)).to_quaternion() @ V(math.cos(aa) * math.cos(el), math.sin(aa) * math.cos(el), math.sin(el)).to_track_quat("Z", "Y"))


def a_pierres_de_gue(b):
    r = b.rnd
    g = grad("B", "stone", 0.0, 0.17)
    pts = [(-1.3, 0.0, 0.34), (-0.65, 0.15, 0.3), (0.0, -0.06, 0.36), (0.68, 0.14, 0.31), (1.32, -0.02, 0.33)]
    for k, (x, y, R) in enumerate(pts):
        b.blob(V(x, y, 0.0), (R * 1.15, R, R * 0.36), g, amp=0.18, freq=1.8, seed=k + 1, sub=3, rot=Euler((0, 0, r.uniform(0, 3))).to_quaternion())
    for k in range(5):
        a = r.uniform(0, 6.28)
        b.blob(V(r.uniform(-1.4, 1.4), r.uniform(-0.35, 0.4), 0.0), 0.07, grad("B", "earth", 0.0, 0.1), amp=0.2, squash=(1, 1, 0.5), seed=k + 20, sub=2)


def a_feu_de_camp(b):
    r = b.rnd
    g = grad("B", "stone", 0.0, 0.3)
    bark = tex("bark", 2, 0.4)
    b.blob(V(0, 0, 0.0), (0.42, 0.42, 0.04), pal("dkstone"), amp=0.05, sub=2)
    for k in range(10):
        a = k * 2 * math.pi / 10 + 0.2
        b.blob(V(math.cos(a) * 0.55, math.sin(a) * 0.55, 0.0), (0.14, 0.12, 0.1), g, amp=0.22, seed=k, sub=2, rot=Euler((0, 0, a)).to_quaternion())
    for k in range(5):
        a = k * 2 * math.pi / 5 + 0.5
        d = V(math.cos(a), math.sin(a), 0)
        p0 = d * 0.52 + V(0, 0, 0.1)
        p1 = d * 0.03 + V(0, 0, 0.3)
        b.tube([p0, p0.lerp(p1, 0.5) + V(0, 0, 0.01), p1], [0.06, 0.057, 0.05], bark, sides=9, cap_log=True)
    for k, (h, rr, col, o) in enumerate([(0.62, 0.17, "rust", (0, 0)), (0.5, 0.13, "orange", (0.08, 0.04)), (0.4, 0.1, "yellow", (-0.06, -0.05)), (0.34, 0.09, "orange", (-0.1, 0.1)), (0.3, 0.08, "rust", (0.12, -0.1))]):
        prof = [(0.001, 0.14), (rr, 0.14), (rr * 0.95, 0.14 + h * 0.3), (rr * 0.62, 0.14 + h * 0.65), (rr * 0.2, 0.14 + h * 0.9), (0.001, 0.14 + h)]
        mod = lambda a, t, k=k: 1 + 0.18 * math.sin(3 * a + k) * t
        b.lathe(prof, pal(col), center=V(o[0], o[1], 0), sides=10, mod=mod, spline=2, smooth=True)


def a_cloture(b):
    r = b.rnd
    wood = tex("orange", 1.2, 0.8, tri=True)
    post = tex("bark", 2, 0.5)
    xs = [-1.5, -0.5, 0.5, 1.5]
    for k, x in enumerate(xs):
        h = 1.0 + r.uniform(-0.04, 0.04)
        b.tube([V(x, 0, 0.0), V(x, 0, h)], [0.065, 0.06], post, sides=8, cap_log=True)
        b.lathe([(0.001, h + 0.07), (0.062, h + 0.0)], pal("chestnut"), center=V(x, 0, 0), sides=8) if False else None
    for z in (0.35, 0.78):
        pts = [V(-1.6 + 0.0, 0.07, z + 0.01), V(-0.5, 0.07, z - 0.012), V(0.5, 0.07, z + 0.012), V(1.6, 0.07, z - 0.01)]
        b.tube(pts, [0.036] * 4, wood, sides=7, cap_log=True)
    for z in (0.35, 0.78):
        pts = [V(-1.6, -0.07, z + 0.01), V(-0.5, -0.07, z + 0.02), V(0.5, -0.07, z - 0.02), V(1.6, -0.07, z)]
        b.tube(pts, [0.03] * 4, wood, sides=6, cap_log=True)


def a_panneau(b):
    post = tex("bark", 2, 0.8)
    wood = tex("orange", 1.4, 0.8, tri=True)
    b.tube([V(0, 0, 0.0), V(0.01, 0, 1.0), V(0, 0, 1.9)], [0.07, 0.06, 0.055], post, sides=8, cap_log=True)
    b.lathe([(0.001, 2.0), (0.062, 1.9)], pal("chestnut"), center=V(0, 0, 0), sides=8)
    for k, (z, dirn, ang) in enumerate([(1.62, 1, 0.05), (1.3, -1, -0.04)]):
        L = 0.95
        poly = [(-0.35 * dirn, -0.11), (0.62 * dirn, -0.11), (0.88 * dirn, 0.0), (0.62 * dirn, 0.11), (-0.35 * dirn, 0.11)]
        if dirn < 0:
            poly = list(reversed(poly))
        b.prism(poly, -0.095, -0.055, wood, rot=Euler((0, ang, 0)).to_quaternion(), c=(0, 0, z))
        for sx in (-0.2 * dirn, 0.3 * dirn):
            b.blob(V(sx, -0.1, z + sx * ang * -1), 0.016, pal("black"), amp=0.0, sub=2, squash=(1, 0.6, 1))


def a_pont_bois(b):
    r = b.rnd
    wood = tex("orange", 1.2, 0.6, tri=True)
    post = tex("bark", 2, 0.5)
    L = 3.4
    def zc(x):
        return 0.28 * (1 - (x / (L / 2)) ** 2)
    n = 14
    for i in range(n):
        x = -L / 2 + (i + 0.5) * L / n
        ang = math.atan(-0.56 * x / (L / 2) ** 2)
        b.box(V(x, r.uniform(-.01, .01), zc(x) + 0.14), (L / n * 0.86, 1.25, 0.05), wood, rot=Euler((0, -ang, 0)).to_quaternion())
    for sy in (-0.5, 0.5):
        pts = [V(-L / 2 - 0.1 + k * (L + 0.2) / 8, sy, zc(-L / 2 + k * L / 8) + 0.08) for k in range(9)]
        b.tube(pts, [0.06] * 9, post, sides=7, cap_log=True)
    for sy in (-0.65, 0.65):
        for k in range(5):
            x = -L / 2 + 0.15 + k * (L - 0.3) / 4
            b.tube([V(x, sy, zc(x) + 0.1), V(x, sy, zc(x) + 0.98)], [0.045, 0.04], post, sides=7, cap_log=True)
        pts = [V(-L / 2 + 0.15 + k * (L - 0.3) / 8, sy, zc(-L / 2 + 0.15 + k * (L - 0.3) / 8) + 0.95) for k in range(9)]
        b.tube(pts, [0.03] * 9, wood, sides=6, cap_log=True)


def a_rocher_cristaux(b):
    r = b.rnd
    g = grad("B", "stone", 0.0, 0.9)
    b.blob(V(0, 0, 0.1), (0.85, 0.65, 0.42), g, amp=0.3, freq=1.4, seed=3, sub=3)
    b.blob(V(0.55, 0.2, 0.08), (0.38, 0.3, 0.26), grad("B", "earth", 0.0, 0.5), amp=0.3, seed=8, sub=2)
    cols = ["violet", "purple", "violet", "fuchsia", "purple", "violet", "magenta", "violet"]
    spec = [(V(0.0, 0.0, 0.3), 0.0, 0.0, 0.2, 0.9), (V(0.28, -0.12, 0.28), 0.35, 0.5, 0.14, 0.62), (V(-0.3, 0.1, 0.25), -0.45, 2.2, 0.15, 0.7),
            (V(0.1, 0.3, 0.2), 0.2, 1.1, 0.1, 0.5), (V(-0.2, -0.25, 0.2), -0.35, 4.0, 0.11, 0.55), (V(0.5, 0.2, 0.2), 0.6, 0.3, 0.09, 0.42), (V(-0.52, -0.1, 0.12), -0.7, 3.2, 0.08, 0.36), (V(0.3, 0.38, 0.13), 0.3, 5.0, 0.07, 0.3)]
    for k, (c, tilt, az, rad, h) in enumerate(spec):
        q = Euler((0, tilt, 0)).to_quaternion()
        q = Euler((0, 0, az)).to_quaternion() @ q
        prof = [(0.001, -0.05), (rad, -0.05), (rad, h * 0.62), (rad * 0.8, h * 0.72), (0.001, h)]
        b.lathe(prof, pal(cols[k]), center=c, sides=6, tilt=q, smooth=False)


def a_rocher_arche(b):
    r = b.rnd
    g = grad("B", "earth", 0.0, 4.2)
    g2 = grad("B", "stone", 0.0, 4.2)
    rx, rz = 1.7, 1.9
    for k in range(22):
        t = k / 21
        a = math.pi * t
        R = 0.5 * (1.18 - 0.3 * math.sin(a)) + r.uniform(-0.05, 0.07)
        c = V(math.cos(a) * rx + r.uniform(-.06, .06), r.uniform(-0.1, 0.1), math.sin(a) * rz + 0.35)
        b.blob(c, (R * 1.0, R * 1.1, R * 0.95), g if k % 3 == 1 else g2, amp=0.42, freq=1.9, seed=k + 1, sub=3)
    for k, (x, rr) in enumerate([(-1.8, 0.78), (1.8, 0.74), (-2.3, 0.5), (2.25, 0.48), (-1.2, 0.34), (1.25, 0.36)]):
        b.blob(V(x, r.uniform(-0.15, 0.15), 0.18), (rr * 1.1, rr, rr * 0.6), g2, amp=0.4, freq=1.8, seed=k + 30, sub=3)


def split(top, side, thr=0.45):
    """Peinture à deux zones : `top` sur les faces tournées vers le haut, `side` ailleurs."""
    return lambda co, n, pu, pv: (top if n is not None and n.z > thr else side)(co, n, pu, pv)


def a_panier_osier(b):
    r = b.rnd
    wick = tex("wicker", 3, 2.2)
    prof = [(0.001, 0.0), (0.2, 0.0), (0.26, 0.08), (0.31, 0.2), (0.33, 0.3), (0.31, 0.3), (0.29, 0.28), (0.2, 0.04), (0.001, 0.03)]
    b.lathe(prof, wick, sides=22, spline=2)
    b.lathe([(0.34, 0.27), (0.34, 0.33), (0.30, 0.33), (0.3, 0.27)], wick, sides=22, spline=1)
    path = [V(-0.33 * math.cos(a), 0.0, 0.3 + 0.38 * math.sin(a)) for a in [math.pi * k / 10 for k in range(11)]]
    b.tube(path, [0.022] * 11, wick, sides=7)
    cols = ["red", "red", "red2", "sun"]
    for k in range(7):
        a = r.uniform(0, 6.28)
        d = r.uniform(0.0, 0.17)
        b.blob(V(math.cos(a) * d, math.sin(a) * d, 0.27 + r.uniform(0, 0.05)), 0.085, pal(cols[k % 4]), amp=0.06, sub=2, seed=k, squash=(1, 1, 0.92))
    for k in range(4):
        a = k * 1.6 + 0.4
        c = V(math.cos(a) * 0.14, math.sin(a) * 0.14, 0.34)
        b.blob(c, 0.055, pal("chestnut"), amp=0.05, sub=2, squash=(1, 1, 0.6), seed=k + 20)
        b.lathe([(0.02, 0.0), (0.021, 0.07)], pal("ivory"), center=c + V(0, 0, -0.07), sides=8)


def a_buches_bouleau(b):
    bark = tex("birch", 2, 0.3)
    r = b.rnd
    R = 0.1
    for ri, cnt in enumerate([3, 2]):
        for k in range(cnt):
            x = (k - (cnt - 1) / 2) * R * 2.05
            z = R + ri * R * 1.78
            L = 0.85 + r.uniform(-0.05, 0.05)
            yo = r.uniform(-0.04, 0.04)
            b.tube([V(x, -L / 2 + yo, z), V(x + 0.004, yo, z + 0.004), V(x, L / 2 + yo, z)], [R * r.uniform(0.92, 1.05)] * 3, bark, sides=11, cap_log=True)
    b.tube([V(0.45, -0.5, R), V(0.5, 0.45, R * 1.02)], [R * 0.9] * 2, bark, sides=11, cap_log=True)


def a_motte_herbe(b):
    r = b.rnd
    p = split(tex("grass", 3, 3, tri=True), pal("dkbrown"))
    b.blob(V(0, 0, 0.0), (0.7, 0.62, 0.3), p, amp=0.14, freq=1.5, seed=4, sub=3)
    for k in range(6):
        a = r.uniform(0, 6.28)
        b.blob(V(math.cos(a) * 0.55, math.sin(a) * 0.5, 0.0), (0.2, 0.2, 0.12), p, amp=0.2, seed=k + 9, sub=2)
    gp = grad("B", "grass", 0.0, 0.5)
    for k in range(30):
        a = r.uniform(0, 6.28)
        d = math.sqrt(r.random()) * 0.55
        base = V(math.cos(a) * d, math.sin(a) * d * 0.9, 0.28 * math.sqrt(max(0.0, 1 - (d / 0.7) ** 2)))
        aa = r.uniform(0, 6.28)
        blade(b, base, base + V(math.cos(aa) * 0.07, math.sin(aa) * 0.07, r.uniform(0.15, 0.3)), 0.018, gp, bend=0.05, part=None, n=4, start=0.3)
