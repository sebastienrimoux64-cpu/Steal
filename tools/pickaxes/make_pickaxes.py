"""
Pioches en voxel (8 matières) : bois, cuivre, fer, or, diamant, uranium, rubis, lapis-lazuli.

    python tools/pickaxes/make_pickaxes.py        # -> Pickaxes/

Pour chaque pioche : <Nom>.blend (+ .fbx et .glb), plus Pickaxes_All.blend (les 8 côte à côte) et des aperçus.
Repère : la pioche est dans le plan X (droite) / Z (haut), épaisseur sur Y ; l'origine est la POIGNÉE (point de prise).
Taille : 20 voxels de côté, 1 voxel = 4 cm (pioche d'environ 80 cm).
"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shape

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "Pickaxes")
VS = 0.04
GRIP = (3.0, 3.0)       # voxel (x, y) pris comme origine (la poignée)


def rgb(*c):
    return tuple(c)


WOOD_HANDLE = dict(ramp=[rgb(0.30, 0.19, 0.10), rgb(0.46, 0.30, 0.15), rgb(0.60, 0.42, 0.23), rgb(0.70, 0.52, 0.30)], metal=0.0, rough=0.85)
BIND = [rgb(0.20, 0.13, 0.07), rgb(0.32, 0.21, 0.11), rgb(0.42, 0.28, 0.15), rgb(0.5, 0.35, 0.2)]

# nom : ramp (sombre, moyen, clair, reflet), métal, rugosité, émission (par niveau), bruit, éclats (couleur, proba, métal)
MATERIALS = {
    "Wood": dict(ramp=[rgb(0.50, 0.35, 0.19), rgb(0.70, 0.52, 0.29), rgb(0.82, 0.65, 0.40), rgb(0.90, 0.77, 0.54)], metal=0.0, rough=0.85, emit=(0, 0, 0, 0), noise=0.30,
                 fleck=(rgb(0.42, 0.28, 0.15), 0.12, 0.0), label="bois"),
    "Copper": dict(ramp=[rgb(0.45, 0.20, 0.12), rgb(0.78, 0.42, 0.24), rgb(0.93, 0.60, 0.38), rgb(1.0, 0.80, 0.62)], metal=0.75, rough=0.42, emit=(0, 0, 0, 0), noise=0.12,
                   fleck=(rgb(0.28, 0.72, 0.58), 0.06, 0.2), label="cuivre"),
    "Iron": dict(ramp=[rgb(0.36, 0.37, 0.40), rgb(0.62, 0.63, 0.66), rgb(0.82, 0.83, 0.85), rgb(0.96, 0.97, 0.98)], metal=0.8, rough=0.36, emit=(0, 0, 0, 0), noise=0.10,
                 fleck=None, label="fer"),
    "Gold": dict(ramp=[rgb(0.62, 0.42, 0.06), rgb(0.93, 0.70, 0.14), rgb(1.0, 0.85, 0.30), rgb(1.0, 0.96, 0.70)], metal=0.85, rough=0.3, emit=(0, 0, 0, 0), noise=0.10,
                 fleck=None, label="or"),
    "Diamond": dict(ramp=[rgb(0.06, 0.45, 0.52), rgb(0.20, 0.80, 0.82), rgb(0.55, 0.97, 0.95), rgb(0.92, 1.0, 1.0)], metal=0.0, rough=0.08, emit=(0.15, 0.4, 0.8, 1.6), noise=0.22,
                    fleck=(rgb(0.95, 1.0, 1.0), 0.08, 0.0), label="diamant"),
    "Uranium": dict(ramp=[rgb(0.10, 0.42, 0.06), rgb(0.30, 0.82, 0.12), rgb(0.62, 1.0, 0.28), rgb(0.90, 1.0, 0.60)], metal=0.0, rough=0.25, emit=(0.8, 1.6, 2.6, 4.5), noise=0.26,
                    fleck=(rgb(0.04, 0.18, 0.03), 0.07, 0.0), label="uranium vert"),
    "Ruby": dict(ramp=[rgb(0.45, 0.02, 0.10), rgb(0.85, 0.06, 0.18), rgb(1.0, 0.32, 0.40), rgb(1.0, 0.75, 0.78)], metal=0.0, rough=0.08, emit=(0.1, 0.35, 0.7, 1.4), noise=0.22,
                 fleck=(rgb(1.0, 0.85, 0.88), 0.07, 0.0), label="rubis rouge"),
    "Lapis": dict(ramp=[rgb(0.06, 0.10, 0.45), rgb(0.14, 0.26, 0.80), rgb(0.35, 0.50, 0.98), rgb(0.70, 0.80, 1.0)], metal=0.0, rough=0.42, emit=(0, 0, 0, 0), noise=0.26,
                  fleck=(rgb(0.95, 0.80, 0.30), 0.10, 1.0), label="lapis-lazuli bleu"),
}
ORDER = ["Wood", "Copper", "Iron", "Gold", "Diamond", "Uranium", "Ruby", "Lapis"]

_MATS = {}


def lin(x):
    return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4


def material(key, color, metal, rough, emit):
    k = (key, tuple(round(c, 3) for c in color), round(metal, 2), round(rough, 2), round(emit, 2))
    if k in _MATS:
        return _MATS[k]
    m = bpy.data.materials.new(f"px_{key}_{len(_MATS)}")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    c = tuple(lin(x) for x in color) + (1.0,)
    b.inputs["Base Color"].default_value = c
    b.inputs["Metallic"].default_value = metal
    b.inputs["Roughness"].default_value = rough
    m.diffuse_color = c
    if emit > 0:
        b.inputs["Emission Color"].default_value = c
        b.inputs["Emission Strength"].default_value = emit
    _MATS[k] = m
    return m


QUADS = {
    (1, 0, 0): ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1)),
    (-1, 0, 0): ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)),
    (0, 1, 0): ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0)),
    (0, -1, 0): ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)),
    (0, 0, 1): ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)),
    (0, 0, -1): ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0)),
}


def colorize(name, vox):
    """Associe à chaque voxel (couleur, métal, rugosité, émission) selon son rôle, son ombrage et le bruit."""
    cfg = MATERIALS[name]
    out = {}
    for (x, y, z), (role, s, n) in vox.items():
        if role == "head":
            lvl = s + (n - 0.5) * 2 * cfg["noise"]
            i = 0 if lvl < 0.28 else 1 if lvl < 0.55 else 2 if lvl < 0.84 else 3
            col = cfg["ramp"][i]; metal, rough, emit = cfg["metal"], cfg["rough"], cfg["emit"][i]
            fleck = cfg["fleck"]
            if fleck and shape.hash01(x, y, z, 11) < fleck[1]:
                col = fleck[0]; metal = fleck[2] if fleck[2] else metal; emit = 0 if name != "Diamond" and name != "Ruby" else emit
        elif role == "bind":
            i = 0 if n < 0.35 else 1 if n < 0.75 else 2
            col, metal, rough, emit = BIND[i], 0.0, 0.9, 0
        elif role == "pommel":
            col = cfg["ramp"][1] if name != "Wood" else BIND[2]
            metal, rough, emit = cfg["metal"], cfg["rough"], 0
        else:   # manche
            lvl = s + (n - 0.5) * 0.5
            i = 0 if lvl < 0.3 else 1 if lvl < 0.55 else 2 if lvl < 0.75 else 3
            col, metal, rough, emit = WOOD_HANDLE["ramp"][i], 0.0, 0.85, 0
        out[(x, y, z)] = (col, metal, rough, emit)
    return out


def build_object(name, vox, coll, origin_xyz=(0, 0, 0)):
    colors = colorize(name, vox)
    verts, faces, face_mat = [], [], []
    mats, mat_idx = [], {}
    ox, oz = GRIP
    for (x, y, z), (col, metal, rough, emit) in colors.items():
        key = (col, metal, rough, emit)
        if key not in mat_idx:
            mat_idx[key] = len(mats)
            mats.append(material(name, col, metal, rough, emit))
        for d, quad in QUADS.items():
            # d est exprimé dans le repère (x, y_voxel, z_voxel) -> placé en (X = x, Z = y, Y = z) : on permute
            nb = (x + d[0], y + d[1], z + d[2])
            if nb in colors:
                continue
            base = len(verts)
            for (a, b, c) in quad:
                # (a,b,c) en repère voxel (x, y, z) -> monde (X, Y, Z) = (x, z, y)
                verts.append(((x + a - ox) * VS + origin_xyz[0], (z + c) * VS + origin_xyz[1], (y + b - oz) * VS + origin_xyz[2]))
            # la permutation (x,y,z)->(x,z,y) inverse l'orientation : on renverse l'ordre des sommets
            faces.append((base, base + 3, base + 2, base + 1))
            face_mat.append(mat_idx[key])
    mesh = bpy.data.meshes.new(f"Pickaxe_{name}")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for m in mats:
        mesh.materials.append(m)
    mesh.polygons.foreach_set("material_index", face_mat)
    obj = bpy.data.objects.new(f"Pickaxe_{name}", mesh)
    coll.objects.link(obj)
    return obj


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    _MATS.clear()


def setup_preview(res=(1600, 800), samples=64):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = samples
    try:
        scn.cycles.use_denoising = True; scn.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scn.render.resolution_x, scn.render.resolution_y = res
    w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs["Color"].default_value = (0.20, 0.23, 0.29, 1); bg.inputs["Strength"].default_value = 0.55
    for loc_rot, energy in (((0.9, 0.2, 0.6), 2.2),):
        sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = energy; sun.rotation_euler = loc_rot
        scn.collection.objects.link(sun)
    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "AREA")); fill.data.energy = 120; fill.data.size = 3
    fill.location = (-1.5, -2.5, 1.2); fill.rotation_euler = (1.3, 0, -0.5); scn.collection.objects.link(fill)
    fl = bpy.data.objects.new("Floor", bpy.data.meshes.new("Floor"))
    fl.data.from_pydata([(-20, -20, -0.5), (20, -20, -0.5), (20, 20, -0.5), (-20, 20, -0.5)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("floor"); fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.09, 0.10, 0.13, 1)
    fm.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.5
    fl.data.materials.append(fm); scn.collection.objects.link(fl)


def export(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"Pickaxe_{name}.fbx"), use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)
    except Exception as e:
        print("FBX", name, e)
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"Pickaxe_{name}.glb"), export_format="GLB", use_selection=True, export_yup=True)
    except Exception as e:
        print("GLB", name, e)


def main():
    os.makedirs(OUT, exist_ok=True)
    vox = shape.build()
    # 1) un fichier par pioche
    for name in ORDER:
        reset()
        coll = bpy.data.collections.new(f"Pickaxe_{name}"); bpy.context.scene.collection.children.link(coll)
        obj = build_object(name, vox, coll)
        obj["material_name"] = MATERIALS[name]["label"]
        try:
            obj.asset_mark(); obj.asset_data.description = f"Pioche en voxel : {MATERIALS[name]['label']}"
        except Exception:
            pass
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"Pickaxe_{name}.blend"))
        export(obj, name)
        print(f"Pickaxe_{name}: {len(obj.data.polygons)} faces, {len(vox)} voxels")
    # 2) les 8 ensemble
    reset()
    coll = bpy.data.collections.new("Pickaxes"); bpy.context.scene.collection.children.link(coll)
    lab_mat = bpy.data.materials.new("label"); lab_mat.use_nodes = True
    lab_mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.9, 0.9, 0.92, 1)
    for i, name in enumerate(ORDER):
        o = build_object(name, vox, coll, origin_xyz=((i - 3.5) * 0.95, 0, 0))
        try:
            o.asset_mark()
        except Exception:
            pass
        # étiquette sous la pioche (nom de la matière)
        cu = bpy.data.curves.new("txt", "FONT"); cu.body = MATERIALS[name]["label"].capitalize(); cu.size = 0.11; cu.align_x = "CENTER"; cu.extrude = 0.004
        cu.resolution_u = 2; cu.materials.append(lab_mat)
        t = bpy.data.objects.new(f"Label_{name}", cu); coll.objects.link(t)
        t.location = ((i - 3.5) * 0.95 + 0.33, 0, -0.24); t.rotation_euler = (math.radians(90), 0, 0)
        bpy.context.view_layer.objects.active = t; bpy.ops.object.select_all(action="DESELECT"); t.select_set(True)
        bpy.ops.object.convert(target="MESH")
    setup_preview()
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); cam.data.lens = 50
    cam.location = (0, -11.5, 0.5); cam.rotation_euler = (math.radians(90), 0, 0)
    bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Pickaxes_All.blend"))


if __name__ == "__main__":
    main()
