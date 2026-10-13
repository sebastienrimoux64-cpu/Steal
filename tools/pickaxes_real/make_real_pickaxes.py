"""
Pioches RÉALISTES (non voxel) : bois, cuivre, fer, or, diamant, uranium, rubis, lapis-lazuli.

    python tools/pickaxes_real/make_real_pickaxes.py [Nom ...]      # -> PickaxesRealistic/

Un .blend par pioche (matériaux procéduraux, studio d'éclairage et caméra inclus) + Pickaxes_Realistic_All.blend (les 8 en ligne).
Dimensions : environ 94 cm de haut, 47 cm de large (tête). Origine = bout du manche (z = 0), manche vers +Z, tête le long de X.
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402  (après bpy)
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geometry as G
import materials as M

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "PickaxesRealistic")

OAK = ((0.17, 0.09, 0.04), (0.40, 0.23, 0.10), (0.63, 0.41, 0.20))
WALNUT = ((0.07, 0.035, 0.018), (0.19, 0.10, 0.055), (0.34, 0.20, 0.11))
ASH = ((0.35, 0.22, 0.10), (0.60, 0.42, 0.22), (0.80, 0.62, 0.38))

# nom : dict(handle=bois du manche, head=(type, fabrique), collar=fabrique|None, grip=cuir ?, rope=ligature ?, label=...)
def cfg(name):
    if name == "Wood":
        return dict(handle=("oak", OAK), head=("smooth", lambda: M.wood("Head_Ash", *ASH, ring_dir="X", scale=50)),
                    collar=None, rope=True, grip=False, wedge=lambda: M.wood("Wedge_Walnut", *WALNUT), label="bois")
    if name == "Copper":
        return dict(handle=("oak", OAK), head=("smooth", lambda: M.metal("Copper", (0.95, 0.46, 0.27), (0.74, 0.33, 0.2), (0.2, 0.4), edge=(1.0, 0.72, 0.52),
                                                                      patina=dict(color=(0.10, 0.52, 0.42), amount=0.9))),
                    collar=lambda: M.metal("Copper_Collar", (0.80, 0.38, 0.22), (0.6, 0.27, 0.16), (0.3, 0.5), patina=dict(color=(0.10, 0.5, 0.4), amount=0.7)),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Steel", (0.18, 0.19, 0.21), (0.12, 0.12, 0.14), (0.4, 0.6)), label="cuivre")
    if name == "Iron":
        return dict(handle=("oak", OAK), head=("smooth", lambda: M.metal("Iron", (0.44, 0.45, 0.48), (0.30, 0.31, 0.34), (0.26, 0.5), edge=(0.85, 0.87, 0.9),
                                                                      rust=dict(color=(0.42, 0.17, 0.07), amount=0.8))),
                    collar=lambda: M.metal("Iron_Collar", (0.20, 0.21, 0.23), (0.13, 0.13, 0.15), (0.35, 0.6), rust=dict(color=(0.35, 0.14, 0.06), amount=0.5)),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Steel", (0.18, 0.19, 0.21), (0.12, 0.12, 0.14), (0.4, 0.6)), label="fer")
    if name == "Gold":
        return dict(handle=("walnut", WALNUT), head=("smooth", lambda: M.metal("Gold", (1.0, 0.78, 0.30), (0.95, 0.64, 0.17), (0.10, 0.26), edge=(1.0, 0.93, 0.62), scratch=0.3)),
                    collar=lambda: M.metal("Gold_Collar", (0.95, 0.70, 0.22), (0.85, 0.58, 0.14), (0.14, 0.3), scratch=0.3),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Gold", (0.9, 0.66, 0.2), (0.8, 0.55, 0.12), (0.2, 0.35)), label="or")
    if name == "Diamond":
        return dict(handle=("walnut", WALNUT), head=("crystal", lambda: M.crystal("Diamond", (0.92, 0.99, 1.0), (0.35, 0.88, 0.95), ior=2.42)),
                    collar=lambda: M.metal("Steel_Collar", (0.74, 0.76, 0.80), (0.55, 0.57, 0.61), (0.12, 0.3)),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Steel", (0.5, 0.52, 0.56), (0.35, 0.36, 0.4), (0.2, 0.4)), label="diamant")
    if name == "Uranium":
        return dict(handle=("walnut", WALNUT), head=("crystal", lambda: M.crystal("Uranium", (0.55, 1.0, 0.35), (0.25, 0.9, 0.08), emit=3.2, emit_color=(0.30, 1.0, 0.08), ior=2.0, transmission=0.75)),
                    collar=lambda: M.metal("DarkIron_Collar", (0.17, 0.18, 0.20), (0.10, 0.10, 0.12), (0.3, 0.55)),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Dark", (0.15, 0.16, 0.18), (0.1, 0.1, 0.12), (0.4, 0.6)), label="uranium vert")
    if name == "Ruby":
        return dict(handle=("walnut", WALNUT), head=("crystal", lambda: M.crystal("Ruby", (1.0, 0.45, 0.52), (0.92, 0.03, 0.09), emit=0.12, emit_color=(1.0, 0.05, 0.1), ior=1.77)),
                    collar=lambda: M.metal("Gold_Collar", (0.95, 0.70, 0.22), (0.85, 0.58, 0.14), (0.14, 0.3), scratch=0.3),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Gold", (0.9, 0.66, 0.2), (0.8, 0.55, 0.12), (0.2, 0.35)), label="rubis rouge")
    if name == "Lapis":
        return dict(handle=("walnut", WALNUT), head=("smooth", lambda: M.lapis("Lapis")),
                    collar=lambda: M.metal("Gold_Collar", (0.95, 0.70, 0.22), (0.85, 0.58, 0.14), (0.14, 0.3), scratch=0.3),
                    grip=True, rope=False, wedge=lambda: M.metal("Wedge_Gold", (0.9, 0.66, 0.2), (0.8, 0.55, 0.12), (0.2, 0.35)), label="lapis-lazuli bleu")
    raise KeyError(name)


ORDER = ["Wood", "Copper", "Iron", "Gold", "Diamond", "Uranium", "Ruby", "Lapis"]


def build_pickaxe(name, location=(0, 0, 0)):
    c = cfg(name)
    mats = []            # liste des matériaux de l'objet
    def slot(m):
        mats.append(m)
        return len(mats) - 1
    wood_name, tones = c["handle"]
    s_handle = slot(M.wood(f"Handle_{wood_name}", *tones, ring_dir="Z"))
    head_kind, head_fn = c["head"]
    s_head = slot(head_fn())
    s_collar = slot(c["collar"]()) if c["collar"] else None
    s_wedge = slot(c["wedge"]())
    s_leather = slot(M.leather()) if c["grip"] else None
    s_rope = slot(M.rope()) if c["rope"] else None
    bm = bmesh.new()
    G.build_handle(bm, mat=s_handle)
    G.build_head(bm, mat=s_head, kind=head_kind)
    if s_collar is not None:
        G.build_collar(bm, mat=s_collar)
        G.build_rivets(bm, mat=s_collar)
    G.build_wedge(bm, mat=s_wedge)
    if s_leather is not None:
        G.build_helix(bm, 0.075, 0.375, 34, 0.0046, s_leather, pad=0.0008)
        G.build_helix(bm, 0.070, 0.080, 1.6, 0.0052, s_leather, pad=0.0008)
        G.build_helix(bm, 0.372, 0.382, 1.6, 0.0052, s_leather, pad=0.0008)
    if s_rope is not None:
        G.build_helix(bm, 0.775, 0.880, 9, 0.0036, s_rope, pad=0.0012, per_turn=28)
        G.build_helix(bm, 0.772, 0.882, 9, 0.0030, s_rope, pad=0.0034, per_turn=28)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    # arêtes franches là où l'angle est vif (pointes, cale), lissage ailleurs
    lim = math.radians(62)
    for e in bm.edges:
        if len(e.link_faces) == 2 and all(f.smooth for f in e.link_faces):
            e.smooth = e.calc_face_angle(0.0) < lim
    mesh = bpy.data.meshes.new(f"Pickaxe_{name}")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(f"Pickaxe_{name}", mesh)
    obj.location = location
    obj["material_name"] = c["label"]
    return obj


# ------------------------------------------------------------------ studio
def studio(floor_size=40.0, samples=96, res=(1600, 1000)):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.samples = samples
    scn.cycles.use_denoising = True
    try:
        scn.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scn.cycles.max_bounces = 12
    scn.cycles.transmission_bounces = 12
    scn.cycles.transparent_max_bounces = 16
    scn.render.resolution_x, scn.render.resolution_y = res
    try:
        scn.view_settings.view_transform = "AgX"
        scn.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    # monde : dégradé de studio (sol sombre, plafond clair) pour des reflets métalliques crédibles
    w = bpy.data.worlds.new("Studio")
    scn.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mp = nt.nodes.new("ShaderNodeMapRange")
    mp.inputs["From Min"].default_value = -0.6
    mp.inputs["From Max"].default_value = 0.9
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, (0.012, 0.014, 0.02, 1)
    els[1].position, els[1].color = 1.0, (0.55, 0.62, 0.78, 1)
    mid = els.new(0.45); mid.color = (0.12, 0.14, 0.19, 1)
    nt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
    nt.links.new(sep.outputs["Z"], mp.inputs["Value"])
    nt.links.new(mp.outputs["Result"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 0.8
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    def area(name, loc, target, energy, size, color=(1, 1, 1)):
        L = bpy.data.lights.new(name, "AREA"); L.energy = energy; L.size = size; L.color = color
        o = bpy.data.objects.new(name, L); o.location = loc
        o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        scn.collection.objects.link(o)
    area("Key", (-2.2, -2.4, 2.2), (0, 0, 0.5), 520, 2.4, (1.0, 0.96, 0.9))
    area("Rim", (2.4, 2.2, 1.8), (0, 0, 0.5), 420, 1.8, (0.75, 0.85, 1.0))
    area("Fill", (2.6, -2.0, 0.6), (0, 0, 0.5), 140, 3.0)
    # sol : plan sombre légèrement brillant
    fl = bpy.data.objects.new("Floor", bpy.data.meshes.new("Floor"))
    fl.data.from_pydata([(-floor_size, -floor_size, -0.012), (floor_size, -floor_size, -0.012), (floor_size, floor_size, -0.012), (-floor_size, floor_size, -0.012)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("Floor"); fm.use_nodes = True
    b = fm.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.012, 0.013, 0.018, 1); b.inputs["Roughness"].default_value = 0.55
    fl.data.materials.append(fm)
    scn.collection.objects.link(fl)


def camera(loc, target, lens=70):
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0


def main(names):
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        reset()
        coll = bpy.data.collections.new(f"Pickaxe_{name}"); bpy.context.scene.collection.children.link(coll)
        obj = build_pickaxe(name)
        coll.objects.link(obj)
        try:
            obj.asset_mark(); obj.asset_data.description = f"Pioche réaliste : {obj['material_name']}"
        except Exception:
            pass
        studio(res=(1200, 1200))
        camera((-1.55, -1.75, 0.82), (0.02, 0, 0.5), 62)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"Pickaxe_{name}_Realistic.blend"))
        print(f"Pickaxe_{name}: {len(obj.data.polygons)} faces, {len(obj.data.materials)} matériaux")


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in ORDER] or ORDER
    main(wanted)
