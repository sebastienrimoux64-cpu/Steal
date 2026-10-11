"""
Deux scènes de présentation du Home Builder Kit (pour la prévisualisation 3D du site) :

  1. Showroom.blend / .glb      — tous les assets alignés, par catégorie, sur socles, avec étiquettes
  2. Example_Place.blend / .glb — 3 zones : maison (extérieur), maison en coupe (intérieur), salon

    python tools/make_home_places.py

Génère aussi HomeKit/Scenes/cameras.json (points de vue pour le visualiseur web).
"""
import json
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_home_kit as hk

SCENES = os.path.join(hk.OUT, "Scenes")
os.makedirs(SCENES, exist_ok=True)

# ----------------------------------------------------------------------------
# Matériaux de présentation
# ----------------------------------------------------------------------------
PLINTH = {  # une teinte douce par catégorie
    "01_Structure": (0.62, 0.70, 0.80),
    "02_Floors_Roofs": (0.82, 0.60, 0.52),
    "03_Doors_Windows": (0.78, 0.66, 0.48),
    "04_Living": (0.55, 0.65, 0.78),
    "05_Bedroom": (0.68, 0.62, 0.80),
    "06_Kitchen": (0.55, 0.78, 0.68),
    "07_Bathroom": (0.55, 0.76, 0.80),
    "08_Lights_Decor": (0.85, 0.74, 0.50),
    "09_Exterior": (0.58, 0.76, 0.52),
}
TITLES = {
    "01_Structure": "01  STRUCTURE", "02_Floors_Roofs": "02  FLOORS & ROOFS", "03_Doors_Windows": "03  DOORS & WINDOWS",
    "04_Living": "04  LIVING ROOM", "05_Bedroom": "05  BEDROOM", "06_Kitchen": "06  KITCHEN",
    "07_Bathroom": "07  BATHROOM", "08_Lights_Decor": "08  LIGHTS & DECOR", "09_Exterior": "09  EXTERIOR",
}
for cat, col in PLINTH.items():
    hk.MATS["plinth_" + cat] = (col, 0.6, 0.0, {})
    hk.MATS["title_" + cat] = (tuple(c * 0.42 for c in col), 0.5, 0.0, {})
hk.MATS["showroom_floor"] = ((0.93, 0.93, 0.92), 0.7, 0.0, {})
hk.MATS["panel"] = ((0.88, 0.88, 0.87), 0.8, 0.0, {})
hk.MATS["label"] = ((0.14, 0.14, 0.16), 0.5, 0.0, {})
hk.MATS["slab"] = ((0.80, 0.80, 0.79), 0.8, 0.0, {})
hk.MATS["brand"] = ((0.16, 0.18, 0.22), 0.4, 0.0, {})

ORDER = {  # ordre de présentation (logique de construction, puis de meublage)
    "01_Structure": ["Wall_Solid_1m", "Wall_Solid_2m", "Wall_Half_2m", "Wall_Door_2m", "Wall_Window_2m", "Wall_Window_Wide_2m",
                     "Wall_Archway_2m", "Wall_Siding_2m", "Wall_Brick_2m", "Wall_Corner_Post", "Wall_Pillar_Half", "Beam_Ceiling_2m"],
    "02_Floors_Roofs": ["Foundation_2m", "Floor_Wood_2m", "Floor_Tile_2m", "Slab_Upper_Floor_2m", "Ceiling_2m", "Roof_Slope_Tile_2m",
                        "Roof_Slope_Slate_2m", "Roof_Ridge_2m", "Roof_Gable_Triangle_6m", "Dormer_Window_Small", "Chimney"],
    "03_Doors_Windows": ["Door_Frame_1m", "Door_Interior", "Door_Front", "Window_Casement_1.2m", "Window_Casement_Wide_1.6m",
                         "Shutter_Pair", "Railing_2m", "Stairs_Straight_2.8m", "Stairs_Porch_3step"],
    "04_Living": ["Sofa_2Seat", "Sofa_3Seat", "Armchair", "Chair_Dining", "Chair_Bar_Stool", "Table_Coffee", "Table_Side",
                  "Table_Dining_1.6m", "Table_Dining_Round", "TV_Stand_With_TV", "Sideboard_Low", "Bookshelf_Tall", "Fireplace"],
    "05_Bedroom": ["Bed_Single", "Bed_Double", "Nightstand", "Dresser_3Drawer", "Wardrobe_2Door", "Desk_With_Drawers", "Chair_Office"],
    "06_Kitchen": ["Kitchen_Base_60", "Kitchen_Base_Drawers_60", "Kitchen_Sink_120", "Kitchen_Cooker_60", "Kitchen_Wall_Cabinet_60",
                   "Kitchen_Hood", "Fridge_Tall", "Stool_Kitchen"],
    "07_Bathroom": ["Bathtub", "Toilet", "Sink_Pedestal", "Mirror_Cabinet"],
    "08_Lights_Decor": ["Lamp_Floor", "Lamp_Table", "Light_Pendant", "Light_Ceiling_Flush", "Light_Wall_Sconce", "Rug_Rect_2x3",
                        "Rug_Round_1.6m", "Frame_Portrait", "Frame_Landscape", "Mirror_Wall_Round", "Clock_Wall", "Plant_Pot_Large",
                        "Plant_Small", "Vase_Flowers", "Books_Stack", "Curtains_Pair_1.6m", "Cushion_Square", "Coat_Rack_Wall", "Shelf_Wall_1m"],
    "09_Exterior": ["Fence_Section_2m", "Gate_Garden", "Column_Porch", "Mailbox", "Bench_Garden", "Path_Stone_Tile"],
}


# ----------------------------------------------------------------------------
# Outils
# ----------------------------------------------------------------------------
def new_scene():
    hk.reset_scene()
    colls, objs = hk.make_all()
    lib = bpy.data.collections.new("Library_Hidden")
    bpy.context.scene.collection.children.link(lib)
    for o in objs.values():
        for c in o.users_collection:
            c.objects.unlink(o)
        lib.objects.link(o)
        o.hide_render = True
        o.hide_viewport = True
    for c in colls.values():
        bpy.context.scene.collection.children.unlink(c)
    return objs


def make_coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def copy_asset(objs, name, coll, loc=(0, 0, 0), rz=0.0):
    o = objs[name].copy()      # copie liée : maillage partagé (fichiers légers)
    o.hide_render = False
    o.hide_viewport = False
    o.location = loc
    o.rotation_euler = (0, 0, math.radians(rz))
    coll.objects.link(o)
    return o


def box_obj(name, mat, x0, x1, y0, y1, z0, z1, coll, b=0.01):
    a = hk.Asset(name)
    a.bx(mat, x0, x1, y0, y1, z0, z1, b=b)
    o = a.build(coll)
    return o


def text_obj(body, size, loc, rot, mat, coll, align="LEFT", extrude=0.012, bold=False):
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.resolution_u = 2
    cu.align_x = align
    cu.align_y = "CENTER"
    cu.materials.append(hk.material(mat))
    ob = bpy.data.objects.new("T_" + body[:24], cu)
    coll.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.ops.object.convert(target="MESH")
    return ob


def world_bbox(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return (Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))),
            Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts))))


def setup_render(res=(1600, 1000), samples=48, sky=(0.62, 0.76, 0.95), strength=1.0, sun_energy=4.0):
    scn = bpy.context.scene
    scn.render.engine = "CYCLES"
    scn.cycles.device = "CPU"
    scn.cycles.samples = samples
    try:
        scn.cycles.use_denoising = True
        scn.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    scn.render.resolution_x, scn.render.resolution_y = res
    world = bpy.data.worlds.new("sky")
    scn.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = sky + (1,)
    bg.inputs["Strength"].default_value = strength
    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = sun_energy
    sun.data.angle = math.radians(2.5)
    sun.rotation_euler = (math.radians(48), math.radians(8), math.radians(30))
    scn.collection.objects.link(sun)


def add_camera(name, loc, target, lens=30, res=None):
    cam = bpy.data.objects.new(name, bpy.data.cameras.new(name))
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    if res:
        cam["res_x"], cam["res_y"] = res
    return cam


def gltf_xyz(v):
    """Blender (x, y, z) -> glTF Y-up (x, z, -y)."""
    return [round(v[0], 3), round(v[2], 3), round(-v[1], 3)]


# ----------------------------------------------------------------------------
# 1) SHOWROOM
# ----------------------------------------------------------------------------
def build_showroom():
    objs = new_scene()
    coll = make_coll("Showroom")
    cams = {}
    row_y = 0.0
    rows = []
    max_x = 0.0
    for cat in sorted(ORDER):
        names = ORDER[cat]
        assert set(names) == {n for n, o in objs.items() if o["hk_category"] == cat}, cat
        x = 0.0
        row_depth = 0.0
        placed = []
        for name in names:
            src = objs[name]
            lb = [Vector(c) for c in src.bound_box]
            minx, maxx = min(p.x for p in lb), max(p.x for p in lb)
            miny, maxy = min(p.y for p in lb), max(p.y for p in lb)
            minz, maxz = min(p.z for p in lb), max(p.z for p in lb)
            w, d = maxx - minx, maxy - miny
            slot = max(w, 0.8) + 1.45
            cx = x + 0.75 + max(w, 0.8) / 2           # centre de l'emplacement
            o = copy_asset(objs, name, coll, (cx - (minx + maxx) / 2, row_y - miny, -minz if minz < 0 else 0.0))
            # socle
            pm = "plinth_" + cat
            pad = 0.28
            box_obj("Plinth_" + name, pm, cx - max(w, 0.8) / 2 - pad, cx + max(w, 0.8) / 2 + pad,
                    row_y - pad, row_y + d + pad, -0.08, 0.0, coll, b=0.015)
            # panneau support pour les objets muraux (suspendus)
            if minz > 0.25:
                box_obj("Panel_" + name, "panel", cx - w / 2 - 0.2, cx + w / 2 + 0.2, row_y + d + 0.02, row_y + d + 0.07,
                        0.0, maxz + 0.25, coll, b=0.01)
            # étiquette posée devant le socle
            text_obj(name.replace("_", " "), 0.17, (cx, row_y - pad - 0.32, -0.075), (0, 0, 0), "label", coll, align="CENTER", extrude=0.004)
            placed.append((name, cx, d, maxz))
            x += slot
            row_depth = max(row_depth, d)
        # bandeau de titre de la rangée (debout, face à -Y) + compteur
        text_obj(TITLES[cat], 0.95, (-1.4, row_y + 0.05, 0.55), (math.pi / 2, 0, 0), "title_" + cat, coll, align="RIGHT", extrude=0.06)
        text_obj(f"{len(names)} assets", 0.34, (-1.4, row_y - 0.6, -0.075), (0, 0, 0), "label", coll, align="RIGHT", extrude=0.004)
        # ruban de couleur au sol sous la rangée
        box_obj("Strip_" + cat, "plinth_" + cat, -0.2, x - 0.5, row_y - 1.35, row_y - 1.2, -0.08, -0.07, coll, b=0)
        rows.append(dict(cat=cat, y=row_y, x1=x, depth=row_depth, n=len(names)))
        max_x = max(max_x, x)
        row_y += row_depth + 4.4

    # titre général
    text_obj("HOME BUILDER KIT", 2.3, (0, -9.0, 1.25), (math.pi / 2, 0, 0), "brand", coll, align="LEFT", extrude=0.1)
    text_obj("89 modular house assets  -  FBX / GLB / Blender", 0.62, (0.1, -9.6, -0.075), (0, 0, 0), "label", coll, align="LEFT", extrude=0.004)

    # sol
    floor = box_obj("Showroom_Floor", "showroom_floor", -24, max_x + 8, -16, row_y + 6, -0.3, -0.08, coll, b=0)

    setup_render((1800, 900), samples=40, sky=(0.78, 0.84, 0.92), strength=1.15, sun_energy=3.2)
    # caméras : vue d'ensemble + une série par rangée (tronçons de <= 17 m)
    cx_all = (max_x - 22) / 2
    cams["Overview"] = add_camera("Cam_Overview", (cx_all - 8, -48, 52), (cx_all + 1, row_y / 2 - 2, 0), 32, (1800, 1000))
    for r in rows:
        # vue large de toute la rangée
        width = r["x1"] + 3.0
        xc = (r["x1"] - 3.0) / 2
        d = width * 0.72
        tag = f"{r['cat']}_Wide"
        cams[tag] = add_camera("Cam_Row_" + tag, (xc, r["y"] - d, 3.0 + d * 0.52), (xc, r["y"] + r["depth"] * 0.3, 0.9), 24, (2400, 800))
        # tronçons de détail (<= 17 m)
        n_seg = max(1, math.ceil((r["x1"] - 2) / 17.0))
        seg_len = (r["x1"] + 1.5) / n_seg
        for s_i in range(n_seg):
            xs = -1.5 + seg_len * (s_i + 0.5)
            dd = seg_len * 0.95
            tag = f"{r['cat']}" + (f"_{s_i + 1}" if n_seg > 1 else "")
            cams[tag] = add_camera("Cam_Row_" + tag, (xs, r["y"] - dd, 2.8 + r["depth"] * 0.2 + dd * 0.12), (xs, r["y"] + r["depth"] * 0.35, 0.85), 28, (1800, 900))
    bpy.context.scene.camera = cams["Overview"]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES, "Showroom.blend"))
    export_glb("Showroom.glb", coll)
    meta = {"scene": "Showroom", "rows": [{**r, "title": TITLES[r["cat"]]} for r in rows]}
    # points de vue pour le visualiseur web (repère glTF Y-up)
    views = []
    views.append({"id": "overview", "label": "Overview", "target": gltf_xyz((cx_all, row_y / 2 - 2, 0)),
                  "orbit": [0, 48, max(70, row_y * 1.25)]})
    for r in rows:
        xc = (r["x1"] - 2) / 2
        views.append({"id": r["cat"], "label": TITLES[r["cat"]].replace("  ", " "), "target": gltf_xyz((xc, r["y"] + r["depth"] / 2, 1.0)),
                      "orbit": [0, 56, max(20, r["x1"] * 0.68)]})
    meta["views"] = views
    return meta


def export_glb(filename, coll):
    bpy.ops.object.select_all(action="DESELECT")
    for o in coll.all_objects:
        if o.type == "MESH" and not o.hide_render:
            o.select_set(True)
    bpy.context.view_layer.objects.active = next(o for o in coll.all_objects if o.type == "MESH")
    bpy.ops.export_scene.gltf(filepath=os.path.join(SCENES, filename), export_format="GLB", use_selection=True, export_yup=True,
                              export_cameras=False, export_lights=False, export_apply=False)


# ----------------------------------------------------------------------------
# 2) EXAMPLE PLACE : maison complète / maison en coupe / salon
# ----------------------------------------------------------------------------
def make_putter(objs, coll, ox, oy, oz=0.0):
    def put(name, x, y, z=0.0, rz=0.0):
        return copy_asset(objs, name, coll, (ox + x, oy + y, oz + z), rz)
    return put


def furnish_front(put):
    """Salon + salle à manger + cuisine (moitié avant de la maison, y de -4 à 0)."""
    put("TV_Stand_With_TV", -1.05, -0.32)
    put("Bookshelf_Tall", -2.4, -0.3)
    put("Sofa_3Seat", -1.8, -2.3, rz=180)
    put("Table_Coffee", -1.8, -1.3)
    put("Rug_Rect_2x3", -1.8, -1.55, 0.03)
    put("Armchair", -2.55, -1.55, rz=90)
    put("Lamp_Floor", -0.45, -2.9)
    put("Plant_Pot_Large", -2.6, -3.45)
    put("Frame_Landscape", -1.05, -0.12, 1.5)
    put("Light_Pendant", -1.8, -1.6)
    put("Table_Side", -0.4, -1.2)
    put("Vase_Flowers", -0.4, -1.2, 0.5)
    put("Books_Stack", -1.8, -1.3, 0.42)
    for n, y in (("Fridge_Tall", -3.52), ("Kitchen_Base_Drawers_60", -2.85), ("Kitchen_Cooker_60", -2.25),
                 ("Kitchen_Sink_120", -1.35), ("Kitchen_Base_60", -0.45)):
        put(n, 2.6, y, rz=-90)
    for n, y in (("Kitchen_Wall_Cabinet_60", -2.85), ("Kitchen_Hood", -2.25), ("Kitchen_Wall_Cabinet_60", -1.65), ("Kitchen_Wall_Cabinet_60", -1.05)):
        put(n, 2.75, y, rz=-90)
    put("Table_Dining_1.6m", 0.95, -2.2, rz=90)
    for x, y, rz in ((1.65, -2.7, -90), (1.65, -1.7, -90), (0.25, -2.7, 90), (0.25, -1.7, 90)):
        put("Chair_Dining", x, y, rz=rz)
    put("Light_Pendant", 0.95, -2.2)
    put("Plant_Small", 0.95, -2.2, 0.75)
    put("Stool_Kitchen", 1.9, -0.65)


def furnish_back(put):
    """Chambre + salle de bain (moitié arrière, y de 0 à 4)."""
    put("Bed_Double", -1.3, 2.85)
    put("Nightstand", -2.45, 3.65)
    put("Nightstand", -0.15, 3.65)
    put("Lamp_Table", -2.45, 3.65, 0.55)
    put("Lamp_Table", -0.15, 3.65, 0.55)
    put("Wardrobe_2Door", 0.68, 1.85, rz=-90)
    put("Dresser_3Drawer", 0.7, 3.2, rz=-90)
    put("Mirror_Wall_Round", 0.88, 3.2, 1.0, rz=-90)
    put("Rug_Rect_2x3", -1.3, 2.3, 0.03)
    put("Frame_Portrait", -1.3, 3.88, 1.35, rz=180)
    put("Light_Ceiling_Flush", -1.3, 2.0)
    put("Plant_Small", -2.7, 0.5)
    put("Bathtub", 2.05, 3.5, rz=90)
    put("Toilet", 2.75, 1.5, rz=-90)
    put("Sink_Pedestal", 2.75, 2.5, rz=-90)
    put("Mirror_Cabinet", 2.9, 2.5, rz=-90)


def build_house(objs, coll, ox, oy, cutaway):
    put = make_putter(objs, coll, ox, oy)
    for ix in (-2, 0, 2):
        for iy in (-3, -1, 1, 3):
            put("Foundation_2m", ix, iy)
            put("Floor_Wood_2m", ix, iy)
    for iy in (1, 3):
        put("Floor_Tile_2m", 2, iy, 0.001)
    # murs : les faces avant (y=-4) et gauche (x=-3) sont omises en coupe
    if not cutaway:
        for x, n in {-2: "Wall_Window_2m", 0: "Wall_Door_2m", 2: "Wall_Window_2m"}.items():
            put(n, x, -4)
        for y, n in {-3: "Wall_Window_2m", -1: "Wall_Solid_2m", 1: "Wall_Window_2m", 3: "Wall_Solid_2m"}.items():
            put(n, -3, y, rz=-90)
        put("Wall_Corner_Post", -3, -4)
        put("Wall_Corner_Post", 3, -4)
        put("Wall_Corner_Post", -3, 4)
        put("Door_Frame_1m", 0, -4)
        put("Door_Front", 0, -4)
        put("Window_Casement_1.2m", -2, -4, 0.9)
        put("Window_Casement_1.2m", 2, -4, 0.9)
        put("Window_Casement_1.2m", -3, -3, 0.9, -90)
        put("Window_Casement_1.2m", -3, 1, 0.9, -90)
    for x, n in {-2: "Wall_Solid_2m", 0: "Wall_Window_Wide_2m", 2: "Wall_Window_2m"}.items():
        put(n, x, 4, rz=180) if x != 2 else put("Wall_Window_2m", x, 4, rz=180)
    for y, n in {-3: "Wall_Solid_2m", -1: "Wall_Window_Wide_2m", 1: "Wall_Solid_2m", 3: "Wall_Window_2m"}.items():
        put(n, 3, y, rz=90)
    put("Wall_Corner_Post", 3, 4)
    for x, n in {-2: "Wall_Solid_2m", 0: "Wall_Door_2m", 2: "Wall_Solid_2m"}.items():
        put(n, x, 0)
    put("Wall_Solid_2m", 1, 1, rz=90)
    put("Wall_Door_2m", 1, 3, rz=90)
    put("Door_Frame_1m", 0, 0)
    put("Door_Interior", 0, 0)
    put("Door_Frame_1m", 1, 3, rz=90)
    put("Door_Interior", 1, 3, rz=90)
    put("Window_Casement_Wide_1.6m", 0, 4, 0.9, 180)
    put("Window_Casement_1.2m", 2, 4, 0.9, 180)
    put("Window_Casement_Wide_1.6m", 3, -1, 0.9, 90)
    put("Window_Casement_1.2m", 3, 3, 0.9, 90)
    if not cutaway:
        for ix in (-2, 0, 2):
            for iy in (-3, -1, 1, 3):
                put("Ceiling_2m", ix, iy, 2.8)
        for iy in (-3, -1, 1, 3):
            put("Roof_Slope_Tile_2m", -3, iy, 2.9, -90)
            put("Roof_Slope_Tile_2m", 3, iy, 2.9, 90)
            put("Roof_Ridge_2m", 0, iy, 2.9 + 3 * math.tan(math.radians(35)), 90)
        put("Roof_Gable_Triangle_6m", 0, -4, 2.8)
        put("Roof_Gable_Triangle_6m", 0, 4, 2.8, 180)
        put("Chimney", 2.3, 2.2, 2.9)
    furnish_front(put)
    furnish_back(put)
    if not cutaway:
        # jardin
        put("Stairs_Porch_3step", 0, -4.12, -0.5)
        put("Mailbox", 3.9, -8.5, -0.5)
        put("Bench_Garden", -2.3, -4.6, -0.5)
        put("Plant_Pot_Large", 1.25, -4.45, 0.0)
        for i in range(5):
            put("Path_Stone_Tile", 0, -5.15 - i * 0.95, -0.46)
        for x in (-5, -3, 3, 5):
            put("Fence_Section_2m", x, -9.0, -0.5)
        put("Gate_Garden", 0, -9.0, -0.5)
        for y in (-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0):
            put("Fence_Section_2m", -6.0, y, -0.5, 90)
            put("Fence_Section_2m", 6.0, y, -0.5, 90)
        for x in (-5, -3, -1, 1, 3, 5):
            put("Fence_Section_2m", x, 9.0, -0.5)
        put("Column_Porch", 1.4, -4.9, -0.5) if False else None


def build_livingroom(objs, coll, ox, oy):
    put = make_putter(objs, coll, ox, oy)
    for ix in (-2, 0, 2):
        for iy in (-3, -1):
            put("Foundation_2m", ix, iy)
            put("Floor_Wood_2m", ix, iy)
    for x, n in {-2: "Wall_Solid_2m", 0: "Wall_Door_2m", 2: "Wall_Solid_2m"}.items():
        put(n, x, 0)
    put("Door_Frame_1m", 0, 0)
    put("Door_Interior", 0, 0)
    put("Wall_Window_2m", 3, -3, rz=90)
    put("Wall_Window_Wide_2m", 3, -1, rz=90)
    put("Window_Casement_1.2m", 3, -3, 0.9, 90)
    put("Window_Casement_Wide_1.6m", 3, -1, 0.9, 90)
    put("Wall_Corner_Post", 3, 0)
    put("Wall_Corner_Post", -3, 0)
    put("Wall_Corner_Post", 3, -4)
    furnish_front(put)


def build_example_place():
    objs = new_scene()
    spacing = 26.0
    zones = {
        "Exterior": make_coll("Zone_1_Exterior"),
        "Interior": make_coll("Zone_2_Interior_Cutaway"),
        "LivingRoom": make_coll("Zone_3_LivingRoom"),
    }
    xa, xb, xc = 0.0, spacing, spacing * 2
    build_house(objs, zones["Exterior"], xa, 0, cutaway=False)
    build_house(objs, zones["Interior"], xb, 0, cutaway=True)
    build_livingroom(objs, zones["LivingRoom"], xc, 0)

    # sols : jardin + dalles de présentation
    hk.MATS.setdefault("grass", ((0.30, 0.50, 0.22), 1.0, 0.0, {}))
    box_obj("Ground_Garden", "grass", xa - 10, xa + 10, -13, 11, -0.9, -0.5, zones["Exterior"], b=0)
    box_obj("Slab_Interior", "slab", xb - 6, xb + 6, -6, 6, -0.9, -0.5, zones["Interior"], b=0.02)
    box_obj("Slab_LivingRoom", "slab", xc - 5, xc + 5, -6, 2, -0.9, -0.5, zones["LivingRoom"], b=0.02)
    # titres
    for x, label, sub in ((xa, "1  EXTERIOR", "Complete house with garden"), (xb, "2  INTERIOR", "Cutaway view"), (xc, "3  LIVING ROOM", "Living, dining & kitchen")):
        text_obj(label, 1.2, (x, -15.2, -0.3), (math.pi / 2, 0, 0), "brand", zones["Exterior"] if x == xa else zones["Interior"] if x == xb else zones["LivingRoom"], align="CENTER", extrude=0.06)
        text_obj(sub, 0.5, (x, -15.4, -0.89), (0, 0, 0), "label", zones["Exterior"] if x == xa else zones["Interior"] if x == xb else zones["LivingRoom"], align="CENTER", extrude=0.004)
    # sol général
    box_obj("Place_Floor", "showroom_floor", -22, xc + 22, -34, 30, -1.0, -0.9, zones["Exterior"], b=0)

    setup_render((1600, 1000), samples=56)
    cams = {}
    cams["Exterior"] = add_camera("Cam_Exterior", (xa - 13, -17, 7.5), (xa, -0.5, 2.3), 30)
    cams["Interior"] = add_camera("Cam_Interior_Cutaway", (xb - 9.0, -11.0, 11.0), (xb + 0.2, 0.0, 0.6), 34)
    cams["LivingRoom"] = add_camera("Cam_LivingRoom", (xc - 5.2, -6.6, 4.0), (xc - 0.8, -1.8, 0.9), 34)
    cams["Overview"] = add_camera("Cam_Overview", (xb, -50, 27), (xb, -3, 0.5), 25, (2400, 800))
    bpy.context.scene.camera = cams["Exterior"]
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCENES, "Example_Place.blend"))
    export_glb_all("Example_Place.glb")
    return {"scene": "Example_Place", "views": [
        {"id": "overview", "label": "Overview", "target": gltf_xyz((xb, -2, 0.5)), "orbit": [0, 62, 78]},
        {"id": "exterior", "label": "1 Exterior", "target": gltf_xyz((xa, 0, 2.0)), "orbit": [-35, 68, 22]},
        {"id": "interior", "label": "2 Interior (cutaway)", "target": gltf_xyz((xb, 0, 0.8)), "orbit": [-35, 52, 17]},
        {"id": "livingroom", "label": "3 Living room", "target": gltf_xyz((xc - 0.5, -1.8, 0.9)), "orbit": [-35, 62, 9]},
    ]}


def export_glb_all(filename):
    bpy.ops.object.select_all(action="DESELECT")
    first = None
    for o in bpy.context.scene.objects:
        if o.type == "MESH" and not o.hide_render:
            o.select_set(True)
            first = first or o
    bpy.context.view_layer.objects.active = first
    bpy.ops.export_scene.gltf(filepath=os.path.join(SCENES, filename), export_format="GLB", use_selection=True, export_yup=True,
                              export_cameras=False, export_lights=False)


if __name__ == "__main__":
    which = [a for a in sys.argv[1:] if a in ("showroom", "place")] or ["showroom", "place"]
    meta = {}
    if "showroom" in which:
        meta["showroom"] = build_showroom()
        print("showroom OK")
    if "place" in which:
        meta["place"] = build_example_place()
        print("place OK")
    path = os.path.join(SCENES, "views.json")
    old = json.load(open(path)) if os.path.exists(path) else {}
    old.update(meta)
    json.dump(old, open(path, "w"), indent=1)
