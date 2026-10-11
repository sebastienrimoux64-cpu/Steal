"""
Génère les 9 bijū (Shukaku -> Kurama) en cubes, avec armature (squelette) complète,
animations "Idle" et "Walk", puis exporte en .blend, .fbx et .glb.

Usage (Python avec le module bpy) :
    python tools/make_bijuu.py            # tout générer dans models/
    python tools/make_bijuu.py Kurama     # un seul bijū

Repère Blender : le bijū regarde vers -Y, le haut est +Z, côté gauche = +X (".L").
Unité : 1 stud Roblox = 0.25 m.
"""
import math
import os
import sys
from types import SimpleNamespace as NS

import bpy
import bmesh
from mathutils import Vector

S = 0.25  # mètres par unité
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


def v(x, y, z):
    """Vecteur dans le repère de conception (x droite, y haut, z arrière) ; converti à l'export."""
    return Vector((x, y, z))


def rgb(r, g, b):
    return (r / 255, g / 255, b / 255)


WHITE = rgb(245, 243, 235)
BLACK = rgb(22, 22, 26)
CLAW = rgb(240, 235, 215)


def sides(fn):
    fn(-1, "R")
    fn(1, "L")


# ----------------------------------------------------------------------------
# Construction de la géométrie (liste de cubes + hiérarchie d'os)
# ----------------------------------------------------------------------------
class Part:
    def __init__(self, name, size, off, color, mat, bone):
        self.name, self.size, self.off, self.color, self.mat, self.bone = name, size, off, color, mat, bone


class Ctx:
    def __init__(self, spec):
        self.spec = spec
        self.scale = spec.get("scale", 1)
        self.parts = []
        self.bones = {}  # nom -> dict(head, parent, part)
        self.root = Part("Root", v(0, 0, 0), v(0, 0, 0), BLACK, None, "Root")
        self.bones["Root"] = dict(head=v(0, 0, 0), parent=None, part=None)

    def add(self, name, size, off, color, mat=None, parent=None, pivot=None):
        parent = parent or self.root
        k = self.scale
        p = Part(name, size * k, off * k, color, mat, parent.bone)
        if pivot is not None:
            assert name not in self.bones, "os en double : " + name
            self.bones[name] = dict(head=pivot * k, parent=parent.bone, part=p)
            p.bone = name
        self.parts.append(p)
        return p


def build_tails(c, spec, g):
    n = spec.get("tails", 0)
    if n <= 0:
        return
    B = spec["body"]
    tw, segs = spec["tailW"], spec["tailSegs"]
    ls = spec["tailLen"] / segs
    rise = spec.get("tailRise", 0.7) * tw
    spread = spec.get("tailSpread", 0.4) * tw
    wave = spec.get("tailWave", 0) * tw
    tip_segs = spec.get("tipSegs", 1)
    mid = (n + 1) / 2
    col = spec["colors"]
    for i in range(1, n + 1):
        t = i - mid
        x0 = max(-B.x / 2 + tw / 2, min(B.x / 2 - tw / 2, t * tw * 0.55))
        a = v(x0, g.baseY, g.rearZ - 0.3)
        parent = g.body
        for k in range(1, segs + 1):
            w = tw * (0.6 + 0.5 * math.sin(math.pi * k / (segs + 1)))
            # décalages bornés pour que les cubes consécutifs se chevauchent (queue continue)
            lim = 0.6 * w
            dx = max(-lim, min(lim, t * spread + math.sin(k * 1.1 + i) * wave))
            dy = min(lim, rise + (mid - abs(t)) * 0.08 * tw)
            step = v(dx, dy, ls)
            is_tip = k > segs - tip_segs
            parent = c.add(
                f"Tail{i}_{k}", v(w, w, ls * 1.35), a + step / 2,
                col["tip"] if is_tip else col["tail"],
                spec.get("tipMat") if is_tip and spec.get("tipMat") else spec.get("tailMat"),
                parent, a,
            )
            a = a + step


def build_legs(c, spec, g):
    legH, legW = spec["legH"], spec["legW"]
    if legH <= 0 or spec.get("legs") is False:
        return
    B, col = spec["body"], spec["colors"]
    uh, lh, ph = legH * 0.45, legH * 0.40, legH * 0.15
    limb = col.get("limb", col["body"])
    paw_c = col.get("paw", limb)
    for row, z in (("Front", g.frontZ + legW * 0.9), ("Back", g.rearZ - legW * 0.9)):
        def leg(s, n, row=row, z=z):
            x = s * (B.x / 2 - legW * 0.55)
            tag = f"{row}Leg_"
            up = c.add(f"{tag}Upper.{n}", v(legW * 1.15, uh + 0.4, legW * 1.3), v(x, legH - uh / 2 + 0.2, z), limb, None, g.body, v(x, legH, z))
            lo = c.add(f"{tag}Lower.{n}", v(legW, lh, legW), v(x, legH - uh - lh / 2, z), limb, None, up, v(x, legH - uh, z))
            paw = c.add(f"{tag}Paw.{n}", v(legW * 1.1, ph, legW * 1.5), v(x, ph / 2, z - legW * 0.2), paw_c, None, lo, v(x, ph, z))
            for i in range(1, 4):
                c.add(f"{tag}Claw{i}.{n}", v(legW * 0.2, ph * 0.5, legW * 0.28),
                      v(x + (i - 2) * legW * 0.32, ph * 0.3, z - legW * 0.2 - legW * 0.8), col.get("claw", CLAW), None, paw)
        sides(leg)


def build_quad(spec):
    c = Ctx(spec)
    col = spec["colors"]
    B, H = spec["body"], spec["head"]
    legH = spec["legH"]
    top = legH + B.y
    g = NS(B=B, H=H, legH=legH, bodyTop=top, frontZ=-B.z / 2, rearZ=B.z / 2,
           baseY=legH + B.y * spec.get("tailBaseY", 0.6), ears={})

    body = c.add("Body", B, v(0, legH + B.y / 2, 0), col["body"], None, c.root, v(0, legH + B.y / 2, 0))
    g.body = body
    c.add("Belly", v(B.x * 1.02, B.y * 0.35, B.z * 0.92), v(0, legH + B.y * 0.175 - 0.03, 0), col["belly"], None, body)

    if spec.get("bands"):
        bd = spec["bands"]
        for i in range(1, bd["count"] + 1):
            z = g.frontZ + B.z * i / (bd["count"] + 1)
            c.add(f"Band{i}", v(B.x * 1.03, B.y * 1.03, bd["thick"]), v(0, legH + B.y / 2, z), bd["color"], None, body)

    neck_pivot = v(0, legH + B.y * 0.65, g.frontZ)
    neck = c.add("Neck", v(H.x * 0.8, B.y * 0.7, H.z * 0.5), v(0, legH + B.y * 0.65, g.frontZ - H.z * 0.1), col["body"], None, body, neck_pivot)
    g.neck = neck

    hcy = legH + B.y * 0.8 + H.y * 0.3
    hcz = g.frontZ - H.z * 0.4
    g.headCY, g.headCZ, g.headTop = hcy, hcz, hcy + H.y / 2
    head = c.add("Head", H, v(0, hcy, hcz), col["body"], None, neck, neck_pivot)
    g.head = head

    sl = spec["snout"]
    sw, sh = H.x * 0.5, H.y * 0.38
    sy = hcy - H.y * 0.18
    sz = hcz - H.z / 2 - sl / 2 + 0.2
    g.snoutY, g.snoutZ = sy, sz
    c.add("Snout", v(sw, sh, sl), v(0, sy, sz), col.get("snout", col["body"]), None, head)
    c.add("Nose", v(H.x * 0.2, H.y * 0.15, 0.5), v(0, sy + sh / 2 - 0.1, sz - sl / 2 - 0.1), col.get("nose", BLACK), None, head)

    jw, jh, jl = H.x * 0.44, H.y * 0.14, sl * 0.9
    jy = sy - sh / 2 - jh / 2 + 0.02
    jz = sz + 0.1
    jaw = c.add("Jaw", v(jw, jh, jl), v(0, jy, jz), col.get("jaw", col["belly"]), None, head, v(0, jy, jz + jl / 2))
    g.jaw = jaw

    if spec.get("fangs") is not False:
        fw, fl = H.x * 0.07, H.y * 0.22
        def fangs(s, n):
            c.add(f"UpperFang.{n}", v(fw, fl, fw), v(s * sw * 0.38, sy - sh / 2 - fl / 2 + 0.05, sz - sl / 2 + fw), WHITE, None, head)
            c.add(f"LowerFang.{n}", v(fw, fl * 0.8, fw), v(s * jw * 0.38, jy + jh / 2 + fl * 0.4 - 0.05, jz - jl / 2 + fw), WHITE, None, jaw)
        sides(fangs)

    ey, ez = hcy + H.y * 0.12, hcz - H.z / 2
    g.eyeY, g.eyeZ = ey, ez
    def eyes(s, n):
        c.add(f"Eye.{n}", v(H.x * 0.2, H.y * 0.13, 0.3), v(s * H.x * 0.3, ey, ez - 0.05), col["eye"], "neon", head)
        c.add(f"Pupil.{n}", v(H.x * 0.05, H.y * 0.14, 0.35), v(s * H.x * 0.3, ey, ez - 0.08), BLACK, None, head)
        c.add(f"Brow.{n}", v(H.x * 0.26, H.y * 0.06, 0.4), v(s * H.x * 0.3, ey + H.y * 0.11, ez - 0.02), col["accent"], None, head)
    sides(eyes)

    style = spec.get("earStyle", "fox")
    if style in ("fox", "cat"):
        eh = H.y * (0.55 if style == "fox" else 0.33) * spec.get("earScale", 1)
        ew, ed = H.x * 0.28, H.x * 0.2
        def ears(s, n):
            ex, eyy, ezz = s * H.x * 0.32, g.headTop + eh / 2 - 0.1, hcz + H.z * 0.15
            e = c.add(f"Ear.{n}", v(ew, eh, ed), v(ex, eyy, ezz), col["body"], None, head, v(ex, eyy - eh / 2, ezz))
            g.ears[n] = e
            if col.get("earTip"):
                c.add(f"EarTip.{n}", v(ew * 1.04, eh * 0.3, ed * 1.04), v(ex, eyy + eh * 0.35, ezz), col["earTip"], None, e)
        sides(ears)
    elif style == "round":
        def ears(s, n):
            c.add(f"Ear.{n}", v(H.x * 0.2, H.x * 0.2, H.x * 0.12), v(s * H.x * 0.42, g.headTop - 0.2, hcz + H.z * 0.1), col["body"], None, head, v(s * H.x * 0.42, g.headTop - 0.2, hcz + H.z * 0.1))
        sides(ears)

    build_legs(c, spec, g)
    build_tails(c, spec, g)
    if spec.get("extras"):
        spec["extras"](c, g)
    return c


# ----------------------------------------------------------------------------
# Les 9 bijū
# ----------------------------------------------------------------------------
SPECS = {}

def extras_shukaku(c, g):
    H, B = g.H, g.B
    sides(lambda s, n: c.add(f"EyeRing.{n}", v(H.x * 0.3, H.y * 0.22, 0.25), v(s * H.x * 0.3, g.eyeY, g.eyeZ + 0.05), BLACK, None, g.head))
    c.add("ForeheadMark", v(H.x * 0.18, H.y * 0.22, 0.3), v(0, g.headTop - H.y * 0.2, g.eyeZ), rgb(40, 60, 170), None, g.head)
    for i in range(1, 6):
        c.add(f"SandTuft{i}", v(2, 2.5, 2), v(((i % 2) * 2 - 1) * 1.2, g.bodyTop + 1, g.frontZ + B.z * i / 6), rgb(190, 160, 100), None, g.body)

SPECS["Shukaku"] = dict(
    name="Shukaku", order=1, body=v(12, 10, 16), legH=4, legW=3, head=v(9, 8, 8), snout=3, earStyle="round",
    colors=dict(body=rgb(214, 186, 120), belly=rgb(240, 225, 180), accent=rgb(40, 60, 170), eye=rgb(255, 230, 60),
                tail=rgb(214, 186, 120), tip=rgb(230, 205, 140)),
    bands=dict(count=5, color=rgb(40, 60, 170), thick=0.8),
    tails=1, tailSegs=5, tailW=3.6, tailLen=14, tailRise=0.8, extras=extras_shukaku)


def extras_matatabi(c, g):
    fc = rgb(80, 190, 255)
    for i in range(1, 6):
        c.add(f"BackFlame{i}", v(1.2, 2.5 + (i % 2) * 1.2, 1.2), v(0, g.bodyTop + 1, g.frontZ + g.B.z * i / 6), fc, "neon", g.body)
    def f(s, n):
        c.add(f"LegFlame.{n}", v(1.4, 2, 1.4), v(s * (g.B.x / 2 + 0.4), 3.2, g.rearZ - 1.8), fc, "neon", g.body)
        c.add(f"CheekFlame.{n}", v(1.2, 2, 1.2), v(s * (g.H.x / 2 + 0.6), g.headCY - 0.5, g.headCZ + 1), fc, "neon", g.head)
    sides(f)

SPECS["Matatabi"] = dict(
    name="Matatabi", order=2, body=v(8, 7, 13), legH=5, legW=2, head=v(7, 6.5, 6), snout=2, earStyle="cat",
    colors=dict(body=rgb(150, 195, 240), belly=rgb(240, 248, 255), accent=rgb(30, 50, 140), eye=rgb(120, 255, 255),
                tail=rgb(150, 195, 240), tip=rgb(80, 190, 255), earTip=rgb(30, 50, 140), paw=rgb(30, 50, 140)),
    tails=2, tailSegs=6, tailW=2.4, tailLen=18, tailRise=0.9, tailSpread=0.8, tipSegs=3, tipMat="neon",
    extras=extras_matatabi)


def extras_isobu(c, g):
    B = g.B
    plate = c.add("Shell", v(B.x * 0.95, 3, B.z * 0.9), v(0, g.bodyTop + 1.2, 0), rgb(140, 70, 60), None, g.body)
    c.add("ShellRim", v(B.x * 1.1, 1.4, B.z * 1.05), v(0, g.bodyTop + 0.2, 0), rgb(225, 205, 160), None, plate)
    for ix in (-1, 0, 1):
        for iz in (-1, 0, 1):
            x, z = ix * B.x * 0.28, iz * B.z * 0.27
            base = c.add(f"ShellSpikeBase_{ix}_{iz}", v(2.6, 2.2, 2.6), v(x, g.bodyTop + 3.7, z), rgb(105, 50, 45), None, plate)
            c.add(f"ShellSpikeTip_{ix}_{iz}", v(1.2, 2.4, 1.2), v(x, g.bodyTop + 5.8, z), WHITE, None, base)
    sides(lambda s, n: c.add(f"EyeSpike.{n}", v(0.9, 1.6, 0.9), v(s * g.H.x * 0.3, g.headTop + 0.6, g.headCZ - 1), WHITE, None, g.head))

SPECS["Isobu"] = dict(
    name="Isobu", order=3, body=v(13, 6, 14), legH=3.5, legW=3.5, head=v(7, 6, 7), snout=2, earStyle="none", fangs=False,
    colors=dict(body=rgb(90, 120, 140), belly=rgb(225, 205, 160), accent=rgb(140, 70, 60), eye=rgb(255, 200, 70),
                tail=rgb(110, 140, 160), tip=rgb(210, 80, 70)),
    tails=3, tailSegs=4, tailW=2.4, tailLen=9, tailRise=0.5, tailSpread=0.7, tailBaseY=0.45, extras=extras_isobu)


def extras_songoku(c, g):
    white = rgb(245, 240, 230)
    for i in range(1, 4):
        c.add(f"Mane{i}", v(g.H.x * (1.2 - i * 0.1), 3, 2.2), v(0, g.headTop - i * 2.2, g.headCZ + g.H.z / 2 + 0.6), white, None, g.head)
    def f(s, n):
        hx = s * g.H.x * 0.3
        h1 = c.add(f"Horn1.{n}", v(1.4, 3, 1.4), v(hx, g.headTop + 1.2, g.headCZ - 0.5), white, None, g.head, v(hx, g.headTop - 0.2, g.headCZ - 0.5))
        h2 = c.add(f"Horn2.{n}", v(1.2, 2.5, 1.2), v(s * g.H.x * 0.42, g.headTop + 3.6, g.headCZ - 0.5), white, None, h1, v(hx, g.headTop + 2.4, g.headCZ - 0.5))
        c.add(f"Horn3.{n}", v(1, 2, 1), v(s * g.H.x * 0.54, g.headTop + 5.4, g.headCZ - 0.5), white, None, h2, v(s * g.H.x * 0.42, g.headTop + 4.8, g.headCZ - 0.5))
        c.add(f"ShoulderSpike.{n}", v(2, 3, 2), v(s * (g.B.x / 2 + 0.6), g.bodyTop - 0.5, g.frontZ + 2.5), white, None, g.body)
        c.add(f"ChestHair.{n}", v(g.B.x * 0.3, 5, 0.8), v(s * g.B.x * 0.18, g.legH + g.B.y * 0.55, g.frontZ - 0.3), white, None, g.body)
    sides(f)

SPECS["SonGoku"] = dict(
    name="SonGoku", order=4, body=v(13, 12, 10), legH=6, legW=3.5, head=v(8, 8, 8), snout=3, earStyle="round",
    colors=dict(body=rgb(200, 60, 55), belly=rgb(240, 230, 210), accent=rgb(245, 240, 230), eye=rgb(255, 220, 70),
                tail=rgb(200, 60, 55), tip=rgb(245, 240, 230), snout=rgb(235, 210, 185)),
    tails=4, tailSegs=5, tailW=2.6, tailLen=14, tailRise=0.55, tailSpread=0.6, extras=extras_songoku)


def extras_kokuo(c, g):
    red = rgb(220, 60, 70)
    h1 = c.add("Horn1", v(1.6, 2.4, 1.6), v(0, g.headTop + 1, g.headCZ - 2), WHITE, None, g.head, v(0, g.headTop - 0.2, g.headCZ - 2))
    h2 = c.add("Horn2", v(1.2, 2.4, 1.2), v(0, g.headTop + 3.2, g.headCZ - 2.6), red, None, h1, v(0, g.headTop + 2.2, g.headCZ - 2))
    c.add("Horn3", v(0.8, 2.2, 0.8), v(0, g.headTop + 5.2, g.headCZ - 3.2), WHITE, None, h2, v(0, g.headTop + 4.4, g.headCZ - 2.6))
    for i in range(1, 8):
        c.add(f"Mane{i}", v(1.4, 2 + (i % 2), 2), v(0, g.bodyTop + 0.6 + (2 if i == 1 else 0), g.frontZ + (i - 1) * 2.2), red, None, g.body)
    def f(s, n):
        c.add(f"EyeMark.{n}", v(g.H.x * 0.14, g.H.y * 0.34, 0.25), v(s * g.H.x * 0.3, g.eyeY - g.H.y * 0.2, g.eyeZ + 0.05), red, None, g.head)
        c.add(f"Fin.{n}", v(0.6, 3, 4), v(s * (g.B.x / 2 + 0.3), g.legH + g.B.y * 0.7, g.frontZ + 4), red, None, g.body)
    sides(f)

SPECS["Kokuo"] = dict(
    name="Kokuo", order=5, body=v(8, 8, 16), legH=7, legW=2.4, head=v(6, 7, 8), snout=4, earStyle="fox", earScale=0.8,
    colors=dict(body=rgb(240, 240, 245), belly=rgb(255, 255, 255), accent=rgb(220, 60, 70), eye=rgb(255, 70, 70),
                tail=rgb(240, 240, 245), tip=rgb(220, 60, 70), paw=rgb(220, 60, 70), earTip=rgb(220, 60, 70), nose=rgb(220, 60, 70)),
    tails=5, tailSegs=5, tailW=2, tailLen=14, tailRise=0.6, tailSpread=0.7, tipSegs=2, extras=extras_kokuo)


def extras_saiken(c, g):
    c.add("Foot", v(g.B.x * 1.12, 1.6, g.B.z * 1.05), v(0, 0.8, 0), rgb(185, 205, 235), None, g.body)
    def f(s, n):
        px = s * g.H.x * 0.28
        st = c.add(f"Antenna.{n}", v(0.9, 3.5, 0.9), v(px, g.headTop + 1.6, g.headCZ - 1), rgb(215, 230, 250), None, g.head, v(px, g.headTop - 0.1, g.headCZ - 1))
        c.add(f"AntennaBall.{n}", v(1.6, 1.6, 1.6), v(px, g.headTop + 3.8, g.headCZ - 1), rgb(110, 160, 230), "neon", st)
    sides(f)
    for i in range(1, 6):
        c.add(f"BackBump{i}", v(2.4, 1.6, 2.4), v(0, g.bodyTop + 0.6, g.frontZ + g.B.z * i / 6), rgb(110, 160, 230), None, g.body)

SPECS["Saiken"] = dict(
    name="Saiken", order=6, body=v(11, 9, 22), legH=0, legW=1, legs=False, head=v(8, 7, 7), snout=1.5, earStyle="none", fangs=False,
    colors=dict(body=rgb(225, 235, 250), belly=rgb(185, 205, 235), accent=rgb(110, 160, 230), eye=rgb(255, 190, 60),
                tail=rgb(215, 230, 250), tip=rgb(150, 200, 255)),
    bands=dict(count=6, color=rgb(190, 210, 240), thick=0.9),
    tails=6, tailSegs=6, tailW=2.2, tailLen=16, tailRise=0.5, tailSpread=0.5, tailWave=0.4, tailMat="glass", tipSegs=2,
    extras=extras_saiken)


def extras_chomei(c, g):
    dark = rgb(30, 90, 60)
    h1 = c.add("Horn1", v(1.6, 2, 1.6), v(0, g.headTop + 0.6, g.headCZ - 1.5), dark, None, g.head, v(0, g.headTop - 0.2, g.headCZ - 1.5))
    h2 = c.add("Horn2", v(1.3, 1.8, 1.8), v(0, g.headTop + 2, g.headCZ - 3), dark, None, h1, v(0, g.headTop + 1.4, g.headCZ - 1.5))
    c.add("Horn3", v(1, 1.4, 2), v(0, g.headTop + 2.8, g.headCZ - 4.8), dark, None, h2, v(0, g.headTop + 2.4, g.headCZ - 3))
    def f(s, n):
        c.add(f"Elytron.{n}", v(g.B.x * 0.48, 1.2, g.B.z * 0.8), v(s * g.B.x * 0.25, g.bodyTop + 0.6, 0.5), dark, None, g.body)
        c.add(f"Wing.{n}", v(8, 0.4, 16), v(s * (g.B.x * 0.35 + 4), g.bodyTop + 1.4, 1), rgb(200, 245, 215), "glass", g.body, v(s * g.B.x * 0.3, g.bodyTop + 1.2, -2))
        c.add(f"Antenna.{n}", v(0.6, 3, 0.6), v(s * g.H.x * 0.25, g.headTop + 1.2, g.headCZ - 2), dark, None, g.head, v(s * g.H.x * 0.25, g.headTop - 0.2, g.headCZ - 2))
    sides(f)

SPECS["Chomei"] = dict(
    name="Chomei", order=7, body=v(8, 7, 14), legH=5, legW=1.6, head=v(7, 6, 6), snout=1.5, earStyle="none",
    colors=dict(body=rgb(60, 160, 90), belly=rgb(200, 210, 120), accent=rgb(30, 90, 60), eye=rgb(255, 60, 60),
                tail=rgb(170, 230, 190), tip=rgb(100, 200, 140), limb=rgb(40, 120, 70)),
    tails=7, tailSegs=3, tailW=1.5, tailLen=8, tailRise=0.9, tailSpread=0.8, tailMat="glass", tipSegs=1,
    extras=extras_chomei)


def extras_gyuki(c, g):
    horn = rgb(240, 235, 220)
    c.add("Hump", v(g.B.x * 0.8, 3.5, 6), v(0, g.bodyTop + 1.4, g.frontZ + 4), rgb(125, 55, 40), None, g.body)
    def f(s, n):
        hx, hy, hz = s * g.H.x * 0.5, g.headTop - 1.2, g.headCZ
        h1 = c.add(f"Horn1.{n}", v(1.8, 1.8, 1.8), v(hx, hy, hz), horn, None, g.head, v(hx - s * 0.9, hy, hz))
        h2 = c.add(f"Horn2.{n}", v(1.6, 1.6, 1.6), v(s * (g.H.x * 0.5 + 1.8), hy, hz), horn, None, h1, v(hx, hy, hz))
        h3 = c.add(f"Horn3.{n}", v(1.4, 2.4, 1.4), v(s * (g.H.x * 0.5 + 3.2), g.headTop + 0.4, hz), horn, None, h2, v(s * (g.H.x * 0.5 + 1.8), hy, hz))
        c.add(f"Horn4.{n}", v(1.1, 2.2, 1.1), v(s * (g.H.x * 0.5 + 3.6), g.headTop + 2.4, hz), horn, None, h3, v(s * (g.H.x * 0.5 + 3.2), g.headTop + 1.2, hz))
    sides(f)
    c.add("NoseRing", v(2.4, 0.5, 0.5), v(0, g.snoutY - 1, g.snoutZ - 1.6), rgb(220, 190, 80), None, g.head)

SPECS["Gyuki"] = dict(
    name="Gyuki", order=8, body=v(13, 11, 17), legH=5, legW=3.4, head=v(9, 9, 9), snout=3.5, earStyle="cat",
    colors=dict(body=rgb(150, 70, 50), belly=rgb(230, 200, 170), accent=rgb(240, 235, 220), eye=rgb(255, 200, 60),
                tail=rgb(200, 140, 125), tip=rgb(235, 190, 170), snout=rgb(210, 160, 130)),
    tails=8, tailSegs=6, tailW=2.6, tailLen=20, tailRise=0.25, tailSpread=0.5, tailWave=0.8, tailBaseY=0.45, tipSegs=1,
    extras=extras_gyuki)


def extras_kurama(c, g):
    H = g.H
    def f(s, n):
        c.add(f"EyeStreak.{n}", v(H.x * 0.12, H.y * 0.4, 0.25), v(s * H.x * 0.3, g.eyeY - H.y * 0.26, g.eyeZ + 0.05), BLACK, None, g.head)
        c.add(f"CheekFur.{n}", v(1.6, H.y * 0.35, 2.4), v(s * (H.x / 2 + 0.6), g.headCY - H.y * 0.2, g.headCZ + 1), rgb(255, 140, 20), None, g.head)
        for i in range(1, 4):
            c.add(f"Whisker{i}.{n}", v(2, 0.25, 0.25), v(s * (H.x / 2 + 1.4), g.headCY - H.y * 0.25 - (i - 2) * 0.6, g.headCZ - H.z / 2 + 1.2), BLACK, None, g.head)
        c.add(f"ShoulderMark.{n}", v(0.3, 2.4, 2.4), v(s * (g.B.x / 2 + 0.05), g.bodyTop - 2.2, g.frontZ + 2.5), BLACK, None, g.body)
    sides(f)
    c.add("ForeheadMark", v(1.2, 1.6, 0.3), v(0, g.headTop - 1, g.eyeZ), BLACK, None, g.head)

SPECS["Kurama"] = dict(
    name="Kurama", order=9, body=v(9, 8, 14), legH=6, legW=2.4, head=v(7.5, 7, 7), snout=3.5, earStyle="fox",
    colors=dict(body=rgb(255, 140, 20), belly=rgb(255, 240, 215), accent=BLACK, eye=rgb(255, 20, 20),
                tail=rgb(255, 140, 20), tip=rgb(255, 235, 205), earTip=BLACK, paw=BLACK),
    tails=9, tailSegs=6, tailW=3, tailLen=18, tailRise=0.6, tailSpread=0.45, tipSegs=1, extras=extras_kurama)

NAMES = sorted(SPECS, key=lambda n: SPECS[n]["order"])


# ----------------------------------------------------------------------------
# Conversion vers Blender : mesh unique + armature + matériaux + animations
# ----------------------------------------------------------------------------
def to_blender(p, k):
    """Repère de conception (x, y haut, z arrière) -> Blender (x, y avant=-Y, z haut), en mètres."""
    return Vector((p.x * S, p.z * S, p.y * S))


_MATS = {}

def srgb_to_lin(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def get_material(color, kind):
    key = (color, kind)
    if key in _MATS and _MATS[key].name in bpy.data.materials:
        return _MATS[key]
    name = f"{kind or 'mat'}_{int(color[0]*255):02x}{int(color[1]*255):02x}{int(color[2]*255):02x}"
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    lin = tuple(srgb_to_lin(x) for x in color) + (1.0,)
    bsdf.inputs["Base Color"].default_value = lin
    bsdf.inputs["Roughness"].default_value = 0.85
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


CUBE_FACES = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5)]


def make_object(ctx, origin=Vector((0, 0, 0))):
    spec = ctx.spec
    name = spec["name"]

    # --- mesh : un cube indépendant par pièce (ombrage plat) ---
    bm = bmesh.new()
    mats, mat_index = [], {}
    vert_bone = []  # (bm vert, nom d'os)
    for p in ctx.parts:
        key = (p.color, p.mat)
        if key not in mat_index:
            mat_index[key] = len(mats)
            mats.append(get_material(p.color, p.mat))
        c = to_blender(p.off, 1)
        h = Vector((p.size.x * S / 2, p.size.z * S / 2, p.size.y * S / 2))
        verts = []
        for dz in (-1, 1):
            for corner in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                verts.append(bm.verts.new(c + Vector((corner[0] * h.x, corner[1] * h.y, dz * h.z))))
        for f in CUBE_FACES:
            face = bm.faces.new([verts[i] for i in f])
            face.material_index = mat_index[key]
        for vt in verts:
            vert_bone.append((vt, p.bone))
    bm.verts.ensure_lookup_table()
    mesh = bpy.data.meshes.new(name + "_mesh")
    # mémorise les indices avant conversion
    idx_bone = [(i, b) for i, (_vt, b) in enumerate(vert_bone)]  # sommets créés dans l'ordre
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(name + "_Mesh", mesh)
    bpy.context.scene.collection.objects.link(obj)

    # --- armature ---
    arm_data = bpy.data.armatures.new(name + "_Armature")
    arm = bpy.data.objects.new(name + "_Rig", arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    ebs = {}
    for bname, b in ctx.bones.items():
        eb = arm_data.edit_bones.new(bname)
        head = to_blender(b["head"], 1)
        eb.head = head
        part = b["part"]
        if part is not None:
            cen = to_blender(part.off, 1)
            tail = head + (cen - head) * 2
            if (tail - head).length < 0.05:
                tail = head + Vector((0, 0, max(0.08, part.size.y * S * 0.5)))
        else:
            tail = head + Vector((0, 0, 0.3))
        if (tail - head).length < 0.05:
            tail = head + Vector((0, 0, 0.05))
        eb.tail = tail
        ebs[bname] = eb
    for bname, b in ctx.bones.items():
        if b["parent"]:
            ebs[bname].parent = ebs[b["parent"]]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm_data.display_type = "OCTAHEDRAL"

    # --- skinning rigide (poids 1.0) ---
    groups = {bn: obj.vertex_groups.new(name=bn) for bn in ctx.bones}
    per_bone = {}
    for i, bn in idx_bone:
        per_bone.setdefault(bn, []).append(i)
    for bn, idxs in per_bone.items():
        groups[bn].add(idxs, 1.0, "REPLACE")
    mod = obj.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    obj.parent = arm

    arm.location += origin  # le maillage est enfant de l'armature : il suit
    return obj, arm


def make_actions(arm, ctx):
    """Crée les actions Idle (respiration / queues) et Walk (cycle de marche)."""
    spec = ctx.spec
    pose = arm.pose.bones
    for pb in pose:
        pb.rotation_mode = "XYZ"
    arm.animation_data_create()

    # signe pour que la mâchoire s'ouvre vers le bas
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
            pb.keyframe_insert("location", frame=frame)

    tails = [(n, tuple(int(x) for x in n[4:].split("_"))) for n in ctx.bones if n.startswith("Tail")]
    legs = [n for n in ctx.bones if "Leg_Upper" in n or "Leg_Lower" in n]

    # ---- Idle (60 images, boucle) ----
    action = bpy.data.actions.new("Idle")
    action.use_fake_user = True
    arm.animation_data.action = action
    for frame in (1, 16, 31, 46, 61):
        reset()
        ph = (frame - 1) / 60 * 2 * math.pi
        if "Body" in pose:
            pose["Body"].location = (0, 0, math.sin(ph) * 0.03)
        if "Head" in pose:
            pose["Head"].rotation_euler = (math.sin(ph) * 0.04, 0, math.sin(ph) * 0.08)
        if "Jaw" in pose:
            pose["Jaw"].rotation_euler = (jaw_sign * (0.04 + 0.03 * math.sin(ph)), 0, 0)
        for n, (i, k) in tails:
            pose[n].rotation_euler = (math.sin(ph - k * 0.5 + i) * 0.05, 0, math.sin(ph - k * 0.5 + i * 0.7) * (0.10 + 0.02 * k))
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
            else:
                pose[n].rotation_euler = (max(0.0, -math.cos(ph + diag)) * 0.5, 0, 0)
        if "Body" in pose:
            pose["Body"].location = (0, 0, abs(math.sin(ph)) * 0.04)
        for n, (i, k) in tails:
            pose[n].rotation_euler = (0, 0, math.sin(ph - k * 0.6 + i * 0.7) * (0.08 + 0.02 * k))
        key_all(frame)

    reset()
    arm.animation_data.action = action
    scn = bpy.context.scene
    scn.frame_start, scn.frame_end = 1, 61


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _MATS.clear()


def export_all(name, arm, obj):
    os.makedirs(OUT, exist_ok=True)
    blend = os.path.join(OUT, f"{name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    try:
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"{name}.fbx"), use_selection=True,
                                 add_leaf_bones=False, bake_anim=True, bake_anim_use_all_actions=True,
                                 bake_anim_use_nla_strips=False, bake_anim_simplify_factor=0.0, apply_scale_options="FBX_SCALE_ALL")
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
    print(f"{name}: {len(ctx.parts)} cubes, {len(ctx.bones)} os")
    return ctx


def build_all_in_one():
    reset_scene()
    for i, name in enumerate(NAMES):
        ctx = build_quad(SPECS[name])
        obj, arm = make_object(ctx, origin=Vector(((i - 4) * 14.0, 0, 0)))
        make_actions(arm, ctx)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Bijuu_Tous.blend"))


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in SPECS] or NAMES
    for n in wanted:
        build_one(n)
    if len(wanted) == len(NAMES):
        build_all_in_one()
