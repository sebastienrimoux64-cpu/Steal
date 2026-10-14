"""
Arbres en VOXEL (style cubes) : pommier, olivier, baobab, acacia, sapin enneigé, arbre de jungle.

    python tools/trees_voxel/make_voxel_trees.py [nom ...] [--render]      # -> TreesVoxel/

1 voxel = 12,5 cm. Un .blend (+ .fbx + .glb) par arbre, TreesVoxel_All.blend (tous alignés) et des aperçus.
Repère : Z vers le haut, origine = pied du tronc (centre), l'arbre est dans le plan X/Y/Z.
"""
import math
import os
import sys

import bpy
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "TreesVoxel")
VS = 0.125
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "nature_real"))
import studio_real as S

QUADS = {
    (1, 0, 0): ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
    (-1, 0, 0): ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
    (0, 1, 0): ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    (0, -1, 0): ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
    (0, 0, 1): ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    (0, 0, -1): ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
}


def hsh(x, y, z, s=0):
    n = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (s * 2654435761)
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def lin(c):
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def hexc(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# ------------------------------------------------------------------ palettes (sRGB)
P = dict(
    bark1="#5a3b22", bark2="#6e4a2c", bark3="#47301c", bark4="#826040", grey1="#8f7a60", grey2="#7a6650", grey3="#a8927a", grey4="#5e4d3b",
    g1="#2f7a2b", g2="#3c9334", g3="#4fae3f", g4="#69c455", g5="#86d26b",
    dg1="#1f4d2a", dg2="#276335", dg3="#2f7a40", dg4="#3a9150",
    ol1="#6f8a4c", ol2="#869f62", ol3="#9db37a", ol4="#58703b",
    ac1="#8cab2e", ac2="#a5c038", ac3="#bfd44a", ac4="#6f9024",
    jg1="#14451f", jg2="#1c5a29", jg3="#267335", jg4="#33904a", jg5="#4aab5c",
    red="#d1262a", red2="#a61b20", apple_g="#a7c840", olive="#2b2418", olive2="#3b4a1c",
    snow="#f4f8ff", snow2="#dbe8f5", snow3="#c4d6ea", fruit="#6b5a47", fruit2="#857260",
    moss="#3d6b2a", moss2="#52863a", liane="#3a2a18", liane2="#2a3d1a", brom="#c93a5b", brom2="#e0a030", flower="#f2d34a",
)
_mats = {}


def mat(key):
    if key in _mats:
        return _mats[key]
    m = bpy.data.materials.new("vox_" + key)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    c = lin(hexc(P[key])) + (1.0,)
    b.inputs["Base Color"].default_value = c
    b.inputs["Roughness"].default_value = 0.85
    b.inputs["Specular IOR Level"].default_value = 0.25
    m.diffuse_color = c
    _mats[key] = m
    return m


class G:
    """Grille de voxels : (x, y, z) -> clé de palette."""

    def __init__(self):
        self.v = {}

    def put(self, p, key):
        self.v[p] = key

    def ball(self, c, r, fn, ry=None, rz=None, erode=0.0, seed=0, keep=None):
        rx = r
        ry = ry if ry is not None else r
        rz = rz if rz is not None else r
        cx, cy, cz = c
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
                for z in range(int(cz - rz) - 1, int(cz + rz) + 2):
                    d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 + ((z - cz) / rz) ** 2
                    if d > 1.0:
                        continue
                    if erode and d > 0.55 and hsh(x, y, z, seed) < erode * (d - 0.45) * 2.2:
                        continue
                    if keep is not None and not keep(x, y, z):
                        continue
                    self.v[(x, y, z)] = fn(x, y, z)

    def line(self, p0, p1, r0, r1, fn, flat=False):
        n = int(max(abs(p1[i] - p0[i]) for i in range(3)) * 1.6) + 1
        for i in range(n + 1):
            t = i / n
            c = [p0[k] + (p1[k] - p0[k]) * t for k in range(3)]
            r = r0 + (r1 - r0) * t
            ri = int(math.ceil(r))
            for dx in range(-ri, ri + 1):
                for dy in range(-ri, ri + 1):
                    for dz in range(-ri, ri + 1):
                        if dx * dx + dy * dy + dz * dz <= r * r + 0.25:
                            p = (int(round(c[0])) + dx, int(round(c[1])) + dy, int(round(c[2])) + dz)
                            self.v[p] = fn(*p)


def pick(keys, x, y, z, s=0):
    return keys[min(len(keys) - 1, int(hsh(x, y, z, s) * len(keys)))]


def shade_green(keys, z0, z1, x, y, z, noise=0.35, s=1):
    t = (z - z0) / max(1, z1 - z0) + (hsh(x, y, z, s) - 0.5) * noise
    return keys[max(0, min(len(keys) - 1, int(t * len(keys))))]


# ------------------------------------------------------------------ arbres
def bark_fn(keys):
    return lambda x, y, z: pick(keys, x, y, z, 3)


def pommier():
    g = G()
    bark = bark_fn(["bark1", "bark2", "bark1", "bark3", "bark4"])
    # tronc évasé + 5 branches
    for z in range(0, 15):
        r = 3.4 - 0.1 * z + (1.2 if z < 3 else 0)
        g.ball((0, 0, z), r, bark, ry=r, rz=0.6)
    branches = []
    for i in range(6):
        a = i * 1.05 + 0.4
        tip = (math.cos(a) * 11, math.sin(a) * 11, 25 + 3 * (i % 2))
        g.line((0, 0, 11), tip, 1.8, 0.9, bark)
        branches.append(tip)
    leaf = lambda x, y, z: shade_green(["g1", "g2", "g3", "g4", "g5"], 16, 40, x, y, z)
    g.ball((0, 0, 30), 10, leaf, ry=10, rz=7.5, erode=0.5, seed=1)
    for i, (bx, by, bz) in enumerate(branches):
        g.ball((bx * 0.9, by * 0.9, bz + 3), 7.2, leaf, rz=5.8, erode=0.55, seed=10 + i)
    g.ball((0, 0, 37), 6, leaf, rz=4.5, erode=0.5, seed=33)
    # pommes sur la face externe basse du feuillage
    n = 0
    for (x, y, z), k in list(g.v.items()):
        if k in ("g1", "g2", "g3", "g4", "g5") and z > 21 and ((x, y, z - 1) not in g.v or (x, y - 1, z) not in g.v) and hsh(x, y, z, 9) < 0.09 and n < 70:
            tgt = (x, y, z - 1) if (x, y, z - 1) not in g.v else (x, y - 1, z)
            g.v[tgt] = "red" if hsh(x, y, z, 8) < 0.75 else "apple_g"
            n += 1
    return g


def olivier():
    g = G()
    bark = bark_fn(["grey1", "grey2", "grey1", "grey4", "grey3"])
    path = []
    for z in range(0, 16):
        a = z * 0.28
        path.append((math.cos(a) * 2.2 * min(1, z / 6), math.sin(a) * 2.2 * min(1, z / 6), z))
    for i in range(len(path) - 1):
        r = 3.4 - 0.13 * i + (1.4 if i < 3 else 0)
        g.line(path[i], path[i + 1], r, r - 0.13, bark)
    limbs = []
    for i in range(4):
        a = i * 1.57 + 0.6
        mid = (path[-1][0] + math.cos(a + 0.5) * 6, path[-1][1] + math.sin(a + 0.5) * 6, 21)
        tip = (path[-1][0] + math.cos(a) * 11, path[-1][1] + math.sin(a) * 11, 25 + 2 * (i % 2))
        g.line(path[-1], mid, 2.1, 1.5, bark)
        g.line(mid, tip, 1.5, 0.9, bark)
        limbs.append(tip)
    leaf = lambda x, y, z: shade_green(["ol4", "ol1", "ol2", "ol3"], 17, 32, x, y, z, noise=0.5)
    g.ball((path[-1][0], path[-1][1], 27), 9.5, leaf, ry=9.5, rz=5.5, erode=0.6, seed=4)
    for i, (bx, by, bz) in enumerate(limbs):
        g.ball((bx, by, bz + 2), 6.8, leaf, rz=4.4, erode=0.6, seed=20 + i)
    n = 0
    for (x, y, z), k in list(g.v.items()):
        if k.startswith("ol") and z > 20 and (x, y, z - 1) not in g.v and hsh(x, y, z, 12) < 0.07 and n < 40:
            g.v[(x, y, z - 1)] = "olive" if hsh(x, y, z, 5) < 0.6 else "olive2"
            n += 1
    return g


def baobab():
    g = G()
    bark = lambda x, y, z: pick(["grey3", "grey1", "grey2", "grey1"], x, y // 1, z, 3) if (z % 5) else "grey4"
    H = 38
    for z in range(0, H):
        t = z / H
        r = 12.5 * (1 + 0.35 * math.exp(-t * 11)) * (0.9 + 0.22 * math.sin(math.pi * t ** 0.72) - 0.3 * t ** 2.2)
        g.ball((0, 0, z), r, lambda x, y, z: bark(x, y, z), rz=0.65, erode=0.0)
    leaf = lambda x, y, z: shade_green(["g1", "g2", "g3", "g4"], 38, 52, x, y, z)
    tips = []
    for i in range(8):
        a = i * 0.785 + 0.3
        d = 8 + (i % 2) * 3
        p0 = (math.cos(a) * 5, math.sin(a) * 5, 36)
        tip = (math.cos(a) * (d + 8), math.sin(a) * (d + 8), 49 + (i % 3) * 2)
        g.line(p0, tip, 3.0, 1.2, bark_fn(["bark2", "bark1", "bark4", "bark3"]))
        tips.append(tip)
    for i, (bx, by, bz) in enumerate(tips):
        g.ball((bx, by, bz + 1), 5.2, leaf, rz=3.6, erode=0.5, seed=7 + i)
    for i, (bx, by, bz) in enumerate(tips[::2]):
        for k in range(4):
            g.put((int(bx) + (k % 2), int(by), int(bz) - 3 - k), "fruit" if k < 3 else "fruit2")
            g.put((int(bx) + (k % 2), int(by) + 1, int(bz) - 3 - k), "fruit")
    return g


def acacia():
    g = G()
    bark = bark_fn(["bark3", "bark1", "bark3", "bark2"])
    pts = [(0, 0, 0), (1, 0.5, 8), (3, 1, 16), (5, 1.5, 24)]
    for a, b in zip(pts, pts[1:]):
        g.line(a, b, 2.3 - 0.0, 2.0, bark)
    top = pts[-1]
    tips = []
    for i in range(5):
        a = i * 1.26 + 0.3
        tip = (top[0] + math.cos(a) * 15, top[1] + math.sin(a) * 15, 36 + (i % 2) * 2)
        g.line(top, tip, 1.8, 0.9, bark)
        tips.append(tip)
    leaf = lambda x, y, z: shade_green(["ac4", "ac1", "ac2", "ac3"], 34, 44, x, y, z, noise=0.4)
    # canopée en parasol : disques fins et étagés
    for i, (bx, by, bz) in enumerate(tips + [(top[0], top[1], 38)]):
        g.ball((bx, by, bz + 2), 11 if i < 5 else 13, leaf, ry=11 if i < 5 else 13, rz=2.4, erode=0.55, seed=40 + i)
    g.ball((top[0] + 1, top[1], 42), 8, leaf, rz=2.2, erode=0.5, seed=60)
    return g


def sapin():
    g = G()
    bark = bark_fn(["bark1", "bark3", "bark2"])
    H = 78
    for z in range(0, H + 1):
        r = 2.2 * (1 - z / H) + 0.5
        g.ball((0, 0, z), r, bark, rz=0.6)
    leaf = lambda x, y, z: shade_green(["dg1", "dg2", "dg3", "dg4"], 6, 78, x, y, z, noise=0.4)
    tiers = 12
    for i in range(tiers):
        f = i / (tiers - 1)
        z0 = 8 + i * 5.7
        R = 15 * (1 - f) ** 0.9 + 2.2
        for k in range(8):
            zz = z0 + k
            rr = R * (1 - k * 0.115) + (1.0 if k == 0 else 0)
            rr = max(rr, 0.8)
            for x in range(-int(rr) - 2, int(rr) + 3):
                for y in range(-int(rr) - 2, int(rr) + 3):
                    d = math.hypot(x, y)
                    ang = math.atan2(y, x)
                    rs = rr * (1 + 0.1 * math.sin(7 * ang + i * 1.3))
                    if d <= rs and not (k == 0 and d < 1.5):
                        g.v[(x, y, int(zz))] = leaf(x, y, int(zz))
    # neige : tout voxel dont le dessus est libre
    for (x, y, z), k in list(g.v.items()):
        if k.startswith("dg") and (x, y, z + 1) not in g.v and hsh(x, y, z, 21) < 0.72:
            g.v[(x, y, z)] = pick(["snow", "snow", "snow2", "snow3"], x, y, z, 2)
    # flocons sur les bords
    for (x, y, z), k in list(g.v.items()):
        if k.startswith("snow") and hsh(x, y, z, 5) < 0.18 and (x, y, z - 1) in g.v and g.v[(x, y, z - 1)].startswith("dg"):
            g.v[(x, y, z - 1)] = "snow3"
    return g


def jungle():
    g = G()
    bark = bark_fn(["grey2", "grey4", "grey2", "grey1"])
    H = 74
    for z in range(0, H):
        t = z / H
        r = 4.6 * (1 - 0.3 * t) * (1 + 0.7 * math.exp(-t * 9))
        g.ball((0, 0, z), r, lambda x, y, z: ("moss" if hsh(x, y, z, 6) < 0.22 and z < 40 else pick(["grey2", "grey4", "grey2", "grey1"], x, y, z, 3)), rz=0.65)
    # contreforts (ailerons)
    for k in range(6):
        a = k * 1.047 + 0.2
        for s in range(0, 16):
            r = 4 + s
            h = int(20 * (1 - s / 16) ** 2.2) + 1
            for z in range(0, h):
                x, y = int(round(math.cos(a) * r)), int(round(math.sin(a) * r))
                g.put((x, y, z), "moss" if hsh(x, y, z, 4) < 0.18 else "grey4")
                g.put((x + (1 if abs(math.sin(a)) > 0.5 else 0), y + (1 if abs(math.cos(a)) > 0.5 else 0), z), "grey2")
    leaf = lambda x, y, z: shade_green(["jg1", "jg2", "jg3", "jg4", "jg5"], 62, 90, x, y, z, noise=0.5)
    for i in range(7):
        a = i * 0.9
        tip = (math.cos(a) * 17, math.sin(a) * 17, 80)
        g.line((0, 0, 68), tip, 2.2, 1.0, bark_fn(["grey2", "grey4", "grey1"]))
        g.ball((tip[0], tip[1], tip[2] + 3), 10, leaf, rz=4.3, erode=0.55, seed=70 + i)
    g.ball((0, 0, 82), 14, leaf, rz=5.5, erode=0.55, seed=90)
    g.ball((0, 0, 88), 8, leaf, rz=4.0, erode=0.5, seed=91)
    # lianes pendantes
    for k in range(10):
        a = k * 0.62 + 0.3
        x0, y0 = int(math.cos(a) * 9), int(math.sin(a) * 9)
        for z in range(76, 4, -1):
            w = int(round(math.sin(z * 0.17 + k) * 1.2))
            g.put((x0 + w, y0 + int(round(math.cos(z * 0.13 + k))), z), "liane" if hsh(x0, y0, z, k) < 0.7 else "liane2")
    # bromélias et fleurs sur le tronc / branches
    for k in range(7):
        z = 28 + k * 6
        a = k * 2.1
        x, y = int(math.cos(a) * 5), int(math.sin(a) * 5)
        for dx, dy, dz in ((0, 0, 0), (1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (0, 0, 2)):
            g.put((x + dx, y + dy, z + dz), "brom" if (dx + dy + dz) % 2 else "brom2")
    return g


TREES = {"pommier": ("arbre-pommier", pommier), "olivier": ("arbre-olivier", olivier), "baobab": ("arbre-baobab", baobab),
         "acacia": ("arbre-acacia", acacia), "sapin-enneige": ("arbre-sapin-enneige", sapin), "jungle": ("arbre-jungle", jungle)}


def to_object(name, grid, coll, origin=(0.0, 0.0, 0.0)):
    keys = sorted({k for k in grid.v.values()})
    midx = {k: i for i, k in enumerate(keys)}
    verts, faces, fm = [], [], []
    for (x, y, z), k in grid.v.items():
        for d, quad in QUADS.items():
            if (x + d[0], y + d[1], z + d[2]) in grid.v:
                continue
            base = len(verts)
            for (a, b, c) in quad:
                verts.append(((x + a) * VS + origin[0], (y + b) * VS + origin[1], (z + c) * VS + origin[2]))
            faces.append((base, base + 1, base + 2, base + 3))
            fm.append(midx[k])
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    for k in keys:
        me.materials.append(mat(k))
    me.polygons.foreach_set("material_index", fm)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def export(ob, name):
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    for fn, kw in ((bpy.ops.export_scene.fbx, dict(filepath=os.path.join(OUT, f"{name}.fbx"), use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)),
                   (bpy.ops.export_scene.gltf, dict(filepath=os.path.join(OUT, f"{name}.glb"), export_format="GLB", use_selection=True, export_yup=True))):
        try:
            fn(**kw)
        except Exception as e:
            print("export", name, e)


def flat_ground(size=800.0):
    me = bpy.data.meshes.new("sol")
    h = size / 2
    me.from_pydata([(-h, -h, -0.0), (h, -h, 0), (h, h, 0), (-h, h, 0)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("sol", me)
    m = bpy.data.materials.new("sol")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexc("#4f8f3a")) + (1,)
    b.inputs["Roughness"].default_value = 0.95
    o.data.materials.append(m)
    bpy.context.scene.collection.objects.link(o)
    return o


def stage(res, samples, cam_loc, cam_tgt, lens=50, snow=False):
    S.cycles(samples, res)
    S.sky()
    g = flat_ground()
    if snow:
        g.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = lin(hexc("#e8f0fa")) + (1,)
    S.camera(cam_loc, cam_tgt, lens)


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    names = [a for a in args if a in TREES] or list(TREES)
    render = "--render" in args
    os.makedirs(os.path.join(OUT, "Apercus"), exist_ok=True)
    grids = {}
    lineup_only = "--lineup" in args
    for key in names:
        name, fn = TREES[key]
        grids[key] = fn()
        if lineup_only:
            continue
        S.reset()
        _mats.clear()
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
        ob = to_object(name, grids[key], coll)
        ob["voxel_size_m"] = VS
        xs = [p[0] for p in grids[key].v]
        zs = [p[2] for p in grids[key].v]
        H = (max(zs) + 1) * VS
        W = (max(xs) - min(xs) + 1) * VS
        d = max(H * 1.9, W * 1.7)
        stage((1200, 1200), 48, (d * 0.35, -d, H * 0.52), (0, 0, H * 0.46), 45, snow=(key == "sapin-enneige"))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"{name}.blend"), compress=True)
        print(f"{name}: {len(ob.data.polygons)} faces, {len(grids[key].v)} voxels, {H:.1f} m")
        export(ob, name)
        if render:
            bpy.context.scene.render.filepath = os.path.join(OUT, "Apercus", f"{name}.png")
            bpy.ops.render.render(write_still=True)
    if len(names) == len(TREES):
        S.reset()
        _mats.clear()
        coll = bpy.data.collections.new("ArbresVoxel")
        bpy.context.scene.collection.children.link(coll)
        x = 0.0
        for key in TREES:
            g = grids[key]
            xs = [p[0] for p in g.v]
            w = (max(xs) - min(xs) + 1) * VS
            ob = to_object(TREES[key][0], g, coll, origin=(x + w / 2, 0, 0))
            x += w + 4.0
        total = x
        stage((2400, 900), 48, (total / 2, -total * 1.2, 7.0), (total / 2, 0, 4.6), 40)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "TreesVoxel_All.blend"), compress=True)
        if render:
            bpy.context.scene.render.filepath = os.path.join(OUT, "Apercus", "Lineup.png")
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
