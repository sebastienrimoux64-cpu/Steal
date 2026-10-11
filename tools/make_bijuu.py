"""
Génère les 9 bijū (Shukaku -> Kurama) en VOXELS haute résolution, avec armature détaillée
(colonne, cou, mâchoire, langue, paupières, oreilles, pattes + doigts, queues à 10 os...),
poids de déformation doux aux articulations, animations "Idle" et "Walk",
puis exporte en .blend, .fbx et .glb.

Usage (Python avec le module bpy) :
    python tools/make_bijuu.py            # tout générer dans models/
    python tools/make_bijuu.py Kurama     # un seul bijū

Repère Blender : le bijū regarde vers -Y, le haut est +Z, côté gauche = +X (".L").
Échelle : 1 "stud" de conception = 0.75 m ; 1 voxel = 1/3 stud = 25 cm.
"""
import math
import os
import random
import sys
from types import SimpleNamespace as NS

import bpy
import bmesh  # noqa: F401  (chargé après bpy)
from mathutils import Vector

STUD = 0.75           # mètres par stud
Q = 1.0 / 3.0         # taille d'un voxel, en studs
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
LEVELS = (0.88, 0.94, 1.0, 1.07)  # variations de teinte (texture de pelage)


def v(x, y, z):
    """Vecteur de conception : x droite, y haut, z arrière (en studs)."""
    return Vector((x, y, z))


def rgb(r, g, b):
    return (r / 255, g / 255, b / 255)


WHITE = rgb(245, 243, 235)
BLACK = rgb(22, 22, 26)
CLAW = rgb(240, 235, 215)
PINK = rgb(225, 105, 125)


def sides(fn):
    fn(-1, "R")
    fn(1, "L")


def to_b(p):
    """conception (x, y haut, z arrière) -> axes Blender (x, y arrière, z haut), en studs."""
    return Vector((p.x, p.z, p.y))


def clamp01(x):
    return max(0.0, min(1.0, x))


def mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def shade(c, f):
    return tuple(min(1.0, x * f) for x in c)


# ----------------------------------------------------------------------------
# Fonctions de poids (déformation douce)
# ----------------------------------------------------------------------------
def chain(getv, boundaries, bones, bw):
    """Poids entre os consécutifs le long d'un axe. getv(pos) décroît le long de la chaîne ;
    boundaries[j] = valeur de la frontière entre bones[j] et bones[j+1] ; bw = demi-largeur de mélange."""
    def fn(pos):
        val = getv(pos)
        rest, out = 1.0, {}
        for j, b in enumerate(boundaries):
            f = clamp01((val - (b - bw)) / (2 * bw))
            if f > 0:
                out[bones[j]] = out.get(bones[j], 0) + rest * f
            rest *= 1 - f
            if rest <= 1e-4:
                break
        if rest > 1e-4:
            out[bones[len(boundaries)]] = out.get(bones[len(boundaries)], 0) + rest
        return tuple(out.items())
    return fn


def interp(stations, s):
    """stations = [(s, os), ...] triées : mélange linéaire entre os voisins."""
    if s <= stations[0][0]:
        return ((stations[0][1], 1.0),)
    for (s0, b0), (s1, b1) in zip(stations, stations[1:]):
        if s <= s1:
            f = (s - s0) / (s1 - s0)
            return ((b0, 1 - f), (b1, f))
    return ((stations[-1][1], 1.0),)


# ----------------------------------------------------------------------------
# Contexte de construction
# ----------------------------------------------------------------------------
class Ctx:
    def __init__(self, spec):
        self.spec = spec
        self.scale = spec.get("scale", 1)
        self.vox = {}    # (i,j,k) -> (couleur, kind, poids, fourrure?)
        self.bones = {}  # nom -> dict(head, parent, tail)
        self.order = []
        self.root = NS(bone="Root", bone_name="Root")
        self.bone("Root", None, v(0, 0, 0), v(0, 0, 3))
        self.rng = random.Random(spec["order"] * 7919)

    def bone(self, name, parent, head, tail=None):
        assert name not in self.bones, "os en double : " + name
        self.bones[name] = dict(head=head, parent=parent, tail=tail)
        self.order.append(name)
        return name

    def fill(self, center, size, color, bone, kind=None, n=8, jitter=True, fur=True):
        """Remplit de voxels une boîte (ou super-ellipsoïde si n<8) de centre/taille en studs."""
        cb = to_b(center)
        hb = Vector((max(size.x, Q) / 2, max(size.z, Q) / 2, max(size.y, Q) / 2))
        rng_ax = []
        for a in range(3):
            lo = math.ceil((cb[a] - hb[a]) / Q - 0.5 - 1e-6)
            hi = math.floor((cb[a] + hb[a]) / Q - 0.5 + 1e-6)
            if hi < lo:
                lo = hi = round(cb[a] / Q - 0.5)
            rng_ax.append((lo, hi))
        boxy = min(hi - lo + 1 for lo, hi in rng_ax) <= 2 or n >= 8
        static_w = None if callable(bone) else ((bone, 1.0),)
        for i in range(rng_ax[0][0], rng_ax[0][1] + 1):
            ux = ((i + 0.5) * Q - cb.x) / hb.x
            for j in range(rng_ax[1][0], rng_ax[1][1] + 1):
                uy = ((j + 0.5) * Q - cb.y) / hb.y
                for k in range(rng_ax[2][0], rng_ax[2][1] + 1):
                    uz = ((k + 0.5) * Q - cb.z) / hb.z
                    if not boxy and abs(ux) ** n + abs(uy) ** n + abs(uz) ** n > 1.0:
                        continue
                    lvl = LEVELS[((i * 73856093) ^ (j * 19349663) ^ (k * 83492791)) % 4] if jitter else 1.0
                    w = static_w or bone(Vector(((i + 0.5) * Q, (k + 0.5) * Q, (j + 0.5) * Q)))
                    self.vox[(i, j, k)] = (shade(color, lvl), kind, w, fur)

    def add(self, name, size, off, color, mat=None, parent=None, pivot=None, n=8, fur=False, tail=None):
        """Compatibilité : pièce statique (pivot=None) ou nouvel os (pivot donné)."""
        parent = parent or self.root
        k = self.scale
        pbone = getattr(parent, "bone_name", parent.bone)
        if pivot is not None:
            self.bone(name, pbone, pivot * k, tail * k if tail is not None else None)
            bone = name
        else:
            bone = parent.bone
        self.fill(off * k, size * k, color, bone, mat, n=n, fur=fur)
        return NS(name=name, bone=bone, bone_name=name if pivot is not None else pbone)

    def fur_pass(self, prob, pred):
        dirs = ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1))
        new = {}
        for (i, j, k), (col, kind, w, fur) in list(self.vox.items()):
            if not fur or kind:
                continue
            main = max(w, key=lambda t: t[1])[0]
            if not pred(main):
                continue
            for d in dirs:
                nb = (i + d[0], j + d[1], k + d[2])
                if nb in self.vox or nb in new:
                    continue
                if self.rng.random() < prob:
                    new[nb] = (shade(col, 1.1), kind, w, False)
        self.vox.update(new)


# ----------------------------------------------------------------------------
# Générateur de créature
# ----------------------------------------------------------------------------
def bezier(a, c, e, s):
    return a * ((1 - s) ** 2) + c * (2 * (1 - s) * s) + e * (s * s)


def build_tails(c, spec, g):
    n = spec.get("tails", 0)
    if n <= 0:
        return
    B, col = spec["body"], spec["colors"]
    tw, L = spec["tailW"], spec["tailLen"]
    rise = spec.get("tailRise", 0.7)
    wave = spec.get("tailWave", 0.0) * tw
    K = spec.get("tailBones", 10)
    fan = spec.get("fan") or (0.4 if n <= 3 else 0.34 if n <= 6 else 0.3)
    tip_frac = spec.get("tipSegs", 1) / spec.get("tailSegs", 6)
    mid = (n + 1) / 2
    for i in range(1, n + 1):
        t = i - mid
        yaw = t * fan
        x0 = max(-B.x / 2 + tw / 3, min(B.x / 2 - tw / 3, t * tw * 0.55))
        A = v(x0, g.baseY + (mid - abs(t)) * 0.12, g.rearZ - 0.6)
        d = v(math.sin(yaw), 0, math.cos(yaw))
        C = A + d * L * 0.5
        E = A + d * L * 0.78 + v(0, L * 0.6 * rise, 0)

        def P(s, A=A, C=C, E=E, i=i):
            p = bezier(A, C, E, s)
            p.x += math.sin(s * 6.9 + i * 1.3) * wave * s
            return p

        def rad(s, tw=tw):
            return tw / 2 * (0.6 + 0.5 * math.sin(math.pi * s ** 0.7)) * (1 - 0.55 * s ** 4)

        def colr(s, i=i):
            f = clamp01((s - (1 - tip_frac) + 0.12) / 0.2)
            f = round(f * 5) / 5
            tc = spec.get("tipCol") or col["tip"]
            return mix(col["tail"], tc, f)

        names = [f"Tail{i}_{k + 1}" for k in range(K)]
        for k in range(K):
            c.bone(names[k], "Spine1" if k == 0 else names[k - 1], P(k / K), P((k + 1) / K))
        stations = [((k + 0.5) / K, names[k]) for k in range(K)]
        kind_tail = spec.get("tailMat")
        tip_kind = spec.get("tipMat")

        steps = max(10, int(L / (Q * 0.45)))
        for st in range(steps + 1):
            s = st / steps
            kind = tip_kind if (tip_kind and s > 1 - tip_frac) else kind_tail
            c.fill(P(s), v(2 * max(rad(s), Q * 0.55), 2 * max(rad(s), Q * 0.55), 2 * max(rad(s), Q * 0.55)),
                   colr(s), _const(interp(stations, s)), kind, n=3, fur=True)


def _const(w):
    return lambda pos, w=w: w


def build_legs(c, spec, g):
    legH, legW = spec["legH"], spec["legW"]
    if legH <= 0 or spec.get("legs") is False:
        return
    B, col = spec["body"], spec["colors"]
    uh, lh, ph = legH * 0.45, legH * 0.40, max(legH * 0.15, 0.8)
    limb = col.get("limb", col["body"])
    paw_c = col.get("paw", limb)
    rows = (("Front", g.frontZ + legW * 0.95, "Spine3"), ("Back", g.rearZ - legW * 0.95, "Spine1"))
    for row, z, parent in rows:
        def leg(s, n, row=row, z=z, parent=parent):
            x = s * (B.x / 2 - legW * 0.6)
            tag = f"{row}Leg"
            up, lo, paw = f"{tag}_Upper.{n}", f"{tag}_Lower.{n}", f"{tag}_Paw.{n}"
            c.bone(up, parent, v(x, legH, z), v(x, legH - uh, z))
            c.bone(lo, up, v(x, legH - uh, z), v(x, ph, z))
            c.bone(paw, lo, v(x, ph, z), v(x, 0, z - legW * 0.8))
            wfn = chain(lambda p: p.y, [legH - uh, ph], [up, lo, paw], 0.55)
            thigh = 1.25 if row == "Back" else 1.0
            c.fill(v(x, legH - uh / 2 + 0.3, z), v(legW * 1.35 * thigh, uh + 0.9, legW * 1.5 * thigh), limb, wfn, n=5)
            c.fill(v(x, legH - uh - lh / 2, z), v(legW * 0.95, lh + 0.4, legW * 0.95), limb, wfn, n=6)
            c.fill(v(x, legH - uh - 0.2, z - legW * 0.5), v(legW * 1.0, 0.9, legW * 0.6), shade(limb, 1.07), wfn, n=8)  # genou/coude
            c.fill(v(x, ph / 2, z - legW * 0.25), v(legW * 1.2, ph, legW * 1.6), paw_c, wfn, n=6)
            for ti in range(1, 4):
                tx = x + (ti - 2) * legW * 0.38
                tz = z - legW * 0.25 - legW * 0.6
                tb = f"{tag}_Toe{ti}.{n}"
                c.bone(tb, paw, v(tx, ph * 0.55, tz), v(tx, ph * 0.3, tz - legW * 0.6))
                c.fill(v(tx, ph * 0.3, tz - legW * 0.1), v(legW * 0.32, ph * 0.6, legW * 0.7), paw_c, tb, n=8)
                c.fill(v(tx, ph * 0.22, tz - legW * 0.6), v(legW * 0.2, ph * 0.3, legW * 0.35), col.get("claw", CLAW), tb, n=8, fur=False)
                c.fill(v(tx, ph * 0.15, tz - legW * 0.85), v(legW * 0.13, ph * 0.18, legW * 0.2), col.get("claw", CLAW), tb, n=8, fur=False)
        sides(leg)


def build_quad(spec):
    c = Ctx(spec)
    col = spec["colors"]
    B, H = spec["body"], spec["head"]
    legH = spec["legH"]
    top = legH + B.y
    midY = legH + B.y / 2
    g = NS(B=B, H=H, legH=legH, bodyTop=top, frontZ=-B.z / 2, rearZ=B.z / 2,
           baseY=legH + B.y * spec.get("tailBaseY", 0.6), ears={})

    # --- colonne vertébrale ---
    c.bone("Spine1", "Root", v(0, midY, B.z * 0.3), v(0, midY, B.z * 0.05))
    c.bone("Spine2", "Spine1", v(0, midY, B.z * 0.05), v(0, midY, -B.z * 0.2))
    c.bone("Spine3", "Spine2", v(0, midY, -B.z * 0.2), v(0, midY, g.frontZ))
    spine = chain(lambda p: p.z, [B.z / 6, -B.z / 6], ["Spine1", "Spine2", "Spine3"], B.z / 6)
    g.body = NS(bone=spine, bone_name="Spine2")

    # --- jambes d'abord (le corps les recouvre), puis torse ---
    build_legs(c, spec, g)

    c.fill(v(0, midY, 0), B, col["body"], spine, n=6)
    c.fill(v(0, midY - B.y * 0.05, g.frontZ + B.z * 0.18), v(B.x * 1.06, B.y * 1.0, B.z * 0.4), shade(col["body"], 1.03), spine, n=5)  # poitrail
    c.fill(v(0, midY - B.y * 0.02, g.rearZ - B.z * 0.2), v(B.x * 1.04, B.y * 1.0, B.z * 0.38), shade(col["body"], 0.98), spine, n=5)  # hanches
    c.fill(v(0, legH + B.y * 0.17, 0), v(B.x * 1.02, B.y * 0.34, B.z * 0.96), col["belly"], spine, n=8)  # ventre
    c.fill(v(0, legH + B.y * 0.32, g.frontZ + 0.5), v(B.x * 0.62, B.y * 0.5, B.z * 0.22), col["belly"], spine, n=6)  # plastron

    if spec.get("bands"):
        bd = spec["bands"]
        for i in range(1, bd["count"] + 1):
            z = g.frontZ + B.z * i / (bd["count"] + 1)
            c.fill(v(0, midY, z), v(B.x * 1.04, B.y * 1.04, bd["thick"]), bd["color"], spine, n=8, fur=False)

    # crête dorsale
    rows = max(5, int(B.z / 1.6))
    for r in range(rows):
        z = g.frontZ + B.z * (r + 0.5) / rows
        c.fill(v(0, top + 0.25, z), v(B.x * 0.2, 0.9 + 0.5 * ((r + 1) % 2), 1.2), shade(col["body"], 1.12), spine, n=8)

    # --- cou en capsule (chaîne Spine3 > Neck1 > Neck2 > Head) ---
    N0 = v(0, legH + B.y * 0.62, g.frontZ + B.z * 0.12)
    hcy = legH + B.y * 0.8 + H.y * 0.3
    hcz = g.frontZ - H.z * 0.4
    N1 = v(0, hcy - H.y * 0.12, hcz + H.z * 0.32)
    g.headCY, g.headCZ, g.headTop = hcy, hcz, hcy + H.y / 2

    def NP(s):
        return N0 + (N1 - N0) * s

    c.bone("Neck1", "Spine3", NP(0.1), NP(0.5))
    c.bone("Neck2", "Neck1", NP(0.5), NP(1.0))
    c.bone("Head", "Neck2", NP(1.0), NP(1.0) + v(0, 0.0, -H.z * 0.8))
    stations = [(0.0, "Spine3"), (0.3, "Neck1"), (0.65, "Neck2"), (0.95, "Head")]
    nr = min(H.x, B.x) * 0.45
    steps = int(((N1 - N0).length) / (Q * 0.45)) + 4
    for st in range(steps + 1):
        s = st / steps
        c.fill(NP(s), v(2 * nr, 2 * nr * 1.1, 2 * nr), col["body"], _const(interp(stations, s)), n=4)
    g.neck = NS(bone="Neck2", bone_name="Neck2")

    # --- tête ---
    g.head = NS(bone="Head", bone_name="Head")
    c.fill(v(0, hcy, hcz), H, col["body"], "Head", n=6)
    c.fill(v(0, hcy + H.y * 0.36, hcz - H.z * 0.05), v(H.x * 0.96, H.y * 0.2, H.z * 0.9), shade(col["body"], 1.05), "Head", n=8)  # front
    c.fill(v(0, hcy + H.y * 0.2, hcz - H.z * 0.48), v(H.x * 0.98, H.y * 0.16, H.z * 0.1), shade(col["body"], 0.9), "Head", n=8)  # arcade sourcilière
    for s in (-1, 1):
        c.fill(v(s * H.x * 0.5, hcy - H.y * 0.2, hcz + H.z * 0.18), v(H.x * 0.26, H.y * 0.45, H.z * 0.5), shade(col["body"], 1.06), "Head", n=6)  # joues

    sl = spec["snout"]
    sw, sh = H.x * 0.52, H.y * 0.36
    sy = hcy - H.y * 0.18
    sz = hcz - H.z / 2 - sl / 2 + 0.3
    g.snoutY, g.snoutZ = sy, sz
    snout_c = col.get("snout", col["body"])
    c.fill(v(0, sy, sz), v(sw, sh, sl), snout_c, "Head", n=6)
    c.fill(v(0, sy + sh * 0.18, sz - sl * 0.2), v(sw * 0.6, sh * 0.5, sl * 0.7), shade(snout_c, 1.08), "Head", n=8)  # chanfrein
    c.fill(v(0, sy + sh / 2 - 0.1, sz - sl / 2 - 0.1), v(H.x * 0.22, H.y * 0.14, 0.5), col.get("nose", BLACK), "Head", n=8, fur=False)
    for s in (-1, 1):
        c.fill(v(s * H.x * 0.07, sy + sh * 0.1, sz - sl / 2 - 0.35), v(0.34, 0.34, 0.2), BLACK, "Head", n=8, fur=False)  # narines

    # mâchoire + langue + dents
    jw, jh, jl = H.x * 0.46, H.y * 0.15, sl * 0.95
    jy = sy - sh / 2 - jh / 2 + 0.02
    jz = sz + 0.2
    hinge = v(0, jy, jz + jl / 2)
    c.bone("Jaw", "Head", hinge, v(0, jy, jz - jl / 2))
    c.fill(v(0, jy, jz), v(jw, jh, jl), col.get("jaw", col["belly"]), "Jaw", n=6)
    c.fill(v(0, jy - jh * 0.45, jz - jl * 0.12), v(jw * 0.7, jh * 0.5, jl * 0.7), shade(col.get("jaw", col["belly"]), 0.92), "Jaw", n=8)
    c.bone("Tongue", "Jaw", hinge + v(0, 0.1, -0.2), v(0, jy + 0.1, jz - jl / 2 + 0.2))
    c.fill(v(0, jy + jh / 2 - 0.02, jz + 0.1), v(jw * 0.55, 0.34, jl * 0.8), PINK, "Tongue", n=8, fur=False)
    if spec.get("fangs") is not False:
        fw, fl = H.x * 0.06, H.y * 0.2
        rowsT = max(3, int(sl / 0.7))
        for s in (-1, 1):
            for r in range(rowsT):
                zt = sz + sl / 2 - 0.2 - r * (sl / rowsT)
                big = r == rowsT - 1
                c.fill(v(s * sw * 0.42, sy - sh / 2 - (fl if big else fl * 0.45) / 2 + 0.05, zt - (sl / rowsT) * 0.0),
                       v(fw, fl if big else fl * 0.45, fw), WHITE, "Head", n=8, fur=False)
                c.fill(v(s * jw * 0.4, jy + jh / 2 + (fl * 0.8 if big else fl * 0.4) / 2 - 0.05, zt + 0.2),
                       v(fw, fl * 0.8 if big else fl * 0.4, fw), WHITE, "Jaw", n=8, fur=False)

    # yeux + paupières
    ey, ez = hcy + H.y * 0.12, hcz - H.z / 2
    g.eyeY, g.eyeZ = ey, ez
    def eyes(s, n):
        ex = s * H.x * 0.3
        c.fill(v(ex, ey, ez - 0.05), v(H.x * 0.22, H.y * 0.16, 0.45), col["eye"], "Head", kind="neon", n=8, fur=False)
        c.fill(v(ex, ey, ez - 0.2), v(Q, H.y * 0.16, 0.25), BLACK, "Head", n=8, fur=False)
        lid = f"Eyelid.{n}"
        c.bone(lid, "Head", v(ex, ey + H.y * 0.09, ez), v(ex, ey - H.y * 0.05, ez))
        c.fill(v(ex, ey + H.y * 0.1, ez - 0.1), v(H.x * 0.26, H.y * 0.07, 0.5), shade(col["body"], 0.82), lid, n=8, fur=False)
        c.fill(v(ex, ey + H.y * 0.19, ez - 0.05), v(H.x * 0.3, H.y * 0.06, 0.45), col["accent"], "Head", n=8, fur=False)  # sourcil
    sides(eyes)

    # oreilles (2 os)
    style = spec.get("earStyle", "fox")
    if style in ("fox", "cat"):
        eh = H.y * (0.6 if style == "fox" else 0.36) * spec.get("earScale", 1)
        ew, ed = H.x * 0.28, H.x * 0.2
        def ears(s, n):
            ex, ezz = s * H.x * 0.32, hcz + H.z * 0.15
            base = g.headTop - 0.2
            c.bone(f"Ear1.{n}", "Head", v(ex, base, ezz), v(ex, base + eh * 0.5, ezz))
            c.bone(f"Ear2.{n}", f"Ear1.{n}", v(ex, base + eh * 0.5, ezz), v(ex, base + eh, ezz))
            # la chaîne doit décroître le long des os : on utilise -y (bas = Ear1, haut = Ear2)
            wfn_ear = chain(lambda p, b=base: -p.y, [-(base + eh * 0.5)], [f"Ear1.{n}", f"Ear2.{n}"], 0.4)
            steps_e = 5
            for k in range(steps_e):
                f0 = k / steps_e
                wd = ew * (1 - 0.7 * f0)
                dd = ed * (1 - 0.55 * f0)
                cy = base + eh * (f0 + 0.5 / steps_e)
                tipc = col.get("earTip")
                color = tipc if (tipc and f0 > 0.7) else col["body"]
                c.fill(v(ex, cy, ezz), v(wd, eh / steps_e + 0.1, dd), color, wfn_ear, n=8)
                inner = col.get("earIn", shade(col["belly"], 0.95))
                if 0 < k < steps_e - 1:
                    c.fill(v(ex, cy, ezz - dd * 0.4), v(wd * 0.5, eh / steps_e + 0.1, dd * 0.3), inner, wfn_ear, n=8, fur=False)
        sides(ears)
    elif style == "round":
        def ears(s, n):
            ex, ezz = s * H.x * 0.42, hcz + H.z * 0.1
            c.bone(f"Ear1.{n}", "Head", v(ex, g.headTop - 0.4, ezz), v(ex, g.headTop + 0.8, ezz))
            c.fill(v(ex, g.headTop - 0.1, ezz), v(H.x * 0.24, H.x * 0.24, H.x * 0.14), col["body"], f"Ear1.{n}", n=4)
            c.fill(v(ex, g.headTop - 0.1, ezz - 0.2), v(H.x * 0.12, H.x * 0.12, H.x * 0.06), shade(col["belly"], 0.9), f"Ear1.{n}", n=8, fur=False)
        sides(ears)

    build_tails(c, spec, g)
    if spec.get("extras"):
        spec["extras"](c, g)

    # pelage : touffes aléatoires sur le corps, les pattes et les queues
    furry = lambda b: b.startswith(("Spine", "Neck", "Tail", "FrontLeg_Upper", "BackLeg_Upper", "FrontLeg_Lower", "BackLeg_Lower"))
    c.fur_pass(spec.get("fur", 0.12), furry)
    c.fur_pass(0.05, lambda b: b.startswith("Tail"))
    return c


# ----------------------------------------------------------------------------
# Les 9 bijū
# ----------------------------------------------------------------------------
SPECS = {}

def extras_shukaku(c, g):
    H, B = g.H, g.B
    sides(lambda s, n: c.add(f"EyeRing.{n}", v(H.x * 0.32, H.y * 0.26, 0.3), v(s * H.x * 0.3, g.eyeY, g.eyeZ + 0.1), BLACK, None, g.head))
    for i, r in enumerate((0.2, 0.14, 0.08)):
        c.add(f"ForeheadSpiral{i}", v(H.x * (0.3 - i * 0.08), H.y * (0.3 - i * 0.08), 0.3), v(0, g.headTop - H.y * 0.2, g.eyeZ + 0.1 * i), rgb(40, 60, 170) if i % 2 == 0 else rgb(214, 186, 120), None, g.head)
    for i in range(1, 7):
        c.add(f"SandTuft{i}", v(2.2, 3, 2.2), v(((i % 2) * 2 - 1) * 1.5, g.bodyTop + 1.2, g.frontZ + B.z * i / 7), rgb(190, 160, 100), None, g.body)
    c.add("TailSwirl", v(3.6, 0.4, 3.6), v(0, g.baseY + 6, g.rearZ + 5), rgb(40, 60, 170), None, g.body)

SPECS["Shukaku"] = dict(
    name="Shukaku", order=1, body=v(12, 10, 16), legH=4, legW=3, head=v(9, 8, 8), snout=3, earStyle="round",
    colors=dict(body=rgb(214, 186, 120), belly=rgb(240, 225, 180), accent=rgb(40, 60, 170), eye=rgb(255, 230, 60),
                tail=rgb(214, 186, 120), tip=rgb(230, 205, 140)),
    bands=dict(count=5, color=rgb(40, 60, 170), thick=0.8),
    tails=1, tailSegs=5, tailW=4.2, tailLen=15, tailRise=0.8, extras=extras_shukaku)


def extras_matatabi(c, g):
    fc = rgb(80, 190, 255)
    for i in range(1, 8):
        c.add(f"BackFlame{i}", v(1.4, 2.5 + (i % 3) * 1.2, 1.4), v(0, g.bodyTop + 1.2, g.frontZ + g.B.z * i / 8), fc, "neon", g.body)
    def f(s, n):
        for k in range(3):
            c.add(f"LegFlame{k}.{n}", v(1.4, 2 + k, 1.4), v(s * (g.B.x / 2 + 0.4), 3.2 + k, g.rearZ - 1.8 - k * 1.2), fc, "neon", g.body)
        c.add(f"CheekFlame.{n}", v(1.2, 2.2, 1.2), v(s * (g.H.x / 2 + 0.7), g.headCY - 0.5, g.headCZ + 1), fc, "neon", g.head)
        c.add(f"AnkleFlame.{n}", v(1.6, 2, 1.6), v(s * (g.B.x / 2 - 1.2), 1.4, g.frontZ + 2), fc, "neon", g.body)
    sides(f)

SPECS["Matatabi"] = dict(
    name="Matatabi", order=2, body=v(8, 7, 13), legH=5, legW=2, head=v(7, 6.5, 6), snout=2, earStyle="cat",
    colors=dict(body=rgb(150, 195, 240), belly=rgb(240, 248, 255), accent=rgb(30, 50, 140), eye=rgb(120, 255, 255),
                tail=rgb(150, 195, 240), tip=rgb(80, 190, 255), earTip=rgb(30, 50, 140), paw=rgb(30, 50, 140)),
    tails=2, tailSegs=6, tailW=2.8, tailLen=19, tailRise=0.9, tipSegs=3, tipMat="neon", extras=extras_matatabi)


def extras_isobu(c, g):
    B = g.B
    shellC = rgb(140, 70, 60)
    plate = c.add("Shell", v(B.x * 1.0, 3.5, B.z * 0.95), v(0, g.bodyTop + 1.4, 0), shellC, None, g.body, n=4)
    c.add("ShellRim", v(B.x * 1.14, 1.5, B.z * 1.08), v(0, g.bodyTop + 0.2, 0), rgb(225, 205, 160), None, g.body, n=6)
    for ix in (-1, 0, 1):
        for iz in (-2, -1, 0, 1, 2):
            x, z = ix * B.x * 0.3, iz * B.z * 0.2
            c.add(f"ShellBase_{ix}_{iz}", v(2.8, 2.4, 2.8), v(x, g.bodyTop + 4.0, z), rgb(105, 50, 45), None, g.body, n=4)
            c.add(f"ShellSpike_{ix}_{iz}", v(1.5, 3.4, 1.5), v(x, g.bodyTop + 6.6, z), WHITE, None, g.body, n=4)
    sides(lambda s, n: c.add(f"EyeSpike.{n}", v(1.1, 2.0, 1.1), v(s * g.H.x * 0.3, g.headTop + 0.8, g.headCZ - 1), WHITE, None, g.head))

SPECS["Isobu"] = dict(
    name="Isobu", order=3, body=v(13, 6, 14), legH=3.5, legW=3.5, head=v(7, 6, 7), snout=2, earStyle="none", fangs=False,
    colors=dict(body=rgb(90, 120, 140), belly=rgb(225, 205, 160), accent=rgb(140, 70, 60), eye=rgb(255, 200, 70),
                tail=rgb(110, 140, 160), tip=rgb(210, 80, 70)),
    tails=3, tailSegs=4, tailW=2.8, tailLen=10, tailRise=0.5, tailBaseY=0.45, extras=extras_isobu)


def extras_songoku(c, g):
    white = rgb(245, 240, 230)
    for i in range(1, 5):
        c.add(f"Mane{i}", v(g.H.x * (1.35 - i * 0.1), 3, 2.6), v(0, g.headTop - i * 2.0, g.headCZ + g.H.z / 2 + 0.8), white, None, g.head, n=5, fur=True)
    for i in range(1, 5):
        c.add(f"BackMane{i}", v(g.B.x * 0.7, 2.5, 2.4), v(0, g.bodyTop + 0.6, g.frontZ + i * 2.2), white, None, g.body, n=5, fur=True)
    def f(s, n):
        hx = s * g.H.x * 0.3
        h1 = c.add(f"Horn1.{n}", v(1.6, 3.2, 1.6), v(hx, g.headTop + 1.2, g.headCZ - 0.5), white, None, g.head, v(hx, g.headTop - 0.2, g.headCZ - 0.5))
        h2 = c.add(f"Horn2.{n}", v(1.4, 2.8, 1.4), v(s * g.H.x * 0.42, g.headTop + 3.8, g.headCZ - 0.5), white, None, h1, v(hx, g.headTop + 2.6, g.headCZ - 0.5))
        c.add(f"Horn3.{n}", v(1.1, 2.2, 1.1), v(s * g.H.x * 0.54, g.headTop + 5.8, g.headCZ - 0.5), white, None, h2, v(s * g.H.x * 0.42, g.headTop + 5.0, g.headCZ - 0.5))
        c.add(f"ShoulderSpike{n}", v(2.2, 3.4, 2.2), v(s * (g.B.x / 2 + 0.7), g.bodyTop - 0.5, g.frontZ + 2.5), white, None, g.body)
        c.add(f"ChestHair.{n}", v(g.B.x * 0.3, 5, 0.9), v(s * g.B.x * 0.18, g.legH + g.B.y * 0.55, g.frontZ - 0.3), white, None, g.body)
    sides(f)

SPECS["SonGoku"] = dict(
    name="SonGoku", order=4, body=v(13, 12, 10), legH=6, legW=3.5, head=v(8, 8, 8), snout=3, earStyle="round",
    colors=dict(body=rgb(200, 60, 55), belly=rgb(240, 230, 210), accent=rgb(245, 240, 230), eye=rgb(255, 220, 70),
                tail=rgb(200, 60, 55), tip=rgb(245, 240, 230), snout=rgb(235, 210, 185)),
    tails=4, tailSegs=5, tailW=3.0, tailLen=15, tailRise=0.55, extras=extras_songoku)


def extras_kokuo(c, g):
    red = rgb(220, 60, 70)
    h1 = c.add("Horn1", v(1.8, 2.6, 1.8), v(0, g.headTop + 1, g.headCZ - 2), WHITE, None, g.head, v(0, g.headTop - 0.2, g.headCZ - 2))
    h2 = c.add("Horn2", v(1.4, 2.6, 1.4), v(0, g.headTop + 3.4, g.headCZ - 2.6), red, None, h1, v(0, g.headTop + 2.3, g.headCZ - 2))
    c.add("Horn3", v(0.9, 2.4, 0.9), v(0, g.headTop + 5.6, g.headCZ - 3.2), WHITE, None, h2, v(0, g.headTop + 4.6, g.headCZ - 2.6))
    for i in range(1, 10):
        c.add(f"Mane{i}", v(1.6, 2.4 + (i % 2), 2.2), v(0, g.bodyTop + 0.8 + (2 if i == 1 else 0), g.frontZ + (i - 1) * 1.9), red, None, g.body, n=5, fur=True)
    def f(s, n):
        c.add(f"EyeMark{n}", v(g.H.x * 0.15, g.H.y * 0.36, 0.3), v(s * g.H.x * 0.3, g.eyeY - g.H.y * 0.22, g.eyeZ + 0.1), red, None, g.head)
        c.add(f"Fin{n}", v(0.7, 3.4, 4.4), v(s * (g.B.x / 2 + 0.3), g.legH + g.B.y * 0.7, g.frontZ + 4), red, None, g.body)
        c.add(f"FlankMark{n}", v(0.4, 3.0, 3.0), v(s * (g.B.x / 2 + 0.1), g.legH + g.B.y * 0.5, 0), red, None, g.body)
    sides(f)

SPECS["Kokuo"] = dict(
    name="Kokuo", order=5, body=v(8, 8, 16), legH=7, legW=2.4, head=v(6, 7, 8), snout=4, earStyle="fox", earScale=0.8,
    colors=dict(body=rgb(240, 240, 245), belly=rgb(255, 255, 255), accent=rgb(220, 60, 70), eye=rgb(255, 70, 70),
                tail=rgb(240, 240, 245), tip=rgb(220, 60, 70), paw=rgb(220, 60, 70), earTip=rgb(220, 60, 70), nose=rgb(220, 60, 70)),
    tails=5, tailSegs=5, tailW=2.4, tailLen=15, tailRise=0.6, tipSegs=2, extras=extras_kokuo)


def extras_saiken(c, g):
    c.add("Foot", v(g.B.x * 1.14, 1.8, g.B.z * 1.06), v(0, 0.9, 0), rgb(185, 205, 235), None, g.body, n=6)
    def f(s, n):
        px = s * g.H.x * 0.28
        st = c.add(f"Antenna.{n}", v(1.0, 4.0, 1.0), v(px, g.headTop + 1.8, g.headCZ - 1), rgb(215, 230, 250), None, g.head, v(px, g.headTop - 0.1, g.headCZ - 1))
        c.add(f"AntennaBall.{n}", v(1.8, 1.8, 1.8), v(px, g.headTop + 4.2, g.headCZ - 1), rgb(110, 160, 230), "neon", st, n=4)
    sides(f)
    for i in range(1, 8):
        c.add(f"BackBump{i}", v(2.6, 1.8, 2.6), v(0, g.bodyTop + 0.7, g.frontZ + g.B.z * i / 8), rgb(110, 160, 230), None, g.body, n=5)

SPECS["Saiken"] = dict(
    name="Saiken", order=6, body=v(11, 9, 22), legH=0, legW=1, legs=False, head=v(8, 7, 7), snout=1.5, earStyle="none", fangs=False,
    colors=dict(body=rgb(225, 235, 250), belly=rgb(185, 205, 235), accent=rgb(110, 160, 230), eye=rgb(255, 190, 60),
                tail=rgb(215, 230, 250), tip=rgb(150, 200, 255)),
    bands=dict(count=8, color=rgb(190, 210, 240), thick=0.9),
    tails=6, tailSegs=6, tailW=2.6, tailLen=17, tailRise=0.5, tailWave=0.5, tailMat="glass", tipSegs=2, fur=0.02,
    extras=extras_saiken)


def extras_chomei(c, g):
    dark = rgb(30, 90, 60)
    h1 = c.add("Horn1", v(1.8, 2.2, 1.8), v(0, g.headTop + 0.6, g.headCZ - 1.5), dark, None, g.head, v(0, g.headTop - 0.2, g.headCZ - 1.5))
    h2 = c.add("Horn2", v(1.5, 2.0, 2.0), v(0, g.headTop + 2.1, g.headCZ - 3), dark, None, h1, v(0, g.headTop + 1.4, g.headCZ - 1.5))
    c.add("Horn3", v(1.1, 1.6, 2.2), v(0, g.headTop + 3.0, g.headCZ - 5), dark, None, h2, v(0, g.headTop + 2.5, g.headCZ - 3))
    def f(s, n):
        c.add(f"Elytron.{n}", v(g.B.x * 0.5, 1.4, g.B.z * 0.85), v(s * g.B.x * 0.26, g.bodyTop + 0.7, 0.5), dark, None, g.body, n=6)
        wing = c.add(f"Wing.{n}", v(8, 0.4, 16), v(s * (g.B.x * 0.35 + 4), g.bodyTop + 1.6, 1), rgb(200, 245, 215), "glass", g.body, v(s * g.B.x * 0.3, g.bodyTop + 1.4, -2))
        c.add(f"WingVein{n}", v(8, 0.5, 0.4), v(s * (g.B.x * 0.35 + 4), g.bodyTop + 1.7, 1), dark, None, wing)
        c.add(f"Antenna.{n}", v(0.7, 3.4, 0.7), v(s * g.H.x * 0.25, g.headTop + 1.4, g.headCZ - 2), dark, None, g.head, v(s * g.H.x * 0.25, g.headTop - 0.2, g.headCZ - 2))
    sides(f)

SPECS["Chomei"] = dict(
    name="Chomei", order=7, body=v(8, 7, 14), legH=5, legW=1.6, head=v(7, 6, 6), snout=1.5, earStyle="none",
    colors=dict(body=rgb(60, 160, 90), belly=rgb(200, 210, 120), accent=rgb(30, 90, 60), eye=rgb(255, 60, 60),
                tail=rgb(170, 230, 190), tip=rgb(100, 200, 140), limb=rgb(40, 120, 70)),
    tails=7, tailSegs=4, tailW=1.9, tailLen=10, tailRise=0.9, tailMat="glass", tipSegs=1, fur=0.03, extras=extras_chomei)


def extras_gyuki(c, g):
    horn = rgb(240, 235, 220)
    c.add("Hump", v(g.B.x * 0.85, 4.0, 7), v(0, g.bodyTop + 1.6, g.frontZ + 4), rgb(125, 55, 40), None, g.body, n=4, fur=True)
    def f(s, n):
        hx, hy, hz = s * g.H.x * 0.5, g.headTop - 1.2, g.headCZ
        h1 = c.add(f"Horn1.{n}", v(2.0, 2.0, 2.0), v(hx, hy, hz), horn, None, g.head, v(hx - s * 0.9, hy, hz))
        h2 = c.add(f"Horn2.{n}", v(1.8, 1.8, 1.8), v(s * (g.H.x * 0.5 + 2.0), hy, hz), horn, None, h1, v(hx, hy, hz))
        h3 = c.add(f"Horn3.{n}", v(1.6, 2.6, 1.6), v(s * (g.H.x * 0.5 + 3.5), g.headTop + 0.4, hz), horn, None, h2, v(s * (g.H.x * 0.5 + 2.0), hy, hz))
        c.add(f"Horn4.{n}", v(1.2, 2.4, 1.2), v(s * (g.H.x * 0.5 + 3.9), g.headTop + 2.6, hz), horn, None, h3, v(s * (g.H.x * 0.5 + 3.5), g.headTop + 1.2, hz))
    sides(f)
    c.add("NoseRing", v(2.6, 0.6, 0.6), v(0, g.snoutY - 1, g.snoutZ - 1.8), rgb(220, 190, 80), None, g.head)

SPECS["Gyuki"] = dict(
    name="Gyuki", order=8, body=v(13, 11, 17), legH=5, legW=3.4, head=v(9, 9, 9), snout=3.5, earStyle="cat",
    colors=dict(body=rgb(150, 70, 50), belly=rgb(230, 200, 170), accent=rgb(240, 235, 220), eye=rgb(255, 200, 60),
                tail=rgb(200, 140, 125), tip=rgb(235, 190, 170), snout=rgb(210, 160, 130)),
    tails=8, tailSegs=6, tailW=3.0, tailLen=22, tailRise=0.25, tailWave=0.9, tailBaseY=0.45, tipSegs=1, fan=0.2,
    extras=extras_gyuki)


def extras_kurama(c, g):
    H = g.H
    def f(s, n):
        c.add(f"EyeStreak{n}", v(H.x * 0.13, H.y * 0.44, 0.3), v(s * H.x * 0.3, g.eyeY - H.y * 0.28, g.eyeZ + 0.1), BLACK, None, g.head)
        c.add(f"CheekFur{n}", v(1.8, H.y * 0.38, 2.6), v(s * (H.x / 2 + 0.7), g.headCY - H.y * 0.2, g.headCZ + 1), rgb(255, 150, 30), None, g.head, n=5, fur=True)
        c.add(f"CheekFur2{n}", v(1.4, H.y * 0.3, 2.2), v(s * (H.x / 2 + 1.5), g.headCY - H.y * 0.3, g.headCZ + 2.2), rgb(255, 235, 205), None, g.head, n=5, fur=True)
        for i in range(1, 4):
            wb = c.add(f"Whisker{i}.{n}", v(2.6, 0.3, 0.3), v(s * (H.x / 2 + 1.8), g.headCY - H.y * 0.25 - (i - 2) * 0.7, g.headCZ - H.z / 2 + 1.2), BLACK, None, g.head,
                       v(s * (H.x / 2 + 0.5), g.headCY - H.y * 0.25 - (i - 2) * 0.7, g.headCZ - H.z / 2 + 1.2))
        c.add(f"ShoulderMark{n}", v(0.4, 2.8, 2.8), v(s * (g.B.x / 2 + 0.05), g.bodyTop - 2.4, g.frontZ + 2.5), BLACK, None, g.body)
        c.add(f"HipMark{n}", v(0.4, 2.6, 2.6), v(s * (g.B.x / 2 + 0.05), g.bodyTop - 2.4, g.rearZ - 2.5), BLACK, None, g.body)
        for k in range(3):
            c.add(f"ChestFur{k}.{n}", v(1.6, 1.2, 1.4), v(s * 1.0, g.legH + g.B.y * 0.4 - k * 1.2, g.frontZ - 0.5), rgb(255, 240, 215), None, g.body, n=5, fur=True)
    sides(f)
    c.add("ForeheadMark", v(1.4, 2.0, 0.4), v(0, g.headTop - 1.1, g.eyeZ + 0.1), BLACK, None, g.head)
    for k in range(4):
        c.add(f"Ruff{k}", v(g.H.x * (1.25 - 0.1 * k), 2.6, 2.4), v(0, g.legH + g.B.y * 0.7 - k * 1.7, g.headCZ + g.H.z / 2 + 1.0), rgb(255, 150, 30), None, g.head, n=5, fur=True)

SPECS["Kurama"] = dict(
    name="Kurama", order=9, body=v(9, 8, 14), legH=6, legW=2.4, head=v(7.5, 7, 7), snout=3.5, earStyle="fox",
    colors=dict(body=rgb(255, 140, 20), belly=rgb(255, 240, 215), accent=BLACK, eye=rgb(255, 20, 20),
                tail=rgb(255, 140, 20), tip=rgb(255, 235, 205), earTip=BLACK, paw=BLACK),
    tails=9, tailSegs=6, tailW=3.4, tailLen=20, tailRise=0.6, tipSegs=1, extras=extras_kurama)

NAMES = sorted(SPECS, key=lambda n: SPECS[n]["order"])


# ----------------------------------------------------------------------------
# Conversion vers Blender : mesh unique + armature + matériaux + animations
# ----------------------------------------------------------------------------
_MATS = {}

def srgb_to_lin(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def get_material(color, kind):
    key = (color, kind)
    if key in _MATS:
        return _MATS[key]
    name = f"{kind or 'mat'}_{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}"
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    lin = tuple(srgb_to_lin(x) for x in color) + (1.0,)
    bsdf.inputs["Base Color"].default_value = lin
    bsdf.inputs["Roughness"].default_value = 0.9
    mat.diffuse_color = lin
    if kind == "neon":
        bsdf.inputs["Emission Color"].default_value = lin
        bsdf.inputs["Emission Strength"].default_value = 3.0
    elif kind == "glass":
        bsdf.inputs["Alpha"].default_value = 0.65
        mat.diffuse_color = lin[:3] + (0.65,)
        if hasattr(mat, "surface_render_method"):
            mat.surface_render_method = "BLENDED"
    _MATS[key] = mat
    return mat


QUADS = {
    (1, 0, 0): ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
    (-1, 0, 0): ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
    (0, 1, 0): ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    (0, -1, 0): ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
    (0, 0, 1): ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    (0, 0, -1): ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
}


def quantize_weights(w):
    """poids arrondis à 0.05 près, somme = 1."""
    w = [(b, wt) for b, wt in w if wt > 0.02]
    tot = sum(wt for _, wt in w)
    q = [(b, round(wt / tot * 20) / 20) for b, wt in w]
    q = [(b, wt) for b, wt in q if wt > 0]
    s = sum(wt for _, wt in q)
    if abs(s - 1) > 1e-6 and q:
        i = max(range(len(q)), key=lambda k: q[k][1])
        q[i] = (q[i][0], q[i][1] + (1 - s))
    return q


def make_object(ctx, origin=Vector((0, 0, 0))):
    name = ctx.spec["name"]
    verts, faces, face_mat = [], [], []
    mats, mat_index = [], {}
    groups = {}  # (os, poids) -> [indices de sommets]
    m = Q * STUD
    for (i, j, k), (color, kind, w, _fur) in ctx.vox.items():
        key = ((round(color[0], 3), round(color[1], 3), round(color[2], 3)), kind)
        if key not in mat_index:
            mat_index[key] = len(mats)
            mats.append(get_material(*key))
        qw = None
        for d, quad in QUADS.items():
            if (i + d[0], j + d[1], k + d[2]) in ctx.vox:
                continue
            if qw is None:
                qw = quantize_weights(w)
            base = len(verts)
            for (a, b, cc) in quad:
                verts.append(((i + a) * m + origin.x, (j + b) * m + origin.y, (k + cc) * m + origin.z))
            faces.append((base, base + 1, base + 2, base + 3))
            face_mat.append(mat_index[key])
            for bn, wt in qw:
                groups.setdefault((bn, wt), []).extend((base, base + 1, base + 2, base + 3))

    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for mt in mats:
        mesh.materials.append(mt)
    mesh.polygons.foreach_set("material_index", face_mat)
    obj = bpy.data.objects.new(name + "_Mesh", mesh)
    bpy.context.scene.collection.objects.link(obj)

    # --- armature ---
    arm_data = bpy.data.armatures.new(name + "_Armature")
    arm = bpy.data.objects.new(name + "_Rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    children = {}
    for bn, b in ctx.bones.items():
        if b["parent"]:
            children.setdefault(b["parent"], []).append(bn)
    ebs = {}
    for bn in ctx.order:
        b = ctx.bones[bn]
        eb = arm_data.edit_bones.new(bn)
        head = to_b(b["head"]) * STUD + origin
        if b["tail"] is not None:
            tail = to_b(b["tail"]) * STUD + origin
        elif bn in children:
            tail = to_b(ctx.bones[children[bn][0]]["head"]) * STUD + origin
        else:
            tail = head + Vector((0, 0, 0.45))
        if (tail - head).length < 0.08:
            tail = head + Vector((0, 0, 0.3))
        eb.head, eb.tail = head, tail
        ebs[bn] = eb
    for bn, b in ctx.bones.items():
        if b["parent"]:
            ebs[bn].parent = ebs[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_data.display_type = "STICK"

    vgs = {bn: obj.vertex_groups.new(name=bn) for bn in ctx.order}
    for (bn, wt), idxs in groups.items():
        vgs[bn].add(idxs, wt, "ADD")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm
    return obj, arm


def make_actions(arm, ctx):
    pose = arm.pose.bones
    for pb in pose:
        pb.rotation_mode = "XYZ"
    arm.animation_data_create()

    jaw_sign = 1.0
    if "Jaw" in pose:
        pb = pose["Jaw"]
        rest = pb.tail.z
        pb.rotation_euler = (0.3, 0, 0)
        bpy.context.view_layer.update()
        jaw_sign = 1.0 if pb.tail.z < rest else -1.0
        pb.rotation_euler = (0, 0, 0)

    def reset():
        for pb in pose:
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)

    def key_all(frame):
        for pb in pose:
            pb.keyframe_insert("rotation_euler", frame=frame)
        for n in ("Root", "Spine1"):
            if n in pose:
                pose[n].keyframe_insert("location", frame=frame)

    tails = []
    for n in ctx.bones:
        if n.startswith("Tail"):
            a, b = n[4:].split("_")
            tails.append((n, int(a), int(b)))
    legs = [n for n in ctx.bones if "Leg_" in n]

    # ---- Idle (60 images, boucle) ----
    action = bpy.data.actions.new("Idle")
    action.use_fake_user = True
    arm.animation_data.action = action
    for frame in (1, 16, 31, 46, 61):
        reset()
        ph = (frame - 1) / 60 * 2 * math.pi
        pose["Spine1"].location = (0, 0, math.sin(ph) * 0.05)
        for nm, amp in (("Spine2", 0.02), ("Spine3", 0.03), ("Neck1", 0.03), ("Neck2", 0.03)):
            if nm in pose:
                pose[nm].rotation_euler = (math.sin(ph) * amp, 0, 0)
        pose["Head"].rotation_euler = (math.sin(ph + 0.6) * 0.04, 0, math.sin(ph) * 0.08)
        if "Jaw" in pose:
            pose["Jaw"].rotation_euler = (jaw_sign * (0.05 + 0.04 * math.sin(ph)), 0, 0)
        for n in pose.keys():
            if n.startswith("Ear"):
                pose[n].rotation_euler = (0, 0, math.sin(ph * 2 + (1 if n.endswith("L") else 0)) * 0.05)
            if n.startswith("Eyelid") and frame == 31:
                pose[n].rotation_euler = (0.9, 0, 0)
        for n, i, k in tails:
            pose[n].rotation_euler = (math.sin(ph - k * 0.45 + i) * 0.04, 0, math.sin(ph - k * 0.45 + i * 0.7) * (0.06 + 0.012 * k))
        key_all(frame)

    # ---- Walk (40 images, boucle) ----
    walk = bpy.data.actions.new("Walk")
    walk.use_fake_user = True
    arm.animation_data.action = walk
    for frame in (1, 11, 21, 31, 41):
        reset()
        ph = (frame - 1) / 40 * 2 * math.pi
        for n in legs:
            diag = 0.0 if (("Front" in n) == n.endswith(".L")) else math.pi
            if "Upper" in n:
                pose[n].rotation_euler = (math.sin(ph + diag) * 0.5, 0, 0)
            elif "Lower" in n:
                pose[n].rotation_euler = (max(0.0, -math.cos(ph + diag)) * 0.6, 0, 0)
            elif "Paw" in n:
                pose[n].rotation_euler = (-max(0.0, -math.cos(ph + diag)) * 0.3, 0, 0)
        pose["Spine1"].location = (0, 0, abs(math.sin(ph)) * 0.08)
        pose["Spine2"].rotation_euler = (0, 0, math.sin(ph) * 0.03)
        pose["Head"].rotation_euler = (math.sin(ph * 2) * 0.03, 0, 0)
        for n, i, k in tails:
            pose[n].rotation_euler = (0, 0, math.sin(ph - k * 0.55 + i * 0.7) * (0.07 + 0.012 * k))
        key_all(frame)

    reset()
    arm.animation_data.action = action
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, 61


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    _MATS.clear()


def export_all(name, arm, obj):
    os.makedirs(OUT, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"))
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"{name}.fbx"), use_selection=True,
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True,
                                 bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.0,
                                 apply_scale_options="FBX_SCALE_ALL")
    except Exception as e:
        print("FBX export échoué :", e)
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"{name}.glb"), export_format="GLB", use_selection=True,
                                  export_animations=True, export_animation_mode="ACTIONS", export_yup=True)
    except Exception as e:
        print("GLB export échoué :", e)


def build_one(name):
    reset_scene()
    ctx = build_quad(SPECS[name])
    obj, arm = make_object(ctx)
    make_actions(arm, ctx)
    export_all(name, arm, obj)
    print(f"{name}: {len(ctx.vox)} voxels, {len(obj.data.polygons)} faces, {len(ctx.bones)} os")


def build_all_in_one():
    reset_scene()
    for i, name in enumerate(NAMES):
        ctx = build_quad(SPECS[name])
        obj, arm = make_object(ctx, origin=Vector(((i - 4) * 28.0, 0, 0)))
        make_actions(arm, ctx)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Bijuu_Tous.blend"))


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in SPECS] or NAMES
    for n in wanted:
        build_one(n)
    if len(wanted) == len(NAMES):
        build_all_in_one()
