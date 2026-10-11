"""Maison de démonstration assemblée avec les pièces du pack (images de présentation).
    python tools/make_home_showcase.py [dossier_images]"""
import math
import os
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_home_kit as hk

IMG = sys.argv[-1] if len(sys.argv) > 1 and not sys.argv[-1].endswith(".py") else os.path.join(hk.OUT, "Previews")
os.makedirs(IMG, exist_ok=True)

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

groups = {n: bpy.data.collections.new(n) for n in ("Walls", "Floor", "Roof", "Doors_Windows", "Furniture", "Decor", "Exterior")}
for g in groups.values():
    bpy.context.scene.collection.children.link(g)

def put(name, x, y, z=0.0, rz=0.0, group="Furniture"):
    o = objs[name].copy()          # copie liée : même maillage
    o.hide_render = False
    o.hide_viewport = False
    o.location = (x, y, z)
    o.rotation_euler = (0, 0, math.radians(rz))
    groups[group].objects.link(o)
    return o

# ---- gros œuvre : 6 m (X) x 8 m (Y) ----
for ix in (-2, 0, 2):
    for iy in (-3, -1, 1, 3):
        put("Foundation_2m", ix, iy, 0, group="Floor")
        put("Floor_Wood_2m" if iy > 0 or ix > 0 else "Floor_Wood_2m", ix, iy, 0, group="Floor")
# bains et cuisine en carrelage
for ix in (2,):
    for iy in (1, 3):
        put("Floor_Tile_2m", ix, iy, 0.001, group="Floor")

front = {-2: "Wall_Window_2m", 0: "Wall_Door_2m", 2: "Wall_Window_2m"}
for x, n in front.items():
    put(n, x, -4, group="Walls")
for x, n in {-2: "Wall_Solid_2m", 0: "Wall_Window_Wide_2m", 2: "Wall_Window_2m"}.items():
    put(n, x, 4, rz=180, group="Walls")
for y, n in {-3: "Wall_Window_2m", -1: "Wall_Solid_2m", 1: "Wall_Window_2m", 3: "Wall_Solid_2m"}.items():
    put(n, -3, y, rz=-90, group="Walls")
for y, n in {-3: "Wall_Solid_2m", -1: "Wall_Window_Wide_2m", 1: "Wall_Solid_2m", 3: "Wall_Window_2m"}.items():
    put(n, 3, y, rz=90, group="Walls")
for x, y in ((-3, -4), (3, -4), (-3, 4), (3, 4)):
    put("Wall_Corner_Post", x, y, group="Walls")
# cloisons intérieures
for x, n in {-2: "Wall_Solid_2m", 0: "Wall_Door_2m", 2: "Wall_Solid_2m"}.items():
    put(n, x, 0, group="Walls")
put("Wall_Solid_2m", 1, 1, rz=90, group="Walls")
put("Wall_Door_2m", 1, 3, rz=90, group="Walls")

# portes et fenêtres
put("Door_Frame_1m", 0, -4, group="Doors_Windows")
put("Door_Front", 0, -4, group="Doors_Windows")
put("Door_Frame_1m", 0, 0, group="Doors_Windows")
put("Door_Interior", 0, 0, rz=0, group="Doors_Windows")
put("Door_Frame_1m", 1, 3, rz=90, group="Doors_Windows")
put("Door_Interior", 1, 3, rz=90, group="Doors_Windows")
for x, y, rz, n in ((-2, -4, 0, "Window_Casement_1.2m"), (2, -4, 0, "Window_Casement_1.2m"),
                    (0, 4, 180, "Window_Casement_Wide_1.6m"), (-2, 0, 0, None),
                    (-3, -3, -90, "Window_Casement_1.2m"), (-3, 1, -90, "Window_Casement_1.2m"),
                    (3, -1, 90, "Window_Casement_Wide_1.6m"), (3, 3, 90, "Window_Casement_1.2m")):
    if n:
        put(n, x, y, 0.9, rz, group="Doors_Windows")
for x in (-2, 2):
    put("Shutter_Pair", x - 0.0, -4.14, 0.9, 0, group="Doors_Windows") if False else None

# plafond (masqué sur la vue en coupe)
for ix in (-2, 0, 2):
    for iy in (-3, -1, 1, 3):
        put("Ceiling_2m", ix, iy, 2.8, group="Roof")

# toiture : faîtage le long de Y, pentes vers ±X
for iy in (-3, -1, 1, 3):
    put("Roof_Slope_Tile_2m", -3, iy, 2.9, rz=-90, group="Roof")
    put("Roof_Slope_Tile_2m", 3, iy, 2.9, rz=90, group="Roof")
    put("Roof_Ridge_2m", 0, iy, 2.9 + 3 * math.tan(math.radians(35)), rz=90, group="Roof")
put("Roof_Gable_Triangle_6m", 0, -4, 2.8, group="Roof")
put("Roof_Gable_Triangle_6m", 0, 4, 2.8, rz=180, group="Roof")
put("Chimney", 2.3, 2.2, 2.9, group="Roof")

# ---- intérieur ----
# salon (les meubles regardent -Y / -X : visibles depuis la caméra de la vue en coupe)
put("TV_Stand_With_TV", -1.05, -0.32, rz=0)
put("Bookshelf_Tall", -2.4, -0.3, rz=0)
put("Sofa_3Seat", -1.8, -2.3, rz=180)
put("Table_Coffee", -1.8, -1.3, rz=0)
put("Rug_Rect_2x3", -1.8, -1.55, 0.03, rz=0, group="Decor")
put("Armchair", -2.55, -1.55, rz=90)
put("Lamp_Floor", -0.45, -2.9, group="Decor")
put("Plant_Pot_Large", -2.6, -3.45, group="Decor")
put("Frame_Landscape", -1.05, -0.12, 1.5, group="Decor")
put("Light_Pendant", -1.8, -1.6, group="Decor")
put("Table_Side", -0.4, -1.2, group="Decor")
put("Vase_Flowers", -0.4, -1.2, 0.5, group="Decor")
put("Books_Stack", -1.8, -1.3, 0.42, group="Decor")
# cuisine / salle à manger
rotk = -90
for n, y in (("Fridge_Tall", -3.52), ("Kitchen_Base_Drawers_60", -2.85), ("Kitchen_Cooker_60", -2.25),
             ("Kitchen_Sink_120", -1.35), ("Kitchen_Base_60", -0.45)):
    put(n, 2.6, y, rz=rotk)
for n, y in (("Kitchen_Wall_Cabinet_60", -2.85), ("Kitchen_Hood", -2.25), ("Kitchen_Wall_Cabinet_60", -1.65), ("Kitchen_Wall_Cabinet_60", -1.05)):
    put(n, 2.75, y, rz=rotk)
put("Table_Dining_1.6m", 0.95, -2.2, rz=90)
for x, y, rz in ((1.65, -2.7, -90), (1.65, -1.7, -90), (0.25, -2.7, 90), (0.25, -1.7, 90)):
    put("Chair_Dining", x, y, rz=rz)
put("Light_Pendant", 0.95, -2.2, group="Decor")
put("Plant_Small", 0.95, -2.2, 0.75, group="Decor")
put("Stool_Kitchen", 1.9, -0.65)
# chambre
put("Bed_Double", -1.3, 2.85)
put("Nightstand", -2.45, 3.65)
put("Nightstand", -0.15, 3.65)
put("Lamp_Table", -2.45, 3.65, 0.55, group="Decor")
put("Lamp_Table", -0.15, 3.65, 0.55, group="Decor")
put("Wardrobe_2Door", 0.68, 1.85, rz=-90)
put("Dresser_3Drawer", 0.7, 3.2, rz=-90)
put("Mirror_Wall_Round", 0.88, 3.2, 1.0, rz=-90, group="Decor")
put("Rug_Rect_2x3", -1.3, 2.3, 0.03, group="Decor")
put("Frame_Portrait", -1.3, 3.88, 1.35, rz=180, group="Decor")
put("Light_Ceiling_Flush", -1.3, 2.0, group="Decor")
put("Plant_Small", -2.7, 0.5, group="Decor")
# salle de bain
put("Bathtub", 2.05, 3.5, rz=90)
put("Toilet", 2.75, 1.5, rz=-90)
put("Sink_Pedestal", 2.75, 2.5, rz=-90)
put("Mirror_Cabinet", 2.9, 2.5, rz=-90, group="Decor")
put("Rug_Round_1.6m", 1.9, 1.6, 0.03, group="Decor") if False else None

# ---- extérieur ----
put("Stairs_Porch_3step", 0, -4.12, -0.5, group="Exterior")
put("Mailbox", 3.9, -8.5, -0.5, group="Exterior")
put("Bench_Garden", -2.3, -4.6, -0.5, group="Exterior")
put("Plant_Pot_Large", 1.25, -4.45, 0.0, group="Exterior")
put("Plant_Pot_Large", -0.9, -4.45, group="Exterior") if False else None
for i in range(5):
    put("Path_Stone_Tile", 0, -5.15 - i * 0.95, -0.46, group="Exterior")
for x in (-4, -2):
    put("Fence_Section_2m", x - 0.0 + 0.0, -9.5, group="Exterior") if False else None
for x in (-5, -3, 3, 5):
    put("Fence_Section_2m", x, -9.0, -0.5, group="Exterior")
put("Gate_Garden", 0, -9.0, -0.5, group="Exterior")
for y in (-7.0, -5.0, -3.0, -1.0, 1.0, 3.0, 5.0, 7.0):
    put("Fence_Section_2m", -6.0, y, -0.5, rz=90, group="Exterior")
    put("Fence_Section_2m", 6.0, y, -0.5, rz=90, group="Exterior")
for x in (-5, -3, -1, 1, 3, 5):
    put("Fence_Section_2m", x, 9.0, group="Exterior") if False else None

# sol herbeux
ground = bpy.data.objects.new("Ground", bpy.data.meshes.new("Ground"))
ground.data.from_pydata([(-40, -40, -0.5), (40, -40, -0.5), (40, 40, -0.5), (-40, 40, -0.5)], [], [(0, 1, 2, 3)])
ground.data.materials.append(hk.material("grass"))
groups["Exterior"].objects.link(ground)

# ---- éclairage + caméra ----
scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = 48
try:
    scn.cycles.use_denoising = True
    scn.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
scn.render.resolution_x, scn.render.resolution_y = 1600, 1000
world = bpy.data.worlds.new("sky"); scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.55, 0.72, 0.95, 1)
bg.inputs["Strength"].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 4.0
sun.data.angle = math.radians(2)
sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
scn.collection.objects.link(sun)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scn.collection.objects.link(cam)
scn.camera = cam

def shot(path, loc, target, lens=32):
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)

os.makedirs(hk.OUT, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(hk.OUT, "Showcase_House.blend"))
which = [] if "noimg" in sys.argv else ([a for a in sys.argv if a in ("ext", "int")] or ["ext", "int"])
if "ext" in which:
    shot(os.path.join(IMG, "House_Exterior.png"), (-13, -17, 7.5), (0, -0.5, 2.3), 30)
if "int" in which:
    for n in ("Roof",):
        for o in groups[n].objects:
            o.hide_render = True
    for g in ("Walls", "Doors_Windows"):
        for o in groups[g].objects:
            if abs(o.location.y + 4) < 0.01 or abs(o.location.x + 3) < 0.01:
                o.hide_render = True
    for o in groups["Exterior"].objects:
        if o.name.startswith(("Fence", "Gate", "Mailbox", "Path", "Stairs", "Bench")):
            o.hide_render = True
    shot(os.path.join(IMG, "House_Interior_Cutaway.png"), (-9.0, -11.0, 11.0), (0.2, 0.0, 0.6), 34)
    shot(os.path.join(IMG, "House_Livingroom_Closeup.png"), (-5.2, -6.6, 4.0), (-0.8, -1.8, 0.9), 34)
