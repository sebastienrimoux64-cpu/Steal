"""Fruits du démon (One Piece) en cubes : 24 fruits en voxels avec leurs spirales en relief.

Usage :
    python tools/make_fruits_demon.py SORTIE.blend [SORTIE.glb]

Chaque fruit est un seul maillage de cubes (voxels de 18 cm, seules les faces visibles sont créées,
couleurs stockées en attribut de couleur « Col »). La peau est couverte de spirales : plusieurs
centres de tourbillon sont placés sur la surface (un face à la caméra), chacun dessine une spirale
d'Archimède ; les voxels de la spirale sont recolorés ET surélevés d'un cube, donc le motif est un vrai
relief cubique. Tige recourbée et petite feuille en voxels. Les fruits sont posés sur des présentoirs en
gradins, avec leur nom en relief.

Les couleurs sont inspirées de l'œuvre (elles varient selon les sources et selon l'anime / le manga).
"""
import math
import random
import sys

VOX = 0.18            # taille d'un cube (u)
R = 12                # rayon d'un fruit, en cubes
RR = int(R * 1.45) + 2

# nom, forme, couleur de la peau, couleur de la spirale
FRUITS = [
    ("Gomu Gomu no Mi", "round", (0.45, 0.17, 0.55), (0.80, 0.47, 0.87)),
    ("Mera Mera no Mi", "oval", (0.96, 0.46, 0.10), (0.78, 0.13, 0.05)),
    ("Hie Hie no Mi", "round", (0.55, 0.82, 0.96), (0.90, 0.97, 1.00)),
    ("Pika Pika no Mi", "apple", (0.98, 0.85, 0.20), (1.00, 0.97, 0.62)),
    ("Yami Yami no Mi", "squat", (0.12, 0.08, 0.18), (0.38, 0.17, 0.55)),
    ("Magu Magu no Mi", "pear", (0.70, 0.14, 0.07), (1.00, 0.52, 0.10)),
    ("Gura Gura no Mi", "oval", (0.76, 0.86, 0.95), (0.28, 0.44, 0.72)),
    ("Ope Ope no Mi", "round", (0.38, 0.80, 0.75), (0.88, 0.97, 0.88)),
    ("Goro Goro no Mi", "gourd", (0.96, 0.92, 0.45), (0.50, 0.62, 1.00)),
    ("Suna Suna no Mi", "squat", (0.86, 0.70, 0.40), (0.58, 0.42, 0.20)),
    ("Hana Hana no Mi", "apple", (0.96, 0.60, 0.76), (0.74, 0.22, 0.48)),
    ("Bara Bara no Mi", "lobed", (0.88, 0.45, 0.60), (0.48, 0.14, 0.28)),
    ("Doku Doku no Mi", "pear", (0.55, 0.25, 0.66), (0.28, 0.72, 0.30)),
    ("Mochi Mochi no Mi", "squat", (0.98, 0.80, 0.70), (0.85, 0.45, 0.45)),
    ("Yomi Yomi no Mi", "oval", (0.92, 0.28, 0.40), (1.00, 0.72, 0.76)),
    ("Kage Kage no Mi", "gourd", (0.15, 0.15, 0.21), (0.48, 0.42, 0.58)),
    ("Hobby Hobby no Mi", "round", (0.80, 0.10, 0.10), (0.45, 0.03, 0.05)),
    ("Neko Neko no Mi", "lobed", (0.88, 0.65, 0.25), (0.35, 0.20, 0.08)),
    ("Tori Tori no Mi", "pear", (0.25, 0.55, 0.95), (1.00, 0.62, 0.15)),
    ("Zou Zou no Mi", "squat", (0.55, 0.58, 0.62), (0.28, 0.30, 0.36)),
    ("Bomu Bomu no Mi", "apple", (0.45, 0.30, 0.20), (0.95, 0.55, 0.15)),
    ("Horu Horu no Mi", "oval", (0.95, 0.70, 0.85), (0.58, 0.28, 0.64)),
    ("Nikyu Nikyu no Mi", "round", (0.90, 0.55, 0.35), (0.58, 0.28, 0.14)),
    ("Hito Hito no Mi Nika", "lobed", (0.97, 0.97, 0.92), (0.95, 0.78, 0.28)),
]


# ------------------------------------------------------------------------------- formes
def inside(shape, x, y, z):
    r2 = x * x + y * y + z * z
    if shape == "round":
        return r2 <= R * R
    if shape == "oval":
        return (x * x + y * y) / (0.9 * R) ** 2 + z * z / (1.12 * R) ** 2 <= 1
    if shape == "squat":
        if x * x + y * y + (z - 0.98 * R) ** 2 <= (0.3 * R) ** 2:      # creux en haut
            return False
        return (x * x + y * y) / (1.1 * R) ** 2 + z * z / (0.82 * R) ** 2 <= 1
    if shape == "apple":
        if x * x + y * y + (z - 1.02 * R) ** 2 <= (0.42 * R) ** 2:
            return False
        return r2 <= R * R
    if shape == "pear":
        d1 = x * x + y * y + (z + 0.25 * R) ** 2
        d2 = x * x + y * y + (z - 0.62 * R) ** 2
        return (0.92 * R) ** 2 / (d1 + 0.01) + (0.58 * R) ** 2 / (d2 + 0.01) >= 1.05 and abs(z) < 1.3 * R
    if shape == "gourd":
        d1 = x * x + y * y + (z + 0.42 * R) ** 2
        d2 = x * x + y * y + (z - 0.55 * R) ** 2
        return (0.80 * R) ** 2 / (d1 + 0.01) + (0.66 * R) ** 2 / (d2 + 0.01) >= 1.15 and abs(z) < 1.3 * R
    if shape == "lobed":
        ang = math.atan2(y, x)
        return math.sqrt(r2) <= R * (1 + 0.09 * math.cos(5 * ang) * (1 - (z / R) ** 2))
    raise ValueError(shape)


def build_solid(shape):
    S = set()
    for x in range(-RR, RR + 1):
        for y in range(-RR, RR + 1):
            for z in range(-RR, RR + 1):
                if inside(shape, x, y, z):
                    S.add((x, y, z))
    return S


NEIGH = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]


# ------------------------------------------------------------------------------- spirales
def unit(v):
    n = math.sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / n for c in v)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def swirl_centers(rng):
    """Centres de tourbillon sur la sphère : le premier fait face à la caméra (-Y)."""
    cs = [(unit((rng.uniform(-0.25, 0.25), -1.0, rng.uniform(0.1, 0.4))), 1.05, 1)]
    k = 6
    off = rng.random() * 6.28
    for i in range(k):
        z = 1 - 2 * (i + 0.5) / k
        a = i * 2.39996 + off
        rr = math.sqrt(max(0.0, 1 - z * z))
        d = unit((rr * math.cos(a), rr * math.sin(a), z))
        if dot(d, cs[0][0]) > 0.55:          # pas trop près du grand tourbillon
            continue
        cs.append((d, rng.uniform(0.62, 0.9), rng.choice((-1, 1))))
    out = []
    for c, rad, h in cs:
        up = (0.0, 0.0, 1.0) if abs(c[2]) < 0.9 else (1.0, 0.0, 0.0)
        u = unit(cross(c, up))
        v = cross(c, u)
        out.append((c, rad, h, u, v))
    return out


TURNS, WIDTH = 2.4, 0.30


def in_spiral(n, centers):
    """Vrai si la direction n tombe sur un bras de spirale."""
    best = None
    for c, rad, h, u, v in centers:
        r = math.acos(max(-1.0, min(1.0, dot(n, c))))
        if r < rad:
            rn = r / rad
            if best is None or rn < best[0]:
                best = (rn, h, math.atan2(dot(n, v), dot(n, u)))
    if best is None:
        return False
    rn, h, a = best
    if rn < 0.07:
        return True
    s = rn * TURNS - h * a / (2 * math.pi)
    return (s - math.floor(s)) < WIDTH and rn > 0.10


def shade(col, k):
    return tuple(max(0.0, min(1.0, c * k)) for c in col)


# ------------------------------------------------------------------------------- un fruit
def make_fruit(shape, base, line, seed):
    rng = random.Random(seed)
    S = build_solid(shape)
    centers = swirl_centers(rng)
    vox = {}
    raised = {}
    for p in S:
        if all((p[0] + d[0], p[1] + d[1], p[2] + d[2]) in S for d in NEIGH):
            continue                                                  # intérieur : invisible
        n = unit((p[0], p[1], p[2] - 0.1 * R))
        jit = 1 + rng.uniform(-0.05, 0.05)
        if in_spiral(n, centers):
            vox[p] = shade(line, jit)
            ax = max(range(3), key=lambda i: abs(n[i]))              # relief : un cube de plus vers l'extérieur
            q = list(p)
            q[ax] += 1 if n[ax] > 0 else -1
            q = tuple(q)
            if q not in S:
                raised[q] = shade(line, jit * 1.08)
        else:
            vox[p] = shade(base, jit)
    vox.update(raised)
    # tige recourbée + petite feuille
    zt = max(z for (x, y, z) in S if x == 0 and y == 0)
    green = (0.28, 0.50, 0.18)
    stem = [(0, 0, 0), (0, 0, 1), (0, 0, 2), (0, 0, 3), (1, 0, 4), (2, 0, 4), (3, 0, 3), (3, 0, 2)]
    for i, (x, y, z) in enumerate(stem):
        for dx, dy in (((0, 0), (1, 0), (0, 1), (1, 1)) if i < 2 else ((0, 0),)):
            vox[(x + dx, y + dy, zt + z)] = shade(green, 1 + rng.uniform(-0.08, 0.08))
    for x, y in ((-1, 0), (-2, 0), (-1, 1), (-2, 1), (-3, 1)):
        vox[(x, y, zt + 2 + (1 if x < -1 else 0))] = shade((0.36, 0.64, 0.22), 1 + rng.uniform(-0.08, 0.08))
    return vox


# ------------------------------------------------------------------------------- maillage
FACES = {
    (1, 0, 0): [(1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)],
    (-1, 0, 0): [(0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)],
    (0, 1, 0): [(0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)],
    (0, -1, 0): [(0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)],
    (0, 0, 1): [(0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)],
    (0, 0, -1): [(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)],
}


def voxel_mesh(name, vox):
    """Maillage de cubes : uniquement les faces exposées ; couleur par face (attribut « Col »)."""
    import bmesh
    import bpy
    bm = bmesh.new()
    col = bm.loops.layers.color.new("Col")
    for (x, y, z), c in vox.items():
        for d, quad in FACES.items():
            if (x + d[0], y + d[1], z + d[2]) in vox:
                continue
            vs = [bm.verts.new(((x + a - 0.5) * VOX, (y + b - 0.5) * VOX, (z + e - 0.5) * VOX)) for a, b, e in quad]
            f = bm.faces.new(vs)
            for loop in f.loops:
                loop[col] = (*c, 1.0)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def vertex_color_material():
    import bpy
    m = bpy.data.materials.new("Fruit_voxel")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.5
    a = nt.nodes.new("ShaderNodeVertexColor")
    a.layer_name = "Col"
    nt.links.new(a.outputs["Color"], b.inputs["Base Color"])
    return m


def simple_material(name, color, rough=0.7, emission=0.0):
    import bpy
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def add_box(name, lo, hi, mat):
    import bpy
    verts = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def wood_floor():
    import bpy
    m = bpy.data.materials.new("Parquet")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    b.inputs["Roughness"].default_value = 0.8
    co = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.inputs["Color1"].default_value = (0.20, 0.12, 0.07, 1)
    br.inputs["Color2"].default_value = (0.16, 0.09, 0.05, 1)
    br.inputs["Mortar"].default_value = (0.05, 0.03, 0.02, 1)
    br.inputs["Scale"].default_value = 0.5
    br.inputs["Mortar Size"].default_value = 0.01
    br.inputs["Brick Width"].default_value = 3.0
    br.inputs["Row Height"].default_value = 0.5
    nt.links.new(co.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    return m


# ------------------------------------------------------------------------------- scène
COLS, ROWS, DX, DY = 6, 4, 7.4, 8.4


def build(dst, glb=None):
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = 1920, 1080
    sc.view_settings.view_transform = "Standard"

    fmat = vertex_color_material()
    wood = simple_material("Presentoir", (0.30, 0.17, 0.09), 0.7)
    top = simple_material("Presentoir_dessus", (0.42, 0.25, 0.13), 0.6)
    gold = simple_material("Or", (1.0, 0.78, 0.30), 0.35, emission=0.6)

    floor = bpy.data.meshes.new("Sol")
    floor.from_pydata([(-120, -80, 0), (120, -80, 0), (120, 120, 0), (-120, 120, 0)], [], [(0, 1, 2, 3)])
    floor.materials.append(wood_floor())
    sc.collection.objects.link(bpy.data.objects.new("Sol", floor))

    coll = bpy.data.collections.new("Fruits")
    sc.collection.children.link(coll)
    fruit_objs = []
    for i, (name, shape, base, line) in enumerate(FRUITS):
        row, colx = divmod(i, COLS)
        wx = (colx - (COLS - 1) / 2) * DX
        wy = row * DY
        h = 1.5 + 2.2 * row                              # gradins : chaque rangée est plus haute
        add_box(f"Presentoir_{i + 1:02d}", (wx - 3.2, wy - 3.2, 0), (wx + 3.2, wy + 3.2, h), wood)
        add_box(f"Plateau_{i + 1:02d}", (wx - 3.35, wy - 3.35, h), (wx + 3.35, wy + 3.35, h + 0.18), top)
        vox = make_fruit(shape, base, line, seed=1000 + i * 17)
        me = voxel_mesh(f"Fruit_{name}", vox)
        me.materials.append(fmat)
        ob = bpy.data.objects.new(f"Fruit_{name}", me)
        zmin = min(z for (_, _, z) in vox) - 0.5
        ob.location = (wx, wy, h + 0.18 - zmin * VOX)
        ob.rotation_euler = (0, 0, math.radians((i * 37 % 41) - 20))
        coll.objects.link(ob)
        fruit_objs.append(ob)
        # nom en relief, posé sur le plateau
        cu = bpy.data.curves.new(f"Nom_{i + 1:02d}", "FONT")
        cu.body = name
        cu.size = 0.58
        cu.extrude = 0.04
        cu.align_x = "CENTER"
        cu.materials.append(gold)
        txt = bpy.data.objects.new(f"Nom_{i + 1:02d}", cu)
        txt.location = (wx, wy - 2.95, h + 0.2)          # à plat sur le plateau, devant le fruit
        sc.collection.objects.link(txt)

    # lumière : soleil chaud de face, ciel, et une grande lampe douce
    sun_d = bpy.data.lights.new("Soleil", "SUN")
    sun_d.energy = 4.0
    sun_d.color = (1.0, 0.92, 0.82)
    sun = bpy.data.objects.new("Soleil", sun_d)
    sun.rotation_euler = (math.radians(48), math.radians(6), math.radians(24))
    sc.collection.objects.link(sun)
    fill_d = bpy.data.lights.new("Lampe", "AREA")
    fill_d.energy = 3500
    fill_d.size = 40
    fill = bpy.data.objects.new("Lampe", fill_d)
    fill.location = (0, -30, 26)
    fill.rotation_euler = (math.radians(60), 0, 0)
    sc.collection.objects.link(fill)
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.48, 0.58, 0.78, 1)
    bg.inputs["Strength"].default_value = 0.9

    # caméras : vue d'ensemble (par défaut) et gros plan sur le premier fruit
    cam_d = bpy.data.cameras.new("Camera_Ensemble")
    cam_d.lens = 35
    cam = bpy.data.objects.new("Camera_Ensemble", cam_d)
    cam.location = (0, -33, 44)
    cam.rotation_euler = (math.radians(46), 0, 0)
    sc.collection.objects.link(cam)
    sc.camera = cam
    cam2_d = bpy.data.cameras.new("Camera_GrosPlan")
    cam2_d.lens = 60
    cam2 = bpy.data.objects.new("Camera_GrosPlan", cam2_d)
    cam2.location = (-18.5, -13.0, 5.6)
    cam2.rotation_euler = (math.radians(88), 0, 0)
    sc.collection.objects.link(cam2)

    bpy.ops.wm.save_as_mainfile(filepath=dst)
    print(f"OK: {dst} ({len(FRUITS)} fruits)")
    if glb:
        try:
            for o in bpy.data.objects:
                o.select_set(False)
            for o in fruit_objs:
                o.select_set(True)
            bpy.ops.export_scene.gltf(filepath=glb, use_selection=True, export_apply=True,
                                      export_vertex_color="ACTIVE", export_format="GLB")
            print(f"OK: {glb}")
        except Exception as e:                           # l'exporteur glTF peut manquer
            print("glb non exporte :", e)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    build(args[-2] if len(args) > 1 else args[-1], args[-1] if len(args) > 1 else None)
