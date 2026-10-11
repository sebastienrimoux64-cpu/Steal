"""
HOME BUILDER KIT — pack d'assets "maison" pour Blender (et Unity / Unreal / Godot via FBX / glTF).

Génère ~70 assets low-poly propres, à l'échelle réelle (mètres), pivot au sol, matériaux PBR unis :
éléments de construction modulaires (grille de 2 m), sols, toits, escaliers, portes, fenêtres,
mobilier (salon, chambre, cuisine, salle de bain), éclairage, déco, extérieur.

    python tools/make_home_kit.py            # génère le pack dans HomeKit/

Conventions : Z vers le haut, 1 unité = 1 m. L'avant des meubles regarde vers -Y.
Les murs courent le long de X (épaisseur sur Y), pivot au centre-bas.
"""
import math
import os
import random
import shutil
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "HomeKit")

GRID = 2.0      # module de base
WH = 2.8        # hauteur sous plafond
WT = 0.2        # épaisseur des murs
HW = WT / 2

# ----------------------------------------------------------------------------
# Matériaux (PBR unis)
# ----------------------------------------------------------------------------
MATS = {
    #  nom:            (couleur sRGB,            rugosité, métal, options)
    "plaster":        ((0.93, 0.91, 0.86), 0.90, 0.0, {}),
    "paint_sage":     ((0.56, 0.66, 0.59), 0.90, 0.0, {}),
    "paint_blue":     ((0.42, 0.55, 0.70), 0.90, 0.0, {}),
    "trim_white":     ((0.96, 0.96, 0.94), 0.55, 0.0, {}),
    "wood_oak":       ((0.60, 0.42, 0.25), 0.60, 0.0, {}),
    "wood_light":     ((0.82, 0.66, 0.46), 0.60, 0.0, {}),
    "wood_light_b":   ((0.76, 0.60, 0.41), 0.60, 0.0, {}),
    "wood_dark":      ((0.28, 0.17, 0.10), 0.55, 0.0, {}),
    "siding":         ((0.78, 0.74, 0.66), 0.80, 0.0, {}),
    "brick":          ((0.62, 0.29, 0.21), 0.90, 0.0, {}),
    "brick_b":        ((0.56, 0.25, 0.18), 0.90, 0.0, {}),
    "mortar":         ((0.72, 0.70, 0.66), 0.95, 0.0, {}),
    "stone":          ((0.58, 0.58, 0.57), 0.90, 0.0, {}),
    "concrete":       ((0.50, 0.50, 0.50), 0.95, 0.0, {}),
    "roof_tile":      ((0.55, 0.22, 0.15), 0.80, 0.0, {}),
    "roof_tile_b":    ((0.48, 0.19, 0.13), 0.80, 0.0, {}),
    "metal_black":    ((0.04, 0.04, 0.045), 0.40, 0.9, {}),
    "metal_chrome":   ((0.80, 0.80, 0.82), 0.18, 1.0, {}),
    "brass":          ((0.78, 0.60, 0.25), 0.30, 1.0, {}),
    "glass":          ((0.80, 0.90, 1.00), 0.05, 0.0, {"alpha": 0.25}),
    "fabric_grey":    ((0.36, 0.38, 0.41), 1.00, 0.0, {}),
    "fabric_beige":   ((0.78, 0.70, 0.58), 1.00, 0.0, {}),
    "fabric_blue":    ((0.20, 0.31, 0.50), 1.00, 0.0, {}),
    "fabric_red":     ((0.60, 0.18, 0.16), 1.00, 0.0, {}),
    "fabric_green":   ((0.28, 0.42, 0.30), 1.00, 0.0, {}),
    "leather":        ((0.36, 0.19, 0.10), 0.50, 0.0, {}),
    "ceramic":        ((0.96, 0.96, 0.95), 0.12, 0.0, {}),
    "tile_floor":     ((0.80, 0.80, 0.78), 0.30, 0.0, {}),
    "tile_floor_b":   ((0.30, 0.34, 0.38), 0.30, 0.0, {}),
    "mattress":       ((0.92, 0.92, 0.90), 1.00, 0.0, {}),
    "terracotta":     ((0.70, 0.35, 0.20), 0.85, 0.0, {}),
    "soil":           ((0.18, 0.11, 0.07), 1.00, 0.0, {}),
    "leaf":           ((0.20, 0.46, 0.20), 0.70, 0.0, {}),
    "leaf_b":         ((0.30, 0.55, 0.25), 0.70, 0.0, {}),
    "screen":         ((0.02, 0.02, 0.03), 0.08, 0.2, {}),
    "bulb":           ((1.00, 0.92, 0.72), 0.50, 0.0, {"emit": 6.0}),
    "shade":          ((0.95, 0.88, 0.74), 0.90, 0.0, {}),
    "rug_a":          ((0.55, 0.20, 0.18), 1.00, 0.0, {}),
    "rug_b":          ((0.85, 0.78, 0.62), 1.00, 0.0, {}),
    "rug_c":          ((0.25, 0.35, 0.45), 1.00, 0.0, {}),
    "canvas_a":       ((0.85, 0.55, 0.25), 0.90, 0.0, {}),
    "canvas_b":       ((0.30, 0.50, 0.60), 0.90, 0.0, {}),
    "canvas_c":       ((0.88, 0.85, 0.75), 0.90, 0.0, {}),
    "mirror":         ((0.74, 0.82, 0.90), 0.03, 0.0, {}),
    "book_a":         ((0.55, 0.15, 0.15), 0.8, 0.0, {}),
    "book_b":         ((0.15, 0.30, 0.45), 0.8, 0.0, {}),
    "book_c":         ((0.20, 0.45, 0.25), 0.8, 0.0, {}),
    "book_d":         ((0.80, 0.70, 0.35), 0.8, 0.0, {}),
    "grass":          ((0.30, 0.50, 0.22), 1.0, 0.0, {}),
}
_MAT_CACHE = {}


def srgb_to_lin(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def material(name):
    if name in _MAT_CACHE and _MAT_CACHE[name].name in bpy.data.materials:
        return _MAT_CACHE[name]
    col, rough, metal, opt = MATS[name]
    m = bpy.data.materials.new("HK_" + name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    lin = tuple(srgb_to_lin(c) for c in col) + (1.0,)
    b.inputs["Base Color"].default_value = lin
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = lin
    m.roughness = rough
    m.metallic = metal
    if "alpha" in opt:
        b.inputs["Alpha"].default_value = opt["alpha"]
        m.diffuse_color = lin[:3] + (opt["alpha"],)
        if hasattr(m, "surface_render_method"):
            m.surface_render_method = "BLENDED"
    if "emit" in opt:
        b.inputs["Emission Color"].default_value = lin
        b.inputs["Emission Strength"].default_value = opt["emit"]
    _MAT_CACHE[name] = m
    return m


# ----------------------------------------------------------------------------
# Constructeur d'asset (bmesh)
# ----------------------------------------------------------------------------
class Asset:
    def __init__(self, name):
        self.name = name
        self.bm = bmesh.new()
        self.mats = []
        self.aabbs = []   # boîtes non tournées déjà posées (pour éviter les faces coplanaires)

    def _mi(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def _finish_prim(self, verts, mat, bevel, seg):
        faces = {f for v in verts for f in v.link_faces}
        mi = self._mi(mat)
        for f in faces:
            f.material_index = mi
        if bevel > 0:
            edges = {e for v in verts for e in v.link_edges}
            res = bmesh.ops.bevel(self.bm, geom=list(edges), offset=bevel, offset_type="OFFSET",
                                  segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
            for f in res["faces"]:
                f.material_index = mi

    def bx(self, mat, x0, x1, y0, y1, z0, z1, b=0.008, seg=2, rot=None):
        """Boîte par extents. rot=(rx,ry,rz) en radians autour de son centre."""
        if x1 - x0 < 1e-5 or y1 - y0 < 1e-5 or z1 - z0 < 1e-5:
            return
        if not rot:
            x0, x1, y0, y1, z0, z1 = self._dodge(x0, x1, y0, y1, z0, z1)
        c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        m = Matrix.Translation(c)
        if rot:
            m = m @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
        m = m @ Matrix.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1.0))
        r = bmesh.ops.create_cube(self.bm, size=1.0, matrix=m)
        self._finish_prim(r["verts"], mat, min(b, (min(x1 - x0, y1 - y0, z1 - z0)) * 0.45), seg)

    def _dodge(self, *box):
        """Évite que deux faces de même sens soient dans le même plan (z-fighting / faces noires) :
        la boîte la plus récente avance de 0,5 mm tant qu'un plan coïncide avec une boîte existante."""
        b = list(box)
        eps = 5e-4
        for _ in range(8):
            moved = False
            for ax in range(3):
                for side in (0, 1):           # 0 = face min, 1 = face max
                    for o in self.aabbs:
                        if abs(b[2 * ax + side] - o[2 * ax + side]) > 1e-6:
                            continue
                        # recouvrement non nul sur les deux autres axes ?
                        if all(min(b[2 * k + 1], o[2 * k + 1]) - max(b[2 * k], o[2 * k]) > 1e-6 for k in range(3) if k != ax):
                            b[2 * ax + side] += eps if side else -eps
                            moved = True
                            break
            if not moved:
                break
        self.aabbs.append(tuple(b))
        return b

    def cyl(self, mat, r, z0, z1, cx=0.0, cy=0.0, segs=24, r2=None, rot=None, b=0.0, open_ends=False):
        """Cylindre / cône vertical entre z0 et z1."""
        h = z1 - z0
        m = Matrix.Translation(Vector((cx, cy, (z0 + z1) / 2)))
        if rot:
            m = m @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
        res = bmesh.ops.create_cone(self.bm, cap_ends=not open_ends, cap_tris=False, segments=segs,
                                    radius1=r, radius2=r if r2 is None else r2, depth=h, matrix=m)
        self._finish_prim(res["verts"], mat, b, 2)

    def hcyl(self, mat, r, axis, c0, c1, cy_or_cx, cz, segs=20):
        """Cylindre horizontal. axis='x' : de x=c0 à x=c1 (centre y=cy_or_cx, z=cz) ; axis='y' idem sur y."""
        L = c1 - c0
        mid = (c0 + c1) / 2
        if axis == "x":
            pos, rot = Vector((mid, cy_or_cx, cz)), (0, math.pi / 2, 0)
        else:
            pos, rot = Vector((cy_or_cx, mid, cz)), (math.pi / 2, 0, 0)
        m = Matrix.Translation(pos) @ Matrix.Rotation(rot[2], 4, "Z") @ Matrix.Rotation(rot[1], 4, "Y") @ Matrix.Rotation(rot[0], 4, "X")
        res = bmesh.ops.create_cone(self.bm, cap_ends=True, cap_tris=False, segments=segs, radius1=r, radius2=r, depth=L, matrix=m)
        self._finish_prim(res["verts"], mat, 0.0, 2)

    def sphere(self, mat, r, cx, cy, cz, sx=1.0, sy=1.0, sz=1.0, segs=14):
        m = Matrix.Translation(Vector((cx, cy, cz))) @ Matrix.Diagonal((sx, sy, sz, 1.0))
        res = bmesh.ops.create_uvsphere(self.bm, u_segments=segs, v_segments=max(6, segs // 2), radius=r, matrix=m)
        self._finish_prim(res["verts"], mat, 0.0, 1)

    def prism_tri(self, mat, w, h, y0, y1, z0=0.0):
        """Prisme triangulaire (pignon) : base largeur w centrée sur x, hauteur h, épaisseur y0..y1."""
        bm = self.bm
        pts = [(-w / 2, z0), (w / 2, z0), (0.0, z0 + h)]
        vs = [bm.verts.new((x, y, z)) for (x, z) in pts for y in (y0, y1)]
        a0, a1, b0, b1, c0, c1 = vs
        mi = self._mi(mat)
        for quad in ((a0, b0, b1, a1), (b0, c0, c1, b1), (c0, a0, a1, c1)):
            bm.faces.new(quad).material_index = mi
        fs = [bm.faces.new(quad) for quad in ((a0, c0, b0), (a1, b1, c1))]
        for f in fs:
            f.material_index = mi
        bmesh.ops.recalc_face_normals(bm, faces=list({f for v in vs for f in v.link_faces}))

    def legs(self, mat, x0, x1, y0, y1, h, t=0.04, z0=0.0, b=0.004):
        for xs in (x0, x1 - t):
            for ys in (y0, y1 - t):
                self.bx(mat, xs, xs + t, ys, ys + t, z0, h, b=b)

    def build(self, collection):
        bm = self.bm
        # UV : projection cubique en mètres (densité de texels constante)
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for lp in f.loops:
                p = lp.vert.co
                lp[uv].uv = ((p.y, p.z), (p.x, p.z), (p.x, p.y))[ax]
        # arêtes franches au-delà de 50°, le reste lissé
        lim = math.radians(50)
        for f in bm.faces:
            f.smooth = True
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < lim
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for mname in self.mats:
            mesh.materials.append(material(mname))
        obj = bpy.data.objects.new(self.name, mesh)
        collection.objects.link(obj)
        return obj


REGISTRY = []   # (catégorie, nom, fonction)


def asset(category, name):
    def deco(fn):
        REGISTRY.append((category, name, fn))
        return fn
    return deco


# ----------------------------------------------------------------------------
# 01 — STRUCTURE (murs modulaires)
# ----------------------------------------------------------------------------
def wall(a, W, openings=(), height=WH, int_mat="plaster", ext_mat="plaster", trim=True):
    """Mur de largeur W le long de X. openings = [(cx, w, z0, z1)]."""
    ops = sorted(openings)
    cur = -W / 2
    solids = []
    def solid(x0, x1):
        if x1 - x0 > 1e-3:
            solids.append((x0, x1))
            a.bx(int_mat, x0, x1, 0, HW, 0, height, b=0)
            a.bx(ext_mat, x0, x1, -HW, 0, 0, height, b=0)
    for cx, w, z0, z1 in ops:
        solid(cur, cx - w / 2)
        if z0 > 1e-3:
            a.bx(int_mat, cx - w / 2, cx + w / 2, 0, HW, 0, z0, b=0)
            a.bx(ext_mat, cx - w / 2, cx + w / 2, -HW, 0, 0, z0, b=0)
        if z1 < height - 1e-3:
            a.bx(int_mat, cx - w / 2, cx + w / 2, 0, HW, z1, height, b=0)
            a.bx(ext_mat, cx - w / 2, cx + w / 2, -HW, 0, z1, height, b=0)
        cur = cx + w / 2
    solid(cur, W / 2)
    if trim:
        for x0, x1 in solids:
            a.bx("trim_white", x0, x1, HW, HW + 0.014, 0, 0.12, b=0.004)
            a.bx("trim_white", x0, x1, -HW - 0.014, -HW, 0, 0.12, b=0.004)


@asset("01_Structure", "Wall_Solid_2m")
def _(a):
    wall(a, 2.0)

@asset("01_Structure", "Wall_Solid_1m")
def _(a):
    wall(a, 1.0)

@asset("01_Structure", "Wall_Door_2m")
def _(a):
    wall(a, 2.0, [(0, 1.0, 0, 2.1)])

@asset("01_Structure", "Wall_Window_2m")
def _(a):
    wall(a, 2.0, [(0, 1.2, 0.9, 2.1)])
    a.bx("stone", -0.7, 0.7, -HW - 0.07, HW + 0.03, 0.86, 0.9, b=0.01)

@asset("01_Structure", "Wall_Window_Wide_2m")
def _(a):
    wall(a, 2.0, [(0, 1.6, 0.9, 2.1)])
    a.bx("stone", -0.9, 0.9, -HW - 0.07, HW + 0.03, 0.86, 0.9, b=0.01)

@asset("01_Structure", "Wall_Archway_2m")
def _(a):
    wall(a, 2.0, [(0, 1.4, 0, 2.3)])
    a.bx("trim_white", -0.72, -0.7, -HW - 0.02, HW + 0.02, 0, 2.32, b=0.004)
    a.bx("trim_white", 0.7, 0.72, -HW - 0.02, HW + 0.02, 0, 2.32, b=0.004)
    a.bx("trim_white", -0.72, 0.72, -HW - 0.02, HW + 0.02, 2.3, 2.34, b=0.004)

@asset("01_Structure", "Wall_Half_2m")
def _(a):
    wall(a, 2.0, height=1.1, trim=False)
    a.bx("wood_oak", -1.0, 1.0, -HW - 0.03, HW + 0.03, 1.1, 1.16, b=0.01)

@asset("01_Structure", "Wall_Siding_2m")
def _(a):
    wall(a, 2.0, ext_mat="siding")
    n = 14
    for i in range(n):
        z0 = i * WH / n
        a.bx("siding", -1.0, 1.0, -HW - 0.025, -HW, z0 + 0.01, z0 + WH / n - 0.005, b=0.004)

@asset("01_Structure", "Wall_Brick_2m")
def _(a):
    wall(a, 2.0, ext_mat="mortar")
    rows = 40
    bh = WH / rows
    for r in range(rows):
        off = 0.0 if r % 2 == 0 else 0.105
        mat = "brick" if r % 3 else "brick_b"
        x = -1.0 - 0.21 + off
        while x < 1.0:
            x0, x1 = max(x + 0.005, -1.0), min(x + 0.205, 1.0)
            if x1 - x0 > 0.03:
                a.bx(mat, x0, x1, -HW - 0.018, -HW, r * bh + 0.004, (r + 1) * bh - 0.004, b=0)
            x += 0.21

@asset("01_Structure", "Wall_Corner_Post")
def _(a):
    a.bx("trim_white", -0.16, 0.16, -0.16, 0.16, 0, WH, b=0.01)
    a.bx("stone", -0.18, 0.18, -0.18, 0.18, 0, 0.15, b=0.01)

@asset("01_Structure", "Wall_Pillar_Half")
def _(a):
    a.bx("plaster", -0.1, 0.1, -HW, HW, 0, WH, b=0)

@asset("01_Structure", "Beam_Ceiling_2m")
def _(a):
    a.bx("wood_dark", -1.0, 1.0, -0.1, 0.1, WH - 0.22, WH, b=0.01)

# ----------------------------------------------------------------------------
# 02 — SOLS, PLAFONDS, TOITS
# ----------------------------------------------------------------------------
@asset("02_Floors_Roofs", "Floor_Wood_2m")
def _(a):
    a.bx("concrete", -1, 1, -1, 1, -0.15, -0.0, b=0)
    n = 10
    for i in range(n):
        y0 = -1 + i * 0.2
        mat = "wood_light_b" if i % 2 else "wood_light"
        a.bx(mat, -1, 1, y0 + 0.003, y0 + 0.197, -0.005, 0.03, b=0.004)

@asset("02_Floors_Roofs", "Floor_Tile_2m")
def _(a):
    a.bx("concrete", -1, 1, -1, 1, -0.15, 0.0, b=0)
    for i in range(5):
        for j in range(5):
            mat = "tile_floor" if (i + j) % 2 == 0 else "tile_floor_b"
            a.bx(mat, -1 + i * 0.4 + 0.004, -1 + (i + 1) * 0.4 - 0.004, -1 + j * 0.4 + 0.004, -1 + (j + 1) * 0.4 - 0.004, 0.0, 0.02, b=0.003, seg=1)

@asset("02_Floors_Roofs", "Ceiling_2m")
def _(a):
    a.bx("plaster", -1, 1, -1, 1, 0, 0.15, b=0)
    a.bx("trim_white", -1, 1, -1, -0.97, -0.05, 0, b=0.004)
    a.bx("trim_white", -1, 1, 0.97, 1, -0.05, 0, b=0.004)

@asset("02_Floors_Roofs", "Foundation_2m")
def _(a):
    a.bx("concrete", -1, 1, -1, 1, -0.5, 0.0, b=0.01)

@asset("02_Floors_Roofs", "Slab_Upper_Floor_2m")
def _(a):
    a.bx("wood_dark", -1, 1, -1, 1, -0.25, -0.0, b=0)
    a.bx("wood_oak", -1, 1, -1, 1, 0.0, 0.03, b=0.005)

PITCH = math.radians(35)
RUN = 3.0   # portée horizontale d'un pan pour une maison de 6 m

@asset("02_Floors_Roofs", "Roof_Slope_Tile_2m")
def _(a):
    _roof(a, "roof_tile", "roof_tile_b")

@asset("02_Floors_Roofs", "Roof_Slope_Slate_2m")
def _(a):
    MATS.setdefault("slate_a", ((0.24, 0.26, 0.31), 0.7, 0.0, {}))
    MATS.setdefault("slate_b", ((0.19, 0.21, 0.26), 0.7, 0.0, {}))
    _roof(a, "slate_a", "slate_b")


def _roof(a, tile, tile_b):
    """Pan de toit : égout au pivot (y=0,z=0), monte vers +Y. Largeur 2 m (X)."""
    L = RUN / math.cos(PITCH)
    bm = a.bm
    # Construction par rotation d'une boîte autour de l'axe X puis translation
    def slab(mat, x0, x1, s0, s1, h0, h1, b):
        """boîte dans le repère de la pente (s le long de la pente, h perpendiculaire)."""
        before = set(bm.verts)
        a.bx(mat, x0, x1, s0, s1, h0, h1, b=b)
        new = [v for v in bm.verts if v not in before]
        rot = Matrix.Rotation(PITCH, 4, "X")
        bmesh.ops.transform(bm, matrix=rot, verts=new)
    slab("wood_dark", -1.0, 1.0, -0.15, L + 0.05, -0.12, 0.0, 0.0)
    n = int(L / 0.3)
    for r in range(n):
        s0 = r * 0.3
        mat = tile if r % 2 else tile_b
        slab(mat, -1.0, 1.0, s0, s0 + 0.34, 0.0, 0.05, 0.008)
    # liteau de rive
    slab("trim_white", -1.0, -0.97, -0.15, L + 0.05, 0.0, 0.08, 0.004)
    slab("trim_white", 0.97, 1.0, -0.15, L + 0.05, 0.0, 0.08, 0.004)


@asset("02_Floors_Roofs", "Roof_Ridge_2m")
def _(a):
    """Faîtage : deux ailes en V inversé + rouleau. Pivot à l'arête du faîtage."""
    bm = a.bm
    for sgn in (-1, 1):
        before = set(bm.verts)
        if sgn > 0:
            a.bx("roof_tile_b", -1.0, 1.0, 0.0, 0.36, 0.0, 0.05, b=0.008)
        else:
            a.bx("roof_tile_b", -1.0, 1.0, -0.36, 0.0, 0.0, 0.05, b=0.008)
        new = [v for v in bm.verts if v not in before]
        bmesh.ops.transform(bm, matrix=Matrix.Rotation(-sgn * PITCH, 4, "X"), verts=new)
    a.hcyl("roof_tile", 0.07, "x", -1.0, 1.0, 0.0, 0.025)

@asset("02_Floors_Roofs", "Roof_Gable_Triangle_6m")
def _(a):
    h = 3.0 * math.tan(PITCH)
    a.prism_tri("plaster", 6.0, h, -HW, HW)
    # bardage de rive
    a.prism_tri("trim_white", 6.3, h + 0.2, -HW - 0.03, -HW, z0=-0.0)

@asset("02_Floors_Roofs", "Chimney")
def _(a):
    a.bx("brick", -0.4, 0.4, -0.4, 0.4, 0.0, 2.2, b=0.01)
    for i in range(11):
        a.bx("mortar", -0.405, 0.405, -0.405, 0.405, 0.2 * i + 0.095, 0.2 * i + 0.105, b=0, seg=1)
    a.bx("concrete", -0.5, 0.5, -0.5, 0.5, 2.2, 2.3, b=0.01)
    a.bx("metal_black", -0.2, 0.2, -0.2, 0.2, 2.3, 2.34, b=0.005)

@asset("02_Floors_Roofs", "Dormer_Window_Small")
def _(a):
    a.bx("plaster", -0.6, 0.6, -0.5, 0.5, 0.0, 1.1, b=0.01)
    a.prism_tri("roof_tile", 1.4, 0.55, -0.62, 0.55, z0=1.1)
    a.bx("trim_white", -0.35, 0.35, -0.52, -0.5, 0.25, 0.95, b=0.005)
    a.bx("glass", -0.3, 0.3, -0.515, -0.505, 0.3, 0.9, b=0)

# ----------------------------------------------------------------------------
# 03 — ESCALIERS, PORTES, FENÊTRES
# ----------------------------------------------------------------------------
@asset("03_Doors_Windows", "Stairs_Straight_2.8m")
def _(a):
    steps = 15
    rise = WH / steps
    tread = 0.26
    w = 1.0
    for i in range(steps):
        a.bx("wood_oak", -w / 2, w / 2, i * tread, (i + 1) * tread + 0.03, i * rise, (i + 1) * rise, b=0.006)
    # limons
    L = steps * tread
    for sx in (-w / 2 - 0.04, w / 2):
        a.bx("wood_dark", sx, sx + 0.04, 0, L, 0, 0.18, b=0.005)
        for i in range(steps):
            a.bx("wood_dark", sx, sx + 0.04, i * tread, (i + 1) * tread, i * rise - 0.001, (i + 1) * rise, b=0.003)
    # garde-corps (côté +X)
    sx = w / 2 + 0.02
    for i in range(0, steps, 2):
        y = i * tread + tread / 2
        z = (i + 1) * rise
        a.bx("wood_dark", sx, sx + 0.035, y, y + 0.035, z, z + 0.85, b=0.004)
    a.bx("wood_dark", sx - 0.005, sx + 0.04, 0.0, 0.05, 0.0, 0.9, b=0.004)
    hyp = math.hypot(L, WH)
    ang = math.atan2(WH, L)
    a.bx("wood_oak", sx - 0.015, sx + 0.05, L / 2 - hyp / 2, L / 2 + hyp / 2, WH / 2 + 0.88, WH / 2 + 0.96, b=0.008, rot=(ang, 0, 0))

@asset("03_Doors_Windows", "Stairs_Porch_3step")
def _(a):
    for i in range(3):
        a.bx("stone", -0.8, 0.8, -0.35 * (3 - i) + 0.0, 0.0, 0.0, 0.17 * (i + 1), b=0.008)

@asset("03_Doors_Windows", "Railing_2m")
def _(a):
    for x in (-0.95, 0.95):
        a.bx("trim_white", x - 0.04, x + 0.04, -0.04, 0.04, 0, 1.0, b=0.006)
    a.bx("trim_white", -1.0, 1.0, -0.04, 0.04, 0.95, 1.03, b=0.008)
    a.bx("trim_white", -1.0, 1.0, -0.025, 0.025, 0.1, 0.15, b=0.004)
    for i in range(16):
        x = -0.88 + i * (1.76 / 15)
        a.bx("trim_white", x - 0.012, x + 0.012, -0.012, 0.012, 0.15, 0.95, b=0.002, seg=1)

@asset("03_Doors_Windows", "Door_Frame_1m")
def _(a):
    a.bx("trim_white", -0.5, -0.46, -HW - 0.02, HW + 0.02, 0, 2.1, b=0.005)
    a.bx("trim_white", 0.46, 0.5, -HW - 0.02, HW + 0.02, 0, 2.1, b=0.005)
    a.bx("trim_white", -0.5, 0.5, -HW - 0.02, HW + 0.02, 2.06, 2.1, b=0.005)

@asset("03_Doors_Windows", "Door_Interior")
def _(a):
    # battant pivot sur le bord X=-0.45
    a.bx("wood_light", -0.45, 0.45, -0.02, 0.02, 0.0, 2.04, b=0.006)
    for z0, z1 in ((0.25, 0.95), (1.1, 1.85)):
        a.bx("wood_oak", -0.33, 0.33, -0.026, 0.026, z0, z1, b=0.006)
    a.hcyl("brass", 0.012, "y", -0.06, 0.06, 0.34, 1.0, segs=12)
    for y0, y1 in ((-0.03, -0.02), (0.02, 0.03)):
        a.hcyl("brass", 0.028, "y", y0, y1, 0.34, 1.0, segs=16)
    a.bx("brass", 0.26, 0.36, -0.07, -0.05, 0.99, 1.01, b=0.004)
    a.bx("brass", 0.26, 0.36, 0.05, 0.07, 0.99, 1.01, b=0.004)

@asset("03_Doors_Windows", "Door_Front")
def _(a):
    a.bx("wood_dark", -0.45, 0.45, -0.025, 0.025, 0.0, 2.04, b=0.006)
    for z0, z1 in ((0.2, 0.9), (0.2, 0.9)):
        pass
    a.bx("wood_oak", -0.33, 0.33, -0.032, 0.032, 0.2, 0.85, b=0.006)
    a.bx("glass", -0.3, 0.3, -0.012, 0.012, 1.0, 1.9, b=0)
    for x in (-0.31, 0.29):
        a.bx("wood_oak", x, x + 0.02, -0.03, 0.03, 0.98, 1.92, b=0.004)
    a.bx("wood_oak", -0.31, 0.31, -0.03, 0.03, 0.96, 1.0, b=0.004)
    a.bx("wood_oak", -0.31, 0.31, -0.03, 0.03, 1.9, 1.94, b=0.004)
    a.bx("wood_oak", -0.01, 0.01, -0.03, 0.03, 1.0, 1.9, b=0.003)
    a.bx("brass", 0.3, 0.36, -0.05, -0.025, 0.95, 1.2, b=0.008)
    a.sphere("brass", 0.03, 0.33, -0.06, 1.0)

def window(a, W, H, mullions=1):
    t = 0.05
    a.bx("trim_white", -W / 2, -W / 2 + t, -0.05, 0.05, 0, H, b=0.006)
    a.bx("trim_white", W / 2 - t, W / 2, -0.05, 0.05, 0, H, b=0.006)
    a.bx("trim_white", -W / 2, W / 2, -0.05, 0.05, 0, t, b=0.006)
    a.bx("trim_white", -W / 2, W / 2, -0.05, 0.05, H - t, H, b=0.006)
    a.bx("glass", -W / 2 + t, W / 2 - t, -0.006, 0.006, t, H - t, b=0)
    pane = (W - 2 * t) / (mullions + 1)
    for i in range(1, mullions + 1):
        x = -W / 2 + t + pane * i
        a.bx("trim_white", x - 0.012, x + 0.012, -0.02, 0.02, t, H - t, b=0.003)
    a.bx("trim_white", -W / 2 + t, W / 2 - t, -0.02, 0.02, H / 2 - 0.012, H / 2 + 0.012, b=0.003)
    a.bx("metal_chrome", -0.03, 0.03, 0.05, 0.075, H / 2 - 0.05, H / 2 + 0.05, b=0.004)

@asset("03_Doors_Windows", "Window_Casement_1.2m")
def _(a):
    window(a, 1.2, 1.2, 1)

@asset("03_Doors_Windows", "Window_Casement_Wide_1.6m")
def _(a):
    window(a, 1.6, 1.2, 2)

@asset("03_Doors_Windows", "Shutter_Pair")
def _(a):
    for sx in (-1, 1):
        x0 = 0.0 if sx > 0 else -0.3
        a.bx("paint_sage", x0, x0 + 0.3, -0.015, 0.015, 0.0, 1.3, b=0.006)
        for i in range(10):
            z = 0.12 + i * 0.115
            a.bx("paint_sage", x0 + 0.03, x0 + 0.27, -0.025, 0.025, z, z + 0.03, b=0.003, rot=(math.radians(25), 0, 0))
    a.bx("metal_black", -0.3, 0.3, 0.015, 0.025, 0.1, 0.13, b=0.003)

# ----------------------------------------------------------------------------
# 04 — SALON
# ----------------------------------------------------------------------------
@asset("04_Living", "Chair_Dining")
def _(a):
    w, d = 0.46, 0.44
    a.bx("wood_oak", -w / 2, w / 2, -d / 2, d / 2, 0.42, 0.46, b=0.008)
    a.bx("fabric_beige", -w / 2 + 0.015, w / 2 - 0.015, -d / 2 + 0.015, d / 2 - 0.015, 0.46, 0.5, b=0.02, seg=3)
    t = 0.04
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.03)
        a.bx("wood_oak", x - t / 2, x + t / 2, -d / 2 + 0.01, -d / 2 + 0.01 + t, 0.0, 0.42, b=0.004)      # avant
        a.bx("wood_oak", x - t / 2, x + t / 2, d / 2 - 0.01 - t, d / 2 - 0.01, 0.0, 0.92, b=0.004)        # arrière (montant)
    for z0, z1 in ((0.2, 0.24),):
        a.bx("wood_oak", -w / 2 + 0.05, w / 2 - 0.05, -d / 2 + 0.01, -d / 2 + 0.03, z0, z1, b=0.003)
        a.bx("wood_oak", -w / 2 + 0.05, w / 2 - 0.05, d / 2 - 0.03, d / 2 - 0.01, z0, z1, b=0.003)
    a.bx("wood_oak", -w / 2 + 0.03, w / 2 - 0.03, d / 2 - 0.05, d / 2 - 0.01, 0.8, 0.9, b=0.008)
    for x in (-0.12, 0.0, 0.12):
        a.bx("wood_oak", x - 0.015, x + 0.015, d / 2 - 0.04, d / 2 - 0.02, 0.52, 0.8, b=0.003)

@asset("04_Living", "Chair_Bar_Stool")
def _(a):
    a.cyl("wood_oak", 0.19, 0.64, 0.7, segs=24, b=0.0)
    a.cyl("fabric_grey", 0.18, 0.7, 0.75, segs=24)
    for i in range(4):
        ang = i * math.pi / 2 + math.pi / 4
        a.cyl("metal_black", 0.016, 0.0, 0.64, cx=math.cos(ang) * 0.14, cy=math.sin(ang) * 0.14, segs=10)
    a.cyl("metal_black", 0.17, 0.22, 0.235, segs=24)

@asset("04_Living", "Armchair")
def _(a):
    a.bx("wood_dark", -0.43, 0.43, -0.42, 0.42, 0.08, 0.2, b=0.01)
    a.bx("fabric_blue", -0.35, 0.35, -0.42, 0.42, 0.2, 0.36, b=0.04, seg=3)
    a.bx("fabric_blue", -0.33, 0.33, -0.4, 0.3, 0.36, 0.5, b=0.05, seg=3)                # coussin d'assise
    a.bx("fabric_blue", -0.4, 0.4, 0.26, 0.46, 0.3, 0.98, b=0.05, seg=3, rot=(math.radians(-8), 0, 0))
    for sx in (-1, 1):
        a.bx("fabric_blue", sx * 0.35 if sx > 0 else -0.45, 0.45 if sx > 0 else -0.35, -0.42, 0.42, 0.2, 0.62, b=0.04, seg=3)
    a.legs("wood_dark", -0.4, 0.4, -0.38, 0.38, 0.08, t=0.05, b=0.004)

def sofa(a, seats, mat):
    w = 0.72 * seats + 0.3
    d = 0.9
    a.bx("wood_dark", -w / 2, w / 2, -d / 2 + 0.05, d / 2 - 0.05, 0.08, 0.2, b=0.01)
    a.bx(mat, -w / 2, w / 2, -d / 2, d / 2, 0.2, 0.34, b=0.04, seg=3)
    a.bx(mat, -w / 2 + 0.15, w / 2 - 0.15, d / 2 - 0.22, d / 2, 0.34, 0.85, b=0.05, seg=3)
    for i in range(seats):
        x0 = -w / 2 + 0.15 + i * 0.72
        a.bx(mat, x0 + 0.01, x0 + 0.71, -d / 2 + 0.02, d / 2 - 0.22, 0.34, 0.5, b=0.045, seg=3)
        a.bx(mat, x0 + 0.03, x0 + 0.69, d / 2 - 0.36, d / 2 - 0.2, 0.5, 0.82, b=0.05, seg=3, rot=(math.radians(-10), 0, 0))
    for sx in (-1, 1):
        x0 = -w / 2 if sx < 0 else w / 2 - 0.15
        a.bx(mat, x0, x0 + 0.15, -d / 2, d / 2, 0.2, 0.62, b=0.05, seg=3)
    a.legs("wood_dark", -w / 2 + 0.05, w / 2 - 0.05, -d / 2 + 0.05, d / 2 - 0.05, 0.08, t=0.05, b=0.004)

@asset("04_Living", "Sofa_2Seat")
def _(a):
    sofa(a, 2, "fabric_grey")

@asset("04_Living", "Sofa_3Seat")
def _(a):
    sofa(a, 3, "fabric_grey")
    for i, c in enumerate(("fabric_red", "fabric_green")):
        a.bx(c, -0.7 + i * 1.3, -0.7 + i * 1.3 + 0.4, -0.2, 0.15, 0.5, 0.88, b=0.06, seg=3, rot=(math.radians(-12), 0, math.radians(8 - 16 * i)))

def table(a, w, d, h, top_mat="wood_oak", leg_mat="wood_dark", leg_t=0.07):
    a.bx(top_mat, -w / 2, w / 2, -d / 2, d / 2, h - 0.04, h, b=0.01)
    a.bx(leg_mat, -w / 2 + 0.06, w / 2 - 0.06, -d / 2 + 0.06, d / 2 - 0.06, h - 0.1, h - 0.04, b=0.005)
    a.legs(leg_mat, -w / 2 + 0.05, w / 2 - 0.05, -d / 2 + 0.05, d / 2 - 0.05, h - 0.04, t=leg_t, b=0.006)

@asset("04_Living", "Table_Dining_1.6m")
def _(a):
    table(a, 1.6, 0.9, 0.75)

@asset("04_Living", "Table_Dining_Round")
def _(a):
    a.cyl("wood_oak", 0.55, 0.71, 0.75, segs=32)
    a.cyl("wood_dark", 0.06, 0.05, 0.71, segs=16)
    a.cyl("wood_dark", 0.3, 0.0, 0.05, r2=0.12, segs=24)

@asset("04_Living", "Table_Coffee")
def _(a):
    a.bx("wood_oak", -0.55, 0.55, -0.3, 0.3, 0.38, 0.42, b=0.01)
    a.bx("wood_dark", -0.5, 0.5, -0.25, 0.25, 0.14, 0.17, b=0.006)
    a.legs("wood_dark", -0.52, 0.52, -0.27, 0.27, 0.38, t=0.05, b=0.004)

@asset("04_Living", "Table_Side")
def _(a):
    a.cyl("wood_oak", 0.25, 0.46, 0.5, segs=28)
    a.cyl("metal_black", 0.02, 0.0, 0.46, segs=12)
    a.cyl("metal_black", 0.16, 0.0, 0.02, segs=24)

@asset("04_Living", "TV_Stand_With_TV")
def _(a):
    a.bx("wood_dark", -0.8, 0.8, -0.2, 0.2, 0.1, 0.5, b=0.01)
    for sx in (-1, 1):
        a.bx("wood_oak", sx * 0.4 - 0.37, sx * 0.4 + 0.37, -0.205, -0.19, 0.15, 0.45, b=0.006)
        a.bx("metal_chrome", sx * 0.4 - 0.02 * sx, sx * 0.4 - 0.02 * sx + 0.01, -0.225, -0.205, 0.28, 0.36, b=0.003)
    a.legs("wood_dark", -0.78, 0.78, -0.18, 0.18, 0.1, t=0.04, b=0.003)
    a.bx("metal_black", -0.04, 0.04, -0.03, 0.03, 0.5, 0.58, b=0.004)
    a.bx("metal_black", -0.2, 0.2, -0.13, 0.13, 0.5, 0.52, b=0.004)
    a.bx("screen", -0.62, 0.62, -0.04, 0.0, 0.58, 1.3, b=0.006)

@asset("04_Living", "Bookshelf_Tall")
def _(a):
    w, d, h = 0.9, 0.3, 1.9
    a.bx("wood_dark", -w / 2, -w / 2 + 0.03, -d / 2, d / 2, 0, h, b=0.005)
    a.bx("wood_dark", w / 2 - 0.03, w / 2, -d / 2, d / 2, 0, h, b=0.005)
    a.bx("wood_dark", -w / 2, w / 2, d / 2 - 0.01, d / 2, 0, h, b=0)
    for z in (0.08, 0.45, 0.82, 1.19, 1.56, h - 0.03):
        a.bx("wood_dark", -w / 2, w / 2, -d / 2, d / 2, z, z + 0.03, b=0.005)
    rnd = random.Random(7)
    mats = ("book_a", "book_b", "book_c", "book_d")
    for z in (0.11, 0.48, 0.85, 1.22):
        x = -w / 2 + 0.05
        while x < w / 2 - 0.1:
            bw = rnd.uniform(0.025, 0.05)
            bh = rnd.uniform(0.22, 0.32)
            if rnd.random() < 0.15:
                x += 0.08
                continue
            a.bx(rnd.choice(mats), x, x + bw, -d / 2 + 0.04, d / 2 - 0.03, z, z + bh, b=0.002, seg=1)
            x += bw + 0.002

@asset("04_Living", "Sideboard_Low")
def _(a):
    a.bx("wood_oak", -0.8, 0.8, -0.22, 0.22, 0.12, 0.78, b=0.01)
    for sx in (-1, 0, 1):
        a.bx("wood_light", sx * 0.52 - 0.25, sx * 0.52 + 0.25, -0.225, -0.215, 0.18, 0.72, b=0.004)
        a.bx("brass", sx * 0.52 - 0.02, sx * 0.52 + 0.02, -0.245, -0.225, 0.42, 0.48, b=0.004)
    a.legs("wood_dark", -0.75, 0.75, -0.18, 0.18, 0.12, t=0.04, b=0.003)

@asset("04_Living", "Fireplace")
def _(a):
    a.bx("stone", -0.9, 0.9, 0.0, 0.4, 0.0, 1.2, b=0.01)
    a.bx("screen", -0.5, 0.5, -0.0, 0.05, 0.1, 0.8, b=0.005)
    a.bx("wood_dark", -1.0, 1.0, -0.05, 0.45, 1.2, 1.28, b=0.01)
    a.bx("stone", -0.7, 0.7, 0.1, 0.4, 1.28, WH, b=0.01)

# ----------------------------------------------------------------------------
# 05 — CHAMBRE
# ----------------------------------------------------------------------------
def bed(a, w, mat, pillows):
    L = 2.1
    a.bx("wood_dark", -w / 2, w / 2, -L / 2, L / 2, 0.12, 0.3, b=0.01)
    a.bx("wood_dark", -w / 2, w / 2, L / 2 - 0.08, L / 2, 0.12, 1.1, b=0.01)           # tête de lit
    a.bx("wood_dark", -w / 2, w / 2, -L / 2, -L / 2 + 0.06, 0.12, 0.55, b=0.01)        # pied de lit
    a.bx("mattress", -w / 2 + 0.04, w / 2 - 0.04, -L / 2 + 0.06, L / 2 - 0.08, 0.3, 0.52, b=0.04, seg=3)
    a.bx(mat, -w / 2 + 0.02, w / 2 - 0.02, -L / 2 + 0.06, 0.45, 0.46, 0.57, b=0.04, seg=3)   # couverture
    n = pillows
    pw = (w - 0.2) / n
    for i in range(n):
        x0 = -w / 2 + 0.1 + i * pw
        a.bx("trim_white", x0 + 0.02, x0 + pw - 0.02, 0.62, 0.98, 0.52, 0.64, b=0.06, seg=3, rot=(math.radians(8), 0, 0))
    a.legs("wood_dark", -w / 2, w / 2, -L / 2, L / 2, 0.12, t=0.06, b=0.004)

@asset("05_Bedroom", "Bed_Single")
def _(a):
    bed(a, 0.95, "fabric_blue", 1)

@asset("05_Bedroom", "Bed_Double")
def _(a):
    bed(a, 1.6, "fabric_beige", 2)

@asset("05_Bedroom", "Nightstand")
def _(a):
    a.bx("wood_oak", -0.25, 0.25, -0.2, 0.2, 0.12, 0.55, b=0.008)
    a.bx("wood_light", -0.22, 0.22, -0.205, -0.195, 0.16, 0.34, b=0.004)
    a.bx("wood_light", -0.22, 0.22, -0.205, -0.195, 0.36, 0.52, b=0.004)
    for z in (0.25, 0.44):
        a.bx("brass", -0.03, 0.03, -0.225, -0.2, z - 0.01, z + 0.01, b=0.003)
    a.legs("wood_dark", -0.23, 0.23, -0.18, 0.18, 0.12, t=0.035, b=0.003)

@asset("05_Bedroom", "Wardrobe_2Door")
def _(a):
    w, d, h = 1.2, 0.6, 2.0
    a.bx("wood_oak", -w / 2, w / 2, -d / 2, d / 2, 0.08, h, b=0.01)
    a.bx("wood_dark", -w / 2 - 0.01, w / 2 + 0.01, -d / 2 - 0.01, d / 2 + 0.01, 0, 0.08, b=0.004)
    a.bx("wood_dark", -w / 2 - 0.02, w / 2 + 0.02, -d / 2 - 0.02, d / 2 + 0.02, h, h + 0.05, b=0.008)
    for sx in (-1, 1):
        a.bx("wood_light", sx * 0.3 - 0.285, sx * 0.3 + 0.285, -d / 2 - 0.02, -d / 2, 0.14, h - 0.06, b=0.006)
        a.bx("wood_oak", sx * 0.3 - 0.2, sx * 0.3 + 0.2, -d / 2 - 0.028, -d / 2 - 0.02, 0.4, 1.4, b=0.004)
        a.bx("brass", sx * 0.04 - 0.01, sx * 0.04 + 0.01, -d / 2 - 0.05, -d / 2 - 0.02, 0.9, 1.15, b=0.004)

@asset("05_Bedroom", "Dresser_3Drawer")
def _(a):
    a.bx("wood_oak", -0.5, 0.5, -0.25, 0.25, 0.1, 0.85, b=0.008)
    for i in range(3):
        z0 = 0.14 + i * 0.235
        a.bx("wood_light", -0.46, 0.46, -0.262, -0.25, z0, z0 + 0.215, b=0.005)
        a.bx("brass", -0.08, 0.08, -0.29, -0.262, z0 + 0.1, z0 + 0.12, b=0.004)
    a.legs("wood_dark", -0.47, 0.47, -0.22, 0.22, 0.1, t=0.045, b=0.003)

@asset("05_Bedroom", "Desk_With_Drawers")
def _(a):
    a.bx("wood_oak", -0.7, 0.7, -0.35, 0.35, 0.72, 0.76, b=0.008)
    a.bx("wood_dark", 0.3, 0.7, -0.33, 0.33, 0.0, 0.72, b=0.008)
    for i in range(3):
        z0 = 0.06 + i * 0.22
        a.bx("wood_light", 0.32, 0.68, -0.345, -0.33, z0, z0 + 0.2, b=0.004)
        a.bx("brass", 0.44, 0.56, -0.37, -0.345, z0 + 0.09, z0 + 0.11, b=0.003)
    a.bx("wood_dark", -0.7, -0.64, -0.33, 0.33, 0.0, 0.72, b=0.006)

@asset("05_Bedroom", "Chair_Office")
def _(a):
    for i in range(5):
        ang = i * 2 * math.pi / 5
        cx, cy = -math.sin(ang) * 0.15, math.cos(ang) * 0.15
        a.bx("metal_black", cx - 0.03, cx + 0.03, cy - 0.15, cy + 0.15, 0.06, 0.09, b=0.003, rot=(0, 0, ang))
        a.sphere("metal_black", 0.03, -math.sin(ang) * 0.3, math.cos(ang) * 0.3, 0.04)
    a.cyl("metal_chrome", 0.025, 0.09, 0.45, segs=12)
    a.bx("fabric_grey", -0.25, 0.25, -0.25, 0.25, 0.45, 0.52, b=0.03, seg=3)
    a.bx("fabric_grey", -0.24, 0.24, 0.2, 0.26, 0.55, 0.95, b=0.03, seg=3, rot=(math.radians(-6), 0, 0))

# ----------------------------------------------------------------------------
# 06 — CUISINE
# ----------------------------------------------------------------------------
def counter(a, w, top="stone"):
    a.bx("wood_dark", -w / 2, w / 2, -0.28, 0.3, 0.0, 0.1, b=0.005)
    a.bx("trim_white", -w / 2, w / 2, -0.3, 0.3, 0.1, 0.86, b=0.006)
    a.bx(top, -w / 2 - 0.0, w / 2, -0.33, 0.3, 0.86, 0.9, b=0.008)

@asset("06_Kitchen", "Kitchen_Base_60")
def _(a):
    counter(a, 0.6)
    a.bx("wood_light", -0.28, 0.28, -0.312, -0.3, 0.14, 0.82, b=0.005)
    a.bx("metal_chrome", -0.15, 0.15, -0.34, -0.312, 0.75, 0.78, b=0.004)

@asset("06_Kitchen", "Kitchen_Base_Drawers_60")
def _(a):
    counter(a, 0.6)
    for i in range(3):
        z0 = 0.14 + i * 0.235
        a.bx("wood_light", -0.28, 0.28, -0.312, -0.3, z0, z0 + 0.215, b=0.005)
        a.bx("metal_chrome", -0.12, 0.12, -0.34, -0.312, z0 + 0.1, z0 + 0.12, b=0.004)

@asset("06_Kitchen", "Kitchen_Sink_120")
def _(a):
    w = 1.2
    counter(a, w)
    a.bx("wood_light", -0.58, -0.02, -0.312, -0.3, 0.14, 0.82, b=0.005)
    a.bx("wood_light", 0.02, 0.58, -0.312, -0.3, 0.14, 0.82, b=0.005)
    for sx in (-1, 1):
        a.bx("metal_chrome", sx * 0.3 - 0.12, sx * 0.3 + 0.12, -0.34, -0.312, 0.75, 0.78, b=0.004)
    a.bx("metal_chrome", -0.5, -0.05, -0.2, 0.2, 0.895, 0.905, b=0.006)
    a.bx("metal_black", -0.46, -0.09, -0.16, 0.16, 0.897, 0.91, b=0.004)
    a.cyl("metal_chrome", 0.018, 0.9, 1.1, cx=-0.27, cy=0.22, segs=12)
    a.bx("metal_chrome", -0.29, -0.25, 0.1, 0.25, 1.08, 1.12, b=0.004)

@asset("06_Kitchen", "Kitchen_Cooker_60")
def _(a):
    a.bx("metal_chrome", -0.3, 0.3, -0.31, 0.3, 0.0, 0.9, b=0.008)
    a.bx("metal_black", -0.27, 0.27, -0.32, -0.31, 0.12, 0.68, b=0.004)
    a.bx("glass", -0.24, 0.24, -0.325, -0.32, 0.2, 0.6, b=0)
    a.bx("metal_chrome", -0.2, 0.2, -0.36, -0.32, 0.72, 0.75, b=0.004)
    a.bx("metal_black", -0.3, 0.3, -0.31, 0.3, 0.9, 0.915, b=0.004)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.cyl("metal_black", 0.07, 0.915, 0.93, cx=sx * 0.14, cy=sy * 0.1, segs=20)
            a.cyl("metal_chrome", 0.03, 0.93, 0.94, cx=sx * 0.14, cy=sy * 0.1, segs=14)
    for i in range(4):
        a.cyl("metal_black", 0.022, 0.78, 0.82, cx=-0.21 + i * 0.14, cy=-0.31, rot=(math.pi / 2, 0, 0), segs=14)

@asset("06_Kitchen", "Kitchen_Wall_Cabinet_60")
def _(a):
    a.bx("trim_white", -0.3, 0.3, -0.15, 0.15, 1.45, 2.1, b=0.006)
    a.bx("wood_light", -0.28, 0.28, -0.162, -0.15, 1.48, 2.07, b=0.005)
    a.bx("metal_chrome", -0.12, 0.12, -0.19, -0.162, 1.55, 1.58, b=0.004)

@asset("06_Kitchen", "Kitchen_Hood")
def _(a):
    a.bx("metal_chrome", -0.3, 0.3, -0.25, 0.2, 1.55, 1.62, b=0.006)
    bm = a.bm
    a.bx("metal_chrome", -0.12, 0.12, -0.05, 0.2, 1.62, WH, b=0.006)
    a.bx("metal_black", -0.2, 0.2, -0.2, 0.15, 1.54, 1.55, b=0.003)

@asset("06_Kitchen", "Fridge_Tall")
def _(a):
    a.bx("ceramic", -0.35, 0.35, -0.33, 0.33, 0.03, 1.85, b=0.03, seg=3)
    a.bx("metal_chrome", -0.35, 0.35, -0.335, -0.33, 1.2, 1.205, b=0.002)
    a.bx("metal_chrome", 0.25, 0.28, -0.37, -0.33, 1.3, 1.7, b=0.005)
    a.bx("metal_chrome", 0.25, 0.28, -0.37, -0.33, 0.9, 1.15, b=0.005)
    a.bx("metal_black", -0.3, 0.3, -0.3, 0.3, 0.0, 0.03, b=0)

@asset("06_Kitchen", "Stool_Kitchen")
def _(a):
    a.bx("wood_light", -0.2, 0.2, -0.2, 0.2, 0.42, 0.46, b=0.01)
    a.legs("wood_light", -0.18, 0.18, -0.18, 0.18, 0.42, t=0.04, b=0.004)
    a.bx("wood_light", -0.16, 0.16, -0.16, 0.16, 0.2, 0.23, b=0.004)

# ----------------------------------------------------------------------------
# 07 — SALLE DE BAIN
# ----------------------------------------------------------------------------
@asset("07_Bathroom", "Bathtub")
def _(a):
    L, W, H, t = 1.7, 0.75, 0.55, 0.06
    a.bx("ceramic", -W / 2, W / 2, -L / 2, -L / 2 + t, 0.1, H, b=0.02, seg=3)
    a.bx("ceramic", -W / 2, W / 2, L / 2 - t, L / 2, 0.1, H, b=0.02, seg=3)
    a.bx("ceramic", -W / 2, -W / 2 + t, -L / 2, L / 2, 0.1, H, b=0.02, seg=3)
    a.bx("ceramic", W / 2 - t, W / 2, -L / 2, L / 2, 0.1, H, b=0.02, seg=3)
    a.bx("ceramic", -W / 2, W / 2, -L / 2, L / 2, 0.1, 0.16, b=0.02, seg=3)
    a.bx("metal_chrome", -0.02, 0.02, L / 2 - 0.02, L / 2 + 0.05, 0.55, 0.6, b=0.003)
    a.cyl("metal_chrome", 0.015, 0.55, 0.7, cx=0.0, cy=L / 2 + 0.03, segs=10)
    a.bx("metal_chrome", -0.02, 0.02, L / 2 + 0.0, L / 2 + 0.2, 0.68, 0.72, b=0.003)
    a.cyl("metal_black", 0.03, 0.16, 0.162, cx=0, cy=-L / 2 + 0.2, segs=16)
    for sx in (-1, 1):
        for sy in (-1, 1):
            a.cyl("metal_chrome", 0.03, 0.0, 0.1, cx=sx * (W / 2 - 0.08), cy=sy * (L / 2 - 0.1), segs=10)

@asset("07_Bathroom", "Toilet")
def _(a):
    a.bx("ceramic", -0.2, 0.2, 0.12, 0.34, 0.4, 0.82, b=0.025, seg=3)         # réservoir
    a.bx("ceramic", -0.19, 0.19, 0.0, 0.34, 0.2, 0.4, b=0.03, seg=3)           # base
    a.cyl("ceramic", 0.19, 0.4, 0.45, cx=0.0, cy=-0.1, segs=24)               # cuvette
    a.cyl("ceramic", 0.17, 0.2, 0.4, cx=0.0, cy=-0.1, segs=20, r2=0.19)
    a.cyl("trim_white", 0.18, 0.45, 0.47, cx=0.0, cy=-0.1, segs=24)
    a.cyl("metal_chrome", 0.025, 0.82, 0.84, cx=0, cy=0.24, segs=12)

@asset("07_Bathroom", "Sink_Pedestal")
def _(a):
    a.cyl("ceramic", 0.07, 0.0, 0.7, cx=0.0, cy=0.12, segs=16)
    a.bx("ceramic", -0.3, 0.3, -0.07, 0.25, 0.7, 0.88, b=0.04, seg=3)
    a.cyl("metal_chrome", 0.012, 0.88, 0.99, cx=0, cy=0.2, segs=10)
    a.bx("metal_chrome", -0.012, 0.012, 0.1, 0.2, 0.97, 0.99, b=0.002)

@asset("07_Bathroom", "Mirror_Cabinet")
def _(a):
    a.bx("trim_white", -0.35, 0.35, 0.0, 0.14, 1.2, 1.95, b=0.008)
    a.bx("mirror", -0.32, 0.32, -0.005, 0.0, 1.23, 1.92, b=0)

# ----------------------------------------------------------------------------
# 08 — ÉCLAIRAGE & DÉCO
# ----------------------------------------------------------------------------
@asset("08_Lights_Decor", "Lamp_Floor")
def _(a):
    a.cyl("metal_black", 0.16, 0.0, 0.02, segs=24)
    a.cyl("metal_black", 0.012, 0.02, 1.5, segs=10)
    a.cyl("shade", 0.28, 1.35, 1.7, r2=0.19, segs=28, open_ends=True)
    a.sphere("bulb", 0.06, 0, 0, 1.55)

@asset("08_Lights_Decor", "Lamp_Table")
def _(a):
    a.cyl("ceramic", 0.09, 0.0, 0.02, segs=20)
    a.sphere("ceramic", 0.11, 0, 0, 0.17, sz=1.2)
    a.cyl("brass", 0.012, 0.28, 0.4, segs=10)
    a.cyl("shade", 0.17, 0.3, 0.5, r2=0.12, segs=24, open_ends=True)
    a.sphere("bulb", 0.04, 0, 0, 0.42)

@asset("08_Lights_Decor", "Light_Pendant")
def _(a):
    a.cyl("metal_black", 0.01, 1.7, WH, segs=8)
    a.cyl("metal_black", 0.06, WH - 0.02, WH, segs=16)
    a.cyl("metal_black", 0.22, 1.5, 1.72, r2=0.04, segs=28, open_ends=True)
    a.sphere("bulb", 0.07, 0, 0, 1.58)

@asset("08_Lights_Decor", "Light_Ceiling_Flush")
def _(a):
    a.cyl("trim_white", 0.2, 2.7, WH, segs=28)
    a.cyl("bulb", 0.17, 2.69, 2.7, segs=28)

@asset("08_Lights_Decor", "Light_Wall_Sconce")
def _(a):
    a.bx("metal_black", -0.05, 0.05, 0.0, 0.02, 1.7, 1.9, b=0.004)
    a.bx("brass", -0.015, 0.015, 0.02, 0.15, 1.78, 1.81, b=0.003)
    a.cyl("shade", 0.09, 1.78, 1.96, cx=0, cy=0.15, r2=0.06, segs=20, open_ends=True)
    a.sphere("bulb", 0.035, 0, 0.15, 1.82)

@asset("08_Lights_Decor", "Rug_Rect_2x3")
def _(a):
    a.bx("rug_a", -1.0, 1.0, -1.5, 1.5, 0.0, 0.015, b=0.004)
    a.bx("rug_b", -0.9, 0.9, -1.4, 1.4, 0.015, 0.017, b=0)
    a.bx("rug_c", -0.6, 0.6, -1.1, 1.1, 0.017, 0.019, b=0)

@asset("08_Lights_Decor", "Rug_Round_1.6m")
def _(a):
    a.cyl("rug_c", 0.8, 0.0, 0.015, segs=48)
    a.cyl("rug_b", 0.65, 0.015, 0.017, segs=48)
    a.cyl("rug_a", 0.35, 0.017, 0.019, segs=48)

def frame(a, w, h, canv):
    """Cadre mural : pivot en bas au centre, face avant vers -Y."""
    t = 0.04
    z0 = 0.0
    a.bx("wood_dark", -w / 2, w / 2, 0.0, 0.03, z0, z0 + t, b=0.004)
    a.bx("wood_dark", -w / 2, w / 2, 0.0, 0.03, z0 + h - t, z0 + h, b=0.004)
    a.bx("wood_dark", -w / 2, -w / 2 + t, 0.0, 0.03, z0, z0 + h, b=0.004)
    a.bx("wood_dark", w / 2 - t, w / 2, 0.0, 0.03, z0, z0 + h, b=0.004)
    a.bx("trim_white", -w / 2 + t, w / 2 - t, 0.016, 0.022, z0 + t, z0 + h - t, b=0)                       # fond
    a.bx(canv, -w / 2 + t + 0.04, w / 2 - t - 0.04, 0.008, 0.016, z0 + t + 0.04, z0 + h - t - 0.04, b=0)  # toile
    a.bx("canvas_c", -w / 6, w / 6, 0.004, 0.008, z0 + h / 3, z0 + h * 0.75, b=0)                         # motif

@asset("08_Lights_Decor", "Frame_Portrait")
def _(a):
    frame(a, 0.5, 0.7, "canvas_a")

@asset("08_Lights_Decor", "Frame_Landscape")
def _(a):
    frame(a, 0.9, 0.6, "canvas_b")

@asset("08_Lights_Decor", "Mirror_Wall_Round")
def _(a):
    a.hcyl("brass", 0.4, "y", 0.0, 0.035, 0.0, 0.4, segs=40)
    a.hcyl("mirror", 0.36, "y", -0.004, 0.04, 0.0, 0.4, segs=40)

@asset("08_Lights_Decor", "Clock_Wall")
def _(a):
    zc = 0.22
    a.hcyl("wood_dark", 0.22, "y", 0.0, 0.04, 0.0, zc, segs=32)
    a.hcyl("trim_white", 0.19, "y", -0.004, 0.046, 0.0, zc, segs=32)
    for i in range(12):
        ang = i * math.pi / 6
        a.bx("metal_black", math.sin(ang) * 0.16 - 0.006, math.sin(ang) * 0.16 + 0.006, -0.01, -0.004,
             zc + math.cos(ang) * 0.16 - 0.006, zc + math.cos(ang) * 0.16 + 0.006, b=0.001, seg=1)
    a.bx("metal_black", -0.008, 0.008, -0.016, -0.01, zc, zc + 0.12, b=0.001, seg=1)
    a.bx("metal_black", 0.0, 0.1, -0.022, -0.016, zc - 0.008, zc + 0.008, b=0.001, seg=1)

@asset("08_Lights_Decor", "Plant_Pot_Large")
def _(a):
    a.cyl("terracotta", 0.2, 0.0, 0.4, r2=0.27, segs=24)
    a.cyl("terracotta", 0.28, 0.4, 0.45, segs=24)
    a.cyl("soil", 0.25, 0.4, 0.44, segs=24)
    rnd = random.Random(3)
    for i in range(14):
        ang = i * 2 * math.pi / 14 + rnd.uniform(-0.2, 0.2)
        r = rnd.uniform(0.05, 0.16)
        h = rnd.uniform(0.7, 1.15)
        a.sphere("leaf" if i % 2 else "leaf_b", 0.12, math.cos(ang) * r, math.sin(ang) * r, h, sx=0.6, sy=0.25, sz=1.4, segs=10)
        a.cyl("leaf", 0.008, 0.44, h - 0.12, cx=math.cos(ang) * r * 0.5, cy=math.sin(ang) * r * 0.5, segs=6)

@asset("08_Lights_Decor", "Plant_Small")
def _(a):
    a.cyl("ceramic", 0.07, 0.0, 0.13, r2=0.09, segs=20)
    a.cyl("soil", 0.08, 0.12, 0.14, segs=20)
    for i in range(7):
        ang = i * 2 * math.pi / 7
        a.sphere("leaf_b" if i % 2 else "leaf", 0.06, math.cos(ang) * 0.04, math.sin(ang) * 0.04, 0.22 + 0.02 * (i % 3), sx=0.5, sy=0.3, sz=1.5, segs=8)

@asset("08_Lights_Decor", "Vase_Flowers")
def _(a):
    a.cyl("ceramic", 0.06, 0.0, 0.2, r2=0.09, segs=20)
    a.cyl("glass", 0.055, 0.2, 0.27, r2=0.04, segs=20, open_ends=True)
    for i, (dx, dy, c) in enumerate(((0.0, 0.0, "fabric_red"), (0.04, 0.02, "canvas_a"), (-0.04, 0.0, "fabric_red"), (0.0, -0.04, "canvas_a"))):
        a.cyl("leaf", 0.004, 0.15, 0.4 + 0.03 * i, cx=dx, cy=dy, segs=6)
        a.sphere(c, 0.035, dx, dy, 0.42 + 0.03 * i, segs=10)

@asset("08_Lights_Decor", "Books_Stack")
def _(a):
    z = 0.0
    for i, (mat, w, d, h, rot) in enumerate((("book_b", 0.26, 0.19, 0.04, 0.0), ("book_a", 0.24, 0.17, 0.03, 0.15),
                                             ("book_c", 0.22, 0.16, 0.035, -0.1), ("book_d", 0.2, 0.15, 0.025, 0.2))):
        a.bx(mat, -w / 2, w / 2, -d / 2, d / 2, z, z + h, b=0.003, rot=(0, 0, rot))
        z += h

@asset("08_Lights_Decor", "Curtains_Pair_1.6m")
def _(a):
    a.hcyl("brass", 0.014, "x", -0.95, 0.95, 0.0, 2.35)
    for sx in (-1, 1):
        a.sphere("brass", 0.03, sx * 0.95, 0.0, 2.35)
        for i in range(6):
            xa = sx * (0.35 + i * 0.1) if sx > 0 else -(0.35 + (i + 1) * 0.1)
            y = 0.035 if i % 2 else -0.01
            a.bx("fabric_beige", xa, xa + 0.1, y - 0.03, y + 0.03, 0.02, 2.33, b=0.012, seg=2)
        a.bx("brass", sx * 0.6 - 0.025, sx * 0.6 + 0.025, -0.08, -0.02, 0.9, 0.96, b=0.003)

@asset("08_Lights_Decor", "Cushion_Square")
def _(a):
    a.bx("fabric_red", -0.22, 0.22, -0.07, 0.07, 0.0, 0.44, b=0.06, seg=3)

@asset("08_Lights_Decor", "Coat_Rack_Wall")
def _(a):
    a.bx("wood_dark", -0.5, 0.5, 0.0, 0.025, 1.6, 1.72, b=0.006)
    for i in range(4):
        x = -0.38 + i * 0.253
        a.hcyl("brass", 0.012, "y", 0.025, 0.1, x, 1.66, segs=10)
        a.sphere("brass", 0.024, x, 0.105, 1.66)

@asset("08_Lights_Decor", "Shelf_Wall_1m")
def _(a):
    a.bx("wood_oak", -0.5, 0.5, 0.0, 0.22, 0.0, 0.03, b=0.006)
    for sx in (-0.35, 0.35):
        a.bx("metal_black", sx - 0.01, sx + 0.01, 0.0, 0.2, -0.12, 0.0, b=0.002)
        a.bx("metal_black", sx - 0.01, sx + 0.01, 0.0, 0.01, -0.12, 0.0, b=0.002)

# ----------------------------------------------------------------------------
# 09 — EXTÉRIEUR
# ----------------------------------------------------------------------------
@asset("09_Exterior", "Fence_Section_2m")
def _(a):
    for x in (-0.95, 0.95):
        a.bx("trim_white", x - 0.05, x + 0.05, -0.05, 0.05, 0.0, 1.1, b=0.006)
        a.bx("trim_white", x - 0.06, x + 0.06, -0.06, 0.06, 1.1, 1.14, b=0.006)
    for z in (0.3, 0.75):
        a.bx("trim_white", -0.95, 0.95, 0.05, 0.085, z, z + 0.08, b=0.004)
    for i in range(10):
        x = -0.85 + i * 0.19
        a.bx("trim_white", x, x + 0.1, 0.085, 0.11, 0.05, 1.0, b=0.004)

@asset("09_Exterior", "Gate_Garden")
def _(a):
    for x in (-0.45, 0.45):
        a.bx("trim_white", x - 0.04, x + 0.04, -0.04, 0.04, 0.0, 1.0, b=0.005)
    for z in (0.25, 0.7):
        a.bx("trim_white", -0.45, 0.45, -0.02, 0.02, z, z + 0.07, b=0.004)
    for i in range(7):
        x = -0.38 + i * 0.127
        a.bx("trim_white", x, x + 0.07, 0.02, 0.04, 0.05, 0.92, b=0.003)
    a.bx("metal_black", 0.3, 0.38, -0.04, -0.02, 0.5, 0.58, b=0.003)

@asset("09_Exterior", "Column_Porch")
def _(a):
    a.bx("trim_white", -0.17, 0.17, -0.17, 0.17, 0.0, 0.18, b=0.01)
    a.cyl("trim_white", 0.12, 0.18, 2.55, segs=24, r2=0.11)
    a.bx("trim_white", -0.17, 0.17, -0.17, 0.17, 2.55, 2.75, b=0.01)

@asset("09_Exterior", "Mailbox")
def _(a):
    a.cyl("wood_dark", 0.03, 0.0, 1.0, segs=10)
    a.bx("metal_black", -0.12, 0.12, -0.1, 0.18, 1.0, 1.22, b=0.03, seg=3)
    a.bx("fabric_red", 0.12, 0.125, -0.1, -0.03, 1.1, 1.2, b=0.003)

@asset("09_Exterior", "Bench_Garden")
def _(a):
    for i in range(5):
        a.bx("wood_light", -0.7, 0.7, -0.22 + i * 0.09, -0.15 + i * 0.09, 0.44, 0.47, b=0.004)
    for i in range(4):
        a.bx("wood_light", -0.7, 0.7, 0.22, 0.25, 0.5 + i * 0.1, 0.57 + i * 0.1, b=0.004, rot=(math.radians(-10), 0, 0))
    for sx in (-0.62, 0.62):
        a.bx("metal_black", sx - 0.02, sx + 0.02, -0.22, 0.28, 0.0, 0.44, b=0.003)
        a.bx("metal_black", sx - 0.02, sx + 0.02, 0.22, 0.28, 0.44, 0.93, b=0.003)

@asset("09_Exterior", "Path_Stone_Tile")
def _(a):
    a.bx("stone", -0.45, 0.45, -0.45, 0.45, 0.0, 0.04, b=0.012)

# ----------------------------------------------------------------------------
# Génération, export, mise en page
# ----------------------------------------------------------------------------
def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    _MAT_CACHE.clear()


def make_all():
    colls = {}
    objs = {}
    for category, name, fn in REGISTRY:
        if category not in colls:
            c = bpy.data.collections.new(category)
            bpy.context.scene.collection.children.link(c)
            colls[category] = c
        a = Asset(name)
        fn(a)
        o = a.build(colls[category])
        o["hk_category"] = category
        objs[name] = o
    return colls, objs


def export_assets(objs):
    for name, o in objs.items():
        cat = o["hk_category"]
        for fmt in ("FBX", "GLB"):
            os.makedirs(os.path.join(OUT, "Individual_Assets", fmt, cat), exist_ok=True)
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        base = os.path.join(OUT, "Individual_Assets")
        try:
            bpy.ops.export_scene.fbx(filepath=os.path.join(base, "FBX", cat, name + ".fbx"), use_selection=True,
                                     apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False, axis_forward="-Y", axis_up="Z")
        except Exception as e:
            print("FBX", name, e)
        try:
            bpy.ops.export_scene.gltf(filepath=os.path.join(base, "GLB", cat, name + ".glb"), export_format="GLB", use_selection=True, export_yup=True)
        except Exception as e:
            print("GLB", name, e)


def layout_library(colls, objs):
    """Range les assets en grille (une rangée par catégorie) et les marque comme Assets Blender."""
    row_y = 0.0
    for cat, coll in colls.items():
        x, row_depth = 0.0, 0.0
        for o in sorted(coll.objects, key=lambda o: o.name):
            lb = [Vector(c) for c in o.bound_box]
            lx0, lx1 = min(p.x for p in lb), max(p.x for p in lb)
            ly0, ly1 = min(p.y for p in lb), max(p.y for p in lb)
            o.location = (x - lx0, row_y - ly0, 0.0)
            x += (lx1 - lx0) + 0.8
            row_depth = max(row_depth, ly1 - ly0)
            try:
                o.asset_mark()
                o.asset_data.description = "Home Builder Kit - " + cat
                o.asset_data.tags.new(cat[3:])
            except Exception as e:
                print("asset_mark", o.name, e)
        row_y += max(row_depth, 3.0) + 3.0


if __name__ == "__main__":
    reset_scene()
    os.makedirs(OUT, exist_ok=True)
    colls, objs = make_all()
    print(len(objs), "assets")
    export_assets(objs)
    layout_library(colls, objs)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "HomeBuilderKit_Library.blend"))
