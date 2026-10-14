"""Nouvelles plantes du NaturePack : marguerites, tournesols, coquelicots, rosier, bambou, blé, agave, herbe de la pampa, mousse."""
import math

from common import V, arc, blade, flower_head, leaf_profile
from natlib import pal, grad, tex


def a_fleurs_marguerites(b):
    r = b.rnd
    stem = grad("B", "grass", 0, 0.6)
    leafp = grad("B", "green", 0, 0.3)
    for i in range(7):
        a = i * 2 * math.pi / 7 + r.uniform(-.3, .3)
        rad = 0.1 + r.uniform(0, 0.17)
        base = V(math.cos(a) * rad * 0.5, math.sin(a) * rad * 0.5, 0)
        h = r.uniform(0.34, 0.56)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        nm = b.chain(f"tige{i + 1}", base, tip, 2, amp=1.3)
        path = arc(base, tip, 0.04, 6, V(math.cos(a), math.sin(a), 0))
        b.tube(path, [0.0055] * 6, stem, sides=5, part=nm)
        dd = (path[-1] - path[-2]) + V(0, -0.45, 0.25)
        flower_head(b, path[-1], dd, 0.062, 14, pal("white"), pal("sun"), part=nm, center_r=0.38, w=0.26)
        for k in range(2):
            ab = a + (k * 2 - 1) * 1.1
            blade(b, base + V(0, 0, 0.02), base + V(math.cos(ab) * 0.13, math.sin(ab) * 0.13, 0.11 + 0.04 * k), 0.016, leafp, bend=0.03, part=nm, start=0.3)
    for k in range(6):
        ab = k * 1.05
        blade(b, V(0, 0, 0.01), V(math.cos(ab) * 0.17, math.sin(ab) * 0.17, 0.07), 0.02, leafp, bend=0.02, start=0.3)


def a_tournesols(b):
    r = b.rnd
    stem = grad("B", "green2", 0, 1.4)
    leafp = grad("B", "grass", 0.1, 1.2)
    dd0 = V(0.0, -0.8, 0.35)
    for i in range(3):
        a = i * 2.1 + 0.4
        base = V(math.cos(a) * 0.22, math.sin(a) * 0.22, 0)
        h = 1.1 + 0.22 * ((i * 5) % 3) / 2
        tip = V(base.x + 0.06, base.y - 0.05, h)
        nm = b.chain(f"tige{i + 1}", base, tip, 3, amp=0.7)
        path = arc(base, tip, 0.09, 8, V(0.5, -1, 0))
        b.tube(path, lambda t: 0.03 - 0.008 * t, stem, sides=7, part=nm)
        head = path[-1]
        for k in range(4):
            z = 0.25 + k * 0.22
            ab = a + k * 2.1
            p0 = path[min(7, int(z / h * 7))]
            blade(b, p0, p0 + V(math.cos(ab) * 0.3, math.sin(ab) * 0.3, -0.04 + 0.05 * (k % 2)), 0.075, leafp, bend=-0.08, th=0.01, part=nm, bend_dir=V(0, 0, 1), start=0.2, pw=0.7)
        dd = dd0 + V(math.cos(a) * 0.1, math.sin(a) * 0.1, 0)
        flower_head(b, head, dd, 0.2, 22, pal("sun"), pal("brown"), part=nm, center_r=0.5, w=0.21, petal_len=1.0, center_h=0.5)
        flower_head(b, head + V(0, -0.015, 0.0), dd, 0.19, 22, pal("amber"), pal("chestnut"), part=nm, center_r=0.3, w=0.2, petal_len=0.8, rot=0.14, center_h=0.5)


def a_coquelicots(b):
    r = b.rnd
    stem = grad("B", "green3", 0, 0.8)
    leafp = grad("B", "green", 0, 0.3)
    for i in range(7):
        a = i * 2 * math.pi / 7 + r.uniform(-.3, .3)
        rad = 0.08 + r.uniform(0, 0.17)
        base = V(math.cos(a) * rad * 0.4, math.sin(a) * rad * 0.4, 0)
        h = r.uniform(0.42, 0.78)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        nm = b.chain(f"tige{i + 1}", base, tip, 2, amp=1.5)
        path = arc(base, tip, 0.06, 7, V(math.cos(a), math.sin(a), 0))
        b.tube(path, lambda t: 0.0045 * (1 - 0.3 * t), stem, sides=5, part=nm)
        end = path[-1]
        if i % 4 == 3:
            b.blob(end + V(0, 0, 0.02), 0.022, pal("leaf"), amp=0.05, sub=2, squash=(0.85, 0.85, 1.25), part=nm)
            b.blob(end + V(0, 0, 0.034), 0.014, pal("red"), amp=0.0, sub=2, squash=(0.8, 0.8, 0.9), part=nm)
        else:
            d = (path[-1] - path[-2]) + V(0.0, -0.5, 0.45)
            flower_head(b, end, d, 0.08, 4, pal("red"), pal("black"), part=nm, center_r=0.18, w=0.62, cup=0.28, th=0.003, petal_len=0.95, rot=0.8 + i, center_h=1.2)
            b.blob(end + V(0, 0, 0.012), 0.014, pal("dkbrown"), amp=0.0, sub=2, part=nm)
        blade(b, base + V(0, 0, 0.02), base + V(math.cos(a + 1.3) * 0.14, math.sin(a + 1.3) * 0.14, 0.12), 0.014, leafp, bend=0.03, part=nm, start=0.3)
    for k in range(5):
        ab = k * 1.3
        blade(b, V(0, 0, 0.01), V(math.cos(ab) * 0.15, math.sin(ab) * 0.15, 0.06), 0.018, leafp, bend=0.02, start=0.3)


def a_rosier(b):
    r = b.rnd
    wood = pal("brown")
    leaf = grad("A", "green", 0.0, 1.45)
    leaf2 = grad("A", "fresh", 0.0, 1.45)
    blobs = []
    for i in range(7):
        a = i * 2 * math.pi / 7 + r.uniform(-.3, .3)
        rad = 0.32 + r.uniform(0, 0.28)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, r.uniform(0.75, 1.2))
        nm = b.chain(f"tige{i + 1}", V(0, 0, 0.05), tip, 3, amp=0.55)
        path = arc(V(math.cos(a) * 0.03, math.sin(a) * 0.03, 0), tip, 0.2, 8, V(math.cos(a), math.sin(a), 0))
        b.tube(path, lambda t: 0.017 * (1 - 0.55 * t), wood, sides=5, part=nm)
        for k in range(6):
            p = path[min(7, 2 + k)]
            for j in range(2):
                o = V(r.uniform(-.13, .13), r.uniform(-.13, .13), r.uniform(0.0, 0.1))
                R = r.uniform(0.1, 0.16)
                b.blob(p + o, R, leaf if (k + j) % 2 else leaf2, amp=0.35, freq=2.2, sub=2, squash=(1, 1, 0.95), seed=i * 7 + k * 2 + j, part=nm)
                blobs.append((p + o, R, nm))
    b.blob(V(0, 0, 0.55), 0.36, leaf, amp=0.25, sub=2, squash=(1, 1, 1.0), seed=3, part="tige1")
    cols = ["pink", "crimson", "fuchsia", "palepink", "pink", "magenta", "crimson", "pink", "palepink"]
    top = sorted(blobs, key=lambda x: -x[0].z)
    chosen = []
    for c, R, nm in top:
        if all((c - c2).length > 0.26 for c2, _, _ in chosen):
            chosen.append((c, R, nm))
        if len(chosen) >= 9:
            break
    for k, (c, R, nm) in enumerate(chosen):
        col = cols[k % len(cols)]
        a = r.uniform(0, 6.28)
        pos = c + V(math.cos(a) * R * 0.5, math.sin(a) * R * 0.5, R * 0.8)
        for j in range(5):
            aa = j * 1.2566 + k
            b.blob(pos + V(math.cos(aa) * 0.045, math.sin(aa) * 0.045, -0.005), 0.052, pal(col), amp=0.08, sub=2, squash=(1, 0.85, 0.75), seed=k + j, part=nm)
        b.blob(pos + V(0, 0, 0.022), 0.05, pal(col), amp=0.08, sub=2, squash=(1, 1, 0.9), seed=k + 9, part=nm)
        b.blob(pos + V(0, 0, 0.04), 0.03, pal("palepink" if col != "palepink" else "white"), amp=0.1, sub=2, squash=(1, 1, 0.8), seed=k + 11, part=nm)


def a_bambou(b):
    r = b.rnd
    leafp = grad("A", "lime", 2.2, 3.7)
    for i in range(7):
        a = i * 2 * math.pi / 7 + r.uniform(-.2, .2)
        rad = r.uniform(0.1, 0.42) if i else 0.0
        H = r.uniform(2.6, 3.5)
        base = V(math.cos(a) * rad, math.sin(a) * rad, 0)
        lean = V(math.cos(a) * 0.12, math.sin(a) * 0.12, 0)
        tip = base + lean + V(0, 0, H)
        nm = b.chain(f"tige{i + 1}", base + V(0, 0, 0.2), tip, 4, amp=0.5)
        nodes = max(6, int(H / 0.34))
        seg = H / nodes
        for k in range(nodes):
            z0, z1 = k * seg, (k + 1) * seg
            p0 = base + lean * ((z0 / H) ** 2) + V(0, 0, z0)
            p1 = base + lean * ((z1 / H) ** 2) + V(0, 0, z1)
            rad_c = 0.035 * (1 - 0.35 * (z0 / H))
            mid = p0.lerp(p1, 0.5)
            b.tube([p0, mid, p1], [rad_c * 0.92, rad_c, rad_c * 0.92], grad("B", "green2", p0.z, p1.z + 0.02), sides=7, part=nm, cap_a=False, cap_b=False)
            b.tube([p1 - V(0, 0, 0.012), p1 + V(0, 0, 0.012)], [rad_c * 1.18] * 2, pal("dkgreen"), sides=7, part=nm)
            if k > nodes * 0.55 and k % 2 == 0:
                for s in (0, 1):
                    ab = a + s * 3.14 + k
                    tipb = p1 + V(math.cos(ab) * 0.38, math.sin(ab) * 0.38, 0.1)
                    b.tube(arc(p1, tipb, 0.04, 3), [0.005, 0.004, 0.003], pal("green"), sides=4, part=nm)
                    for j in range(4):
                        al = ab + (j - 1.5) * 0.45
                        blade(b, tipb, tipb + V(math.cos(al) * 0.3, math.sin(al) * 0.3, -0.12 - 0.02 * j), 0.032, leafp, bend=0.05, th=0.005, part=nm, bend_dir=V(0, 0, 1), start=0.2, n=4)
        for j in range(5):
            al = j * 1.256 + i
            blade(b, tip, tip + V(math.cos(al) * 0.34, math.sin(al) * 0.34, -0.06), 0.032, leafp, bend=0.04, th=0.005, part=nm, bend_dir=V(0, 0, 1), start=0.2, n=4)


def a_ble(b):
    r = b.rnd
    stem = grad("B", "green3", 0, 0.9)
    ear = pal("tan")
    awn = pal("amber")
    for i in range(16):
        a = i * 2.4 + r.uniform(-.3, .3)
        rad = 0.06 + 0.2 * math.sqrt((i + .5) / 16)
        base = V(math.cos(a) * rad * 0.7, math.sin(a) * rad * 0.7, 0)
        h = r.uniform(0.72, 0.95)
        tip = V(math.cos(a) * rad, math.sin(a) * rad, h)
        nm = b.chain(f"tige{i + 1}", base, tip, 2, amp=1.5)
        path = arc(base, tip, 0.07, 6, V(math.cos(a + 1), math.sin(a + 1), 0))
        b.tube(path, [0.0042, 0.0042, 0.004, 0.0038, 0.0035, 0.0033], stem, sides=4, part=nm)
        end = path[-1]
        dr = (path[-1] - path[-2]).normalized()
        from natlib import Quaternion
        rot = dr.to_track_quat("Z", "Y")
        b.blob(end + dr * 0.04, (0.014, 0.014, 0.05), ear, amp=0.06, sub=2, part=nm, rot=rot)
        for k in range(5):
            aa = k * 1.257 + i
            off = V(math.cos(aa) * 0.01, math.sin(aa) * 0.01, 0)
            q = rot.to_matrix()
            o = q @ off
            b.tube([end + dr * 0.02 + o, end + dr * 0.09 + o * 2.2, end + dr * 0.15 + o * 3.4], [0.0016, 0.0013, 0.0008], awn, sides=4, part=nm)
        if i % 2 == 0:
            blade(b, base + V(0, 0, 0.15), base + V(math.cos(a + 1.8) * 0.2, math.sin(a + 1.8) * 0.2, 0.3), 0.012, grad("B", "green3", 0, 0.9), bend=0.06, part=nm, n=5, start=0.2)


def a_agave(b):
    r = b.rnd
    lp = grad("B", "sage", 0.0, 0.85)
    spine = pal("dkbrown")
    n = 16
    for i in range(n):
        ring = i // 6
        a = i * 2.4 + r.uniform(-.15, .15)
        up = 0.2 + 0.3 * (2 - min(2, ring)) / 2 * 1.5
        L = 0.62 + 0.14 * (2 - min(2, ring)) / 2 - 0.0 * ring
        out = 0.34 + 0.2 * ring
        base = V(math.cos(a) * 0.04, math.sin(a) * 0.04, 0.03)
        tip = V(math.cos(a) * out, math.sin(a) * out, 0.2 + up * L * (1.2 - 0.25 * ring) + 0.12)
        path = arc(base, tip, 0.0, 6)
        path = [p + V(0, 0, -0.08 * math.sin(math.pi * k / 5) * 0.0 + 0.1 * math.sin(math.pi * k / 5)) for k, p in enumerate(path)]
        b.tube(path, lambda t: (max(0.01, 0.075 * math.sin(math.pi * (0.2 + 0.8 * t)) ** 0.7 * (1 - 0.25 * t)), 0.017 * (1 - 0.4 * t) + 0.004), lp, sides=6, cap_a=False)
        d = (path[-1] - path[-2]).normalized()
        b.blob(path[-1] + d * 0.012, 0.012, spine, amp=0.0, sub=2, squash=(0.6, 0.6, 1.6), rot=d.to_track_quat("Z", "Y"))


def a_herbe_pampa(b):
    r = b.rnd
    bl = grad("A", "lime", 0.0, 1.8)
    for i in range(20):
        a = i * 2.4 + r.uniform(-.2, .2)
        rad = r.uniform(0.0, 0.1)
        base = V(math.cos(a) * rad, math.sin(a) * rad, 0)
        L = r.uniform(1.0, 1.65)
        reach = r.uniform(0.55, 1.0)
        tipx = base + V(math.cos(a) * reach, math.sin(a) * reach, 0)
        nm = b.chain(f"lame{i + 1}", base, V(tipx.x, tipx.y, L * 0.7), 2, amp=1.1)
        path = []
        for k in range(9):
            t = k / 8
            path.append(V(base.x + (tipx.x - base.x) * t ** 2.1, base.y + (tipx.y - base.y) * t ** 2.1, L * (t - 0.42 * t * t) * 1.0))
        b.tube(path, leaf_profile(0.022, 0.003, 0.7, 0.3), bl, sides=4, part=nm)
    for i in range(5):
        a = i * 1.9 + 0.4
        rad = 0.07 + 0.06 * (i % 3)
        base = V(math.cos(a) * 0.03, math.sin(a) * 0.03, 0)
        H = r.uniform(1.65, 2.05)
        tip = V(math.cos(a) * rad + 0.1, math.sin(a) * rad, H)
        nm = b.chain(f"hampe{i + 1}", base, tip, 3, amp=1.0)
        path = arc(base, tip, 0.1, 8, V(math.cos(a), math.sin(a), 0))
        b.tube(path, [0.0045] * 8, grad("B", "green3", 0, 2.0), sides=4, part=nm)
        end = path[-1]
        d = (path[-1] - path[-2]).normalized()
        rot = d.to_track_quat("Z", "Y")
        b.blob(end - d * 0.16, (0.05, 0.05, 0.26), pal("ivory"), amp=0.18, sub=3, rot=rot, part=nm)
        b.blob(end - d * 0.26, (0.04, 0.04, 0.16), pal("beige"), amp=0.2, sub=2, rot=rot, part=nm, seed=3)
        b.blob(end - d * 0.04, (0.025, 0.025, 0.07), pal("cream"), amp=0.15, sub=2, rot=rot, part=nm, seed=5)


def a_mousse(b):
    r = b.rnd
    g = grad("B", "grass", 0.0, 0.2)
    g2 = grad("B", "green2", 0.0, 0.18)
    for i in range(16):
        a = r.uniform(0, 6.28)
        d = math.sqrt(r.random()) * 0.55
        R = r.uniform(0.1, 0.24)
        b.blob(V(math.cos(a) * d, math.sin(a) * d, 0.0), R, g if i % 2 else g2, amp=0.3, freq=2.4, squash=(1, 1, 0.5), seed=i, sub=2)
    for i in range(10):
        a = r.uniform(0, 6.28)
        d = math.sqrt(r.random()) * 0.5
        b.blob(V(math.cos(a) * d, math.sin(a) * d, 0.1), 0.04, pal("lime"), amp=0.2, sub=2, squash=(1, 1, 0.8), seed=i + 20)
