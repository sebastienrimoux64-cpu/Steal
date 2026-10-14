"""Briques communes aux assets : tiges, lames, têtes de fleurs."""
import math

from mathutils import Vector

from natlib import pal, grad, tex


def V(*a):
    return Vector(a) if len(a) > 1 else Vector(a[0])


def arc(base, tip, bend, n=6, bend_dir=None):
    """Courbe de base à tip, bombée de `bend` (m) dans la direction bend_dir (par défaut perpendiculaire en XY)."""
    base, tip = V(base), V(tip)
    d = tip - base
    if bend_dir is None:
        bend_dir = V(-d.y, d.x, 0)
        if bend_dir.length < 1e-6:
            bend_dir = V(1, 0, 0)
    bend_dir = V(bend_dir).normalized()
    return [base.lerp(tip, i / (n - 1)) + bend_dir * (bend * math.sin(math.pi * (i / (n - 1)) * 0.5) ** 2) for i in range(n)]


def leaf_profile(w, th, pw=0.8, start=0.12):
    """Largeur (rx) et épaisseur (ry) d'une lame/pétale : étroite à la base, large au milieu, pointue au bout."""
    return lambda t: (max(0.0015, w * math.sin(math.pi * min(1.0, start + (1 - start) * t)) ** pw), th)


def blade(b, base, tip, w, paint, bend=0.1, th=None, part=None, n=6, bend_dir=None, pw=0.8, start=0.12, sides=4):
    path = arc(base, tip, bend, b.n(n, 3), bend_dir)
    b.tube(path, leaf_profile(w, th if th is not None else w * 0.22, pw, start), paint, sides=sides, part=part, cap_a=False, cap_b=False if False else True)


def frame(d):
    d = V(d).normalized()
    ref = V(0, 0, 1) if abs(d.z) < 0.95 else V(1, 0, 0)
    u = ref.cross(d).normalized()
    v = d.cross(u).normalized()
    return d, u, v


def flower_head(b, pos, d, R, n_petals, petal_paint, center_paint, part=None, center_r=0.4, petal_len=1.0, w=0.28, cup=0.0, th=None, rot=0.0, center_h=0.55):
    """Fleur : disque central + pétales rayonnants dans le plan perpendiculaire à d (d = direction de face)."""
    pos = V(pos)
    d, u, v = frame(d)
    b.blob(pos + d * (R * center_r * 0.2), R * center_r, center_paint, amp=0.05, sub=2, squash=(1, 1, center_h), part=part, rot=None if False else d.to_track_quat("Z", "Y"))
    n_petals = b.n(n_petals, 4) if n_petals > 5 else n_petals
    for i in range(n_petals):
        a = rot + 2 * math.pi * i / n_petals
        rd = u * math.cos(a) + v * math.sin(a)
        base = pos + rd * (R * center_r * 0.7)
        tip = pos + rd * (R * (0.55 + 0.45 * petal_len)) + d * (R * cup)
        mid_bend = d * (R * cup * 0.3)
        path = [base.lerp(tip, k / 3) + mid_bend * math.sin(math.pi * k / 3) for k in range(4)]
        b.tube(path, leaf_profile(R * w, (th if th is not None else R * 0.05), 0.7, 0.2), petal_paint, sides=4, part=part)
