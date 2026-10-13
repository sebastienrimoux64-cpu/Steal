"""
Katanas en VOXEL : bois, fer, or, diamant.

    python tools/katanas/make_voxel_katanas.py        # -> KatanasVoxel/

Un .blend (+ .fbx et .glb) par katana, plus Katanas_Voxel_All.blend (les 4 côte à côte) et des aperçus.
Repère : katana debout, lame vers +Z, dos de la lame vers +X, épaisseur sur Y. Origine = bout du manche. 1 voxel = 1,2 cm (~1,1 m au total).
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pickaxes"))
import make_pickaxes as MP
import shape

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "KatanasVoxel")
VS = 0.012
ORDER = ["Wood", "Iron", "Gold", "Diamond"]
rgb = lambda *c: tuple(c)

BLADE_LEN = 70
Z_HANDLE = 20


def build():
    """{(x, y, z): (rôle, niveau 0..1, bruit)} ; x = dos (+) / tranchant (-), y = épaisseur, z = longueur."""
    v = {}
    h = shape.hash01
    # pommeau
    for x in range(-2, 3):
        for y in range(-2, 3):
            if abs(x) == 2 and abs(y) == 2:
                continue
            v[(x, y, 0)] = ("kashira", 0.5, h(x, y, 0))
    # manche 3x3 (z 1..20) : motif en losanges d'ito
    for z in range(1, Z_HANDLE + 1):
        for x in (-1, 0, 1):
            for y in (-1, 0, 1):
                if x == 0 and y == 0:
                    continue
                ring = (x, y)
                k = (z + (0 if x != 1 and y != 1 else 0) + 2 * (x + y)) % 4
                role = "wrap" if k in (0, 1) else "core"
                if z in (1, 2, Z_HANDLE - 1, Z_HANDLE):
                    role = "wrap"
                v[(x, y, z)] = (role, 0.5, h(x, y, z, 1))
    for x in (-1, 0, 1):               # intérieur du manche
        for y in (-1, 0, 1):
            for z in range(1, Z_HANDLE + 1):
                if (x, y, z) not in v:
                    v[(x, y, z)] = ("core", 0.5, h(x, y, z, 2))
    # fuchi
    z = Z_HANDLE + 1
    for x in range(-2, 3):
        for y in range(-2, 3):
            if abs(x) == 2 and abs(y) == 2:
                continue
            if abs(x) <= 1 and abs(y) <= 1 or True:
                v[(x, y, z)] = ("kashira", 0.5, h(x, y, z, 3))
    # tsuba (z 22..23) : disque 9x7
    for z in (Z_HANDLE + 2, Z_HANDLE + 3):
        for x in range(-4, 5):
            for y in range(-3, 4):
                if (abs(x) == 4 and abs(y) >= 2) or (abs(x) == 3 and abs(y) == 3):
                    continue
                v[(x, y, z)] = ("tsuba", 0.5, h(x, y, z, 4))
    # habaki (z 24..26)
    z0 = Z_HANDLE + 4
    for z in range(z0, z0 + 3):
        for x in range(-2, 3):
            for y in (-2, -1, 0, 1, 2) if z == z0 else (-1, 0, 1):
                if abs(x) == 2 and abs(y) == 2:
                    continue
                if z > z0 and abs(x) == 2 and False:
                    continue
                v[(x, y, z)] = ("habaki", 0.5, h(x, y, z, 5))
    # lame : 3 colonnes (dos x=+1, milieu 0, tranchant x=-1), courbure vers +x
    zb0 = z0 + 3
    for i in range(BLADE_LEN):
        s = i / BLADE_LEN
        off = int(round(5.0 * s * s))
        z = zb0 + i
        k = max(0.0, (s - 0.9) / 0.1)
        for col, thick in ((1, 3), (0, 3), (-1, 1)):
            if k > 0:
                # kissaki : le tranchant se replie vers le dos
                if col == -1 and k > 0.35:
                    continue
                if col == 0 and k > 0.75:
                    continue
                if k > 0.9 and col == 1:
                    thick = 1
            ys = (-1, 0, 1) if thick == 3 else (0,)
            for y in ys:
                lvl = {1: 0.18, 0: 0.5, -1: 0.95}[col]       # dos sombre -> tranchant éclairé (hamon)
                v[(col + off, y, z)] = ("blade", lvl if y == 0 else lvl * 0.9, h(col + off, y, z, 6))
    # pointe
    zt = zb0 + BLADE_LEN
    off = 5
    for z in (zt, zt + 1):
        v[(1 + off, 0, z)] = ("blade", 0.25, h(1, 0, z, 7))
    return v


def colorize(name, vox):
    cfg = MP.MATERIALS[name]
    ramp = cfg["ramp"]
    out = {}
    wood_h = MP.WOOD_HANDLE["ramp"]
    for (x, y, z), (role, s, n) in vox.items():
        if role == "blade":
            lvl = s + (n - 0.5) * 2 * cfg["noise"] * 0.6
            i = 0 if lvl < 0.3 else 1 if lvl < 0.58 else 2 if lvl < 0.85 else 3
            col, metal, rough, emit = ramp[i], cfg["metal"], cfg["rough"], cfg["emit"][i]
            if name == "Diamond" and shape.hash01(x, y, z, 11) < 0.07:
                col = rgb(0.95, 1.0, 1.0)
        elif role in ("tsuba", "kashira"):
            if name == "Wood":
                col, metal, rough, emit = (rgb(0.20, 0.12, 0.06) if n < 0.5 else rgb(0.28, 0.17, 0.09)), 0.0, 0.85, 0
            elif name == "Iron":
                col, metal, rough, emit = (rgb(0.14, 0.14, 0.16) if n < 0.6 else rgb(0.22, 0.22, 0.25)), 0.8, 0.4, 0
            elif name == "Gold":
                col, metal, rough, emit = ramp[1], 0.85, 0.3, 0
            else:
                col, metal, rough, emit = rgb(0.72, 0.76, 0.82), 0.85, 0.25, 0
        elif role == "habaki":
            if name == "Wood":
                col, metal, rough, emit = rgb(0.20, 0.12, 0.06), 0.0, 0.85, 0
            elif name == "Iron":
                col, metal, rough, emit = rgb(0.85, 0.64, 0.24), 0.85, 0.3, 0
            elif name == "Gold":
                col, metal, rough, emit = ramp[2], 0.85, 0.3, 0
            else:
                col, metal, rough, emit = rgb(0.72, 0.76, 0.82), 0.85, 0.25, 0
        elif role == "wrap":
            cols = {"Wood": (rgb(0.52, 0.38, 0.20), rgb(0.62, 0.47, 0.27)), "Iron": (rgb(0.03, 0.03, 0.04), rgb(0.07, 0.07, 0.09)),
                    "Gold": (rgb(0.45, 0.03, 0.05), rgb(0.62, 0.06, 0.08)), "Diamond": (rgb(0.03, 0.07, 0.30), rgb(0.06, 0.12, 0.45))}[name]
            col, metal, rough, emit = cols[0 if n < 0.55 else 1], 0.0, 0.9, 0
        else:   # core
            if name == "Wood":
                col = wood_h[2 if n < 0.5 else 1]
            else:
                col = rgb(0.86, 0.84, 0.76) if n < 0.5 else rgb(0.78, 0.76, 0.68)
            metal, rough, emit = 0.0, 0.8, 0
        out[(x, y, z)] = (col, metal, rough, emit)
    return out


def build_object(name, vox, coll, origin=(0, 0, 0)):
    colors = colorize(name, vox)
    verts, faces, fm = [], [], []
    mats, idx = [], {}
    for (x, y, z), (col, metal, rough, emit) in colors.items():
        key = (col, metal, rough, emit)
        if key not in idx:
            idx[key] = len(mats)
            mats.append(MP.material("k" + name, col, metal, rough, emit))
        for d, quad in MP.QUADS.items():
            if (x + d[0], y + d[1], z + d[2]) in colors:
                continue
            base = len(verts)
            for (a, b, c) in quad:
                verts.append(((x + a) * VS + origin[0], (y + b) * VS + origin[1], (z + c) * VS + origin[2]))
            faces.append((base, base + 1, base + 2, base + 3))
            fm.append(idx[key])
    mesh = bpy.data.meshes.new(f"Katana_{name}_Voxel")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    for m in mats:
        mesh.materials.append(m)
    mesh.polygons.foreach_set("material_index", fm)
    obj = bpy.data.objects.new(f"Katana_{name}_Voxel", mesh)
    coll.objects.link(obj)
    return obj


def export(obj, name):
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    try:
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"Katana_{name}_Voxel.fbx"), use_selection=True, apply_scale_options="FBX_SCALE_ALL", add_leaf_bones=False)
    except Exception as e:
        print("FBX", name, e)
    try:
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, f"Katana_{name}_Voxel.glb"), export_format="GLB", use_selection=True, export_yup=True)
    except Exception as e:
        print("GLB", name, e)


def preview_setup(res, lens, cam_loc, cam_target):
    MP.setup_preview(res=res, samples=64)
    from mathutils import Vector
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam")); cam.data.lens = lens
    cam.location = cam_loc
    cam.rotation_euler = (Vector(cam_target) - Vector(cam_loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam); bpy.context.scene.camera = cam
    for o in bpy.data.objects:      # sol sous le katana
        if o.name == "Floor":
            for vtx in o.data.vertices:
                vtx.co.z = -0.01


def main():
    os.makedirs(OUT, exist_ok=True)
    vox = build()
    for name in ORDER:
        MP.reset()
        coll = bpy.data.collections.new(f"Katana_{name}_Voxel"); bpy.context.scene.collection.children.link(coll)
        obj = build_object(name, vox, coll)
        obj["material_name"] = MP.MATERIALS[name]["label"]
        try:
            obj.asset_mark(); obj.asset_data.description = f"Katana en voxel : {MP.MATERIALS[name]['label']}"
        except Exception:
            pass
        preview_setup((1000, 1200), 62, (-1.2, -1.9, 0.62), (0.02, 0, 0.5))
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"Katana_{name}_Voxel.blend"))
        export(obj, name)
        print(f"Katana_{name}_Voxel: {len(obj.data.polygons)} faces, {len(vox)} voxels")
    MP.reset()
    coll = bpy.data.collections.new("Katanas_Voxel"); bpy.context.scene.collection.children.link(coll)
    for i, name in enumerate(ORDER):
        o = build_object(name, vox, coll, origin=((i - 1.5) * 0.28, 0, 0))
        try:
            o.asset_mark()
        except Exception:
            pass
    preview_setup((1800, 900), 50, (0, -4.6, 0.55), (0, 0, 0.55))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "Katanas_Voxel_All.blend"))


if __name__ == "__main__":
    main()
