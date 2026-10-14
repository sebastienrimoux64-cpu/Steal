"""Constructions en bois réalistes : pont de bois, bûches de bouleau, tas de bûches, clôture, panneau."""
import math
import random

from mathutils import Euler, Vector

import rmat
from rgeo import RB, V


def birch_peel(name="BouleauPelure"):
    """Lambeau d'écorce de bouleau qui se décolle : papier blanc crème dessus, brun orangé dessous, translucide."""
    m = rmat.M(name)
    u, v, _ = m.sep(m.uv())
    n = m.noise(m.comb(u, v, 0), 14.0, 5, 0.55)
    col = m.mix(n, rmat.L((0.80, 0.77, 0.70)), rmat.L((0.94, 0.92, 0.86)))
    mark = m.ramp(m.noise(m.comb(m.math("MULTIPLY", u, 2.0), m.math("MULTIPLY", v, 30.0), 0.0), 4.0, 2), [(0.6, (0, 0, 0)), (0.68, (1, 1, 1))])
    col = m.mix(m.math("MULTIPLY", mark, 0.85), col, rmat.L((0.04, 0.035, 0.03)))
    bf = m.geom().outputs["Backfacing"]
    col = m.mix(bf, col, rmat.L((0.60, 0.42, 0.26)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.5)
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", rmat.L((0.85, 0.72, 0.5)))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", 0.3)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


def a_buches_bouleau(b):
    """Pile de bûches de bouleau posées au sol : écorce papier blanc à lenticelles noires, lambeaux décollés, bouts coupés avec cernes et fentes."""
    rng = random.Random(8)
    bark = rmat.birch_bark()
    endg = rmat.end_grain("BoutBouleau", light=(0.86, 0.76, 0.58), dark=(0.66, 0.52, 0.34), bark_ring=(0.82, 0.78, 0.7), rings=20, cracks=0.6)
    peel = birch_peel()
    logs = []
    # (x, y, z, longueur, rayon, rotation z)
    spec = [(-0.13, 0.0, 0.1, 1.5, 0.105, 0.04), (0.10, 0.02, 0.1, 1.45, 0.095, -0.03), (-0.33, 0.05, 0.095, 1.38, 0.09, 0.02),
            (-0.02, 0.0, 0.265, 1.4, 0.1, 0.02), (-0.24, -0.03, 0.255, 1.3, 0.085, -0.04), (0.5, 0.45, 0.085, 1.2, 0.08, 0.5)]
    for k, (x, y, z, Lg, r, rz) in enumerate(spec):
        d = V(math.cos(rz), math.sin(rz), 0)
        c = V(x, y, z)
        path = []
        for i in range(13):
            t = i / 12 - 0.5
            p = c + d * (Lg * t) + V(0, 0, 0.012 * math.sin(i * 0.8 + k))
            p += V(-d.y, d.x, 0) * 0.015 * math.sin(i * 0.5 + k * 2)
            path.append(p)
        rr = lambda t, r=r, k=k: r * (1.0 + 0.05 * math.sin(t * 7 + k) + 0.03 * math.sin(t * 19 + k)) * (1.03 - 0.06 * t)
        b.tube(path, rr, bark, sides=22, noise_amp=0.045, noise_f=1.1, seed=k * 2, cap_a=True, cap_b=True, cap_mat=endg, cap_disc=True, flute=0.025, flute_n=3, uv_len=1.0)
        logs.append((path, r, d))
    # nœuds / départ de branches coupées
    for k in range(7):
        path, r, d = logs[rng.randrange(len(logs))]
        i = rng.randrange(2, 10)
        p = path[i]
        out = V(rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0.5, 0.3)))
        out = (out - d * out.dot(d)).normalized()
        b.tube([p + out * r * 0.85, p + out * (r + 0.05)], [0.022, 0.017], bark, sides=8, cap_b=True, cap_mat=endg, cap_disc=True)
    # lambeaux d'écorce qui se décollent et s'enroulent en parchemin
    for k in range(11):
        path, r, d = logs[rng.randrange(len(logs))]
        i = rng.randrange(1, 11)
        p0 = path[i]
        out = V(rng.gauss(0, 1), rng.gauss(0, 1), abs(rng.gauss(0.7, 0.4)) + 0.2)
        out = (out - d * out.dot(d)).normalized()
        tang = d if rng.random() < 0.5 else -d
        side = out.cross(tang).normalized()
        Lc = rng.uniform(0.12, 0.26)
        w = rng.uniform(0.045, 0.09)
        nlen, nw = 10, 9
        rings = []
        for j in range(nlen + 1):
            t = j / nlen
            turns = 3.2 * t ** 2.2                    # enroulement croissant vers le bout libre
            lift = 0.09 * t ** 2.2 * Lc * 4
            rho = w / max(turns, 0.35)
            ctr = p0 + out * (r * 1.005 + lift) + tang * (Lc * t) * (1.0 - 0.25 * t)
            ring = []
            for s_ in range(nw):
                f = s_ / (nw - 1) - 0.5
                ang = turns * f * 2.0
                ring.append(ctr + side * (rho * math.sin(ang)) + out * (rho * (1 - math.cos(ang))))
            rings.append(ring)
        b.loft(rings, peel, uvfn=lambda uu, vv, co: (uu, vv), closed=False, smooth=True)
    # litière, brindilles, herbes autour
    import scatter
    dead = rmat.dead_leaf()
    grass = rmat.grass_blade("HerbeSousBois", base=(0.04, 0.10, 0.02), tip=(0.22, 0.34, 0.07))
    twig_m = rmat.bark("Brindille", "furrowed", dark=(0.05, 0.04, 0.03), mid=(0.2, 0.15, 0.1), light=(0.35, 0.28, 0.2), around=2.0, along=1.0)
    avoid_logs = lambda x, y: abs(y - 0.0) < 0.55 and abs(x) < 0.8
    scatter.leaf_litter(b, dead, (0.0, 0.1), (2.2, 1.7), 320, rng, avoid=lambda x, y: False, z=0.014)
    scatter.twigs(b, twig_m, (0.0, 0.1), (2.2, 1.6), 24, rng, avoid=avoid_logs)
    scatter.field(b, grass, (0.0, 0.1), (2.4, 1.9), 55, rng, hmin=0.12, hmax=0.34, avoid=avoid_logs)
    return b


def a_pont_bois(b):
    """Pont de bois en arc : poutres cintrées, planches patinées avec clous, poteaux et mains courantes en corde, culées de pierre."""
    rng = random.Random(14)
    wood = rmat.plank_wood("BoisPont", tone=((0.07, 0.05, 0.035), (0.30, 0.22, 0.15), (0.50, 0.40, 0.29)), gray=0.65, cracks=0.9)
    wood2 = rmat.plank_wood("BoisPoutre", tone=((0.05, 0.035, 0.025), (0.22, 0.16, 0.11), (0.42, 0.33, 0.24)), gray=0.5, cracks=0.8, grain=0.7)
    post_m = rmat.bark("EcorcePoteau", "furrowed", dark=(0.04, 0.03, 0.025), mid=(0.17, 0.13, 0.10), light=(0.36, 0.30, 0.24), around=2.5, along=0.5, moss=0.1)
    rope = rmat.rope("CordeMainCourante", (0.58, 0.46, 0.29))
    iron = rmat.iron("ClouRouille")
    stone = rmat.rock("PierreCulee", dark=(0.10, 0.095, 0.085), mid=(0.28, 0.265, 0.24), light=(0.48, 0.46, 0.41), crack=0.5, moss=0.28, lichen=0.3, scale=1.0, grain=1.2)
    Lb, A = 3.8, 0.33          # longueur et flèche de l'arc

    def zc(x):
        return A * (1 - (x / (Lb / 2)) ** 2) + 0.55

    def slope(x):
        return -2 * A * x / (Lb / 2) ** 2
    # poutres cintrées (deux par côté) : segments de poutre suivant l'arc
    nseg = 22
    for sy in (-0.52, 0.52):
        for k in range(nseg):
            x0 = -Lb / 2 - 0.15 + (Lb + 0.3) * k / nseg
            x1 = -Lb / 2 - 0.15 + (Lb + 0.3) * (k + 1) / nseg
            xm = (x0 + x1) / 2
            ang = math.atan(slope(xm))
            Lg = (x1 - x0) / math.cos(ang) * 1.02
            b.plank(V(xm, sy, zc(xm) - 0.16), (Lg, 0.14, 0.2), wood2, rot=Euler((0, -ang, 0)).to_quaternion(), bevel=0.012, seed=k * 7 + int(sy * 10), uv_off=(0, 0))
    # planches du tablier avec espaces, clous
    n = 21
    for k in range(n):
        x = -Lb / 2 + 0.1 + (Lb - 0.2) * k / (n - 1)
        ang = math.atan(slope(x))
        Wp = (Lb - 0.2) / (n - 1) - 0.022
        y_jit = rng.uniform(-0.012, 0.012)
        b.plank(V(x, y_jit, zc(x)), (1.38, Wp, 0.05), wood, rot=Euler((0, -ang, math.pi / 2)).to_quaternion(), bevel=0.006, seed=k * 3, warp=0.004, uv_off=(rng.uniform(0, 8), rng.uniform(0, 8)))
        for sy in (-0.52, 0.52):
            for dx in (-0.02, 0.02):
                if rng.random() < 0.85:
                    px = x + dx * 1.0
                    b.tube([V(px, sy + dx * 0.4, zc(px) + 0.028), V(px, sy + dx * 0.4, zc(px) + 0.04)], [0.0065, 0.0065], iron, sides=6, cap_a=True, cap_b=True)
    # poteaux + mains courantes en corde
    posts_x = [-Lb / 2 + 0.12 + (Lb - 0.24) * i / 3 for i in range(4)]
    for sy in (-0.66, 0.66):
        tops = []
        for i, x in enumerate(posts_x):
            h = 0.98 + rng.uniform(-0.02, 0.02)
            z0 = zc(x) - 0.1
            b.tube([V(x, sy, z0), V(x + 0.003, sy, z0 + h * 0.5), V(x, sy + 0.003, z0 + h)], [0.058, 0.052, 0.047], post_m, sides=12, noise_amp=0.06, cap_b=True, cap_disc=False, seed=i * 5)
            tops.append(V(x, sy, z0 + h - 0.05))
        for dz in (0.0, -0.32):
            pts = []
            for i in range(len(tops) - 1):
                a, c = tops[i], tops[i + 1]
                for j in range(9):
                    t = j / 8
                    p = a.lerp(c, t)
                    p.z += dz - 0.09 * math.sin(math.pi * t)
                    pts.append(p)
            b.tube(pts, [0.017] * len(pts), rope, sides=8, cap_a=True, cap_b=True, uv_len=1.0)
    # culées de pierre et berges
    for sx in (-1, 1):
        for k in range(5):
            x = sx * (Lb / 2 + 0.35 + 0.35 * rng.random() + k * 0.12)
            y = rng.uniform(-0.8, 0.8)
            s = rng.uniform(0.28, 0.5)
            b.rock(V(x, y, s * 0.2), (s * 1.2, s, s * 0.7), stone, seed=700 + k + (0 if sx < 0 else 10), sub=5, planes=8, amp=0.14, kcut=0.1, detail=0.03)
    import scatter
    grass = rmat.grass_blade("HerbePont", base=(0.05, 0.12, 0.02), tip=(0.28, 0.40, 0.08))
    rr = random.Random(5)
    scatter.field(b, grass, (0, 0), (3.6, 1.6), 150, rr, hmin=0.15, hmax=0.55, avoid=lambda x, y: abs(x) < 2.0 and abs(y) < 0.75)
    return b
