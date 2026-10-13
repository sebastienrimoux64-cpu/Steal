"""Aperçu GIF d'une animation R6 (vue 3/4 + vue de côté) : python tools/anim/preview.py <Idle_X.blend> <sortie.gif> [fps] [taille]
Les couleurs sont appliquées uniquement pour l'aperçu (le .blend livré n'est pas modifié)."""
import os, sys, tempfile
import bpy
from mathutils import Vector
from PIL import Image

blend, out = sys.argv[1], sys.argv[2]
fps = int(sys.argv[3]) if len(sys.argv) > 3 else 15
size = int(sys.argv[4]) if len(sys.argv) > 4 else 300
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
body = {"Head": (0.96, 0.82, 0.68), "Torso": (0.22, 0.46, 0.82), "Left Arm": (0.90, 0.32, 0.26), "Right Arm": (0.26, 0.72, 0.32),
        "Left Leg": (0.92, 0.76, 0.22), "Right Leg": (0.62, 0.32, 0.72)}
for o in bpy.data.objects:
    if o.type == "MESH":
        if o.name in body:
            m = bpy.data.materials.new(o.name); m.use_nodes = True
            m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = body[o.name] + (1,)
            o.data.materials.clear(); o.data.materials.append(m)
        else:
            o.hide_render = True
scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 8; scn.cycles.use_denoising = False
scn.render.resolution_x = scn.render.resolution_y = size
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); sun.data.energy = 4.2; sun.rotation_euler = (0.9, 0.3, 2.4); scn.collection.objects.link(sun)
fl = bpy.data.objects.new("f", bpy.data.meshes.new("f")); fl.data.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)]); fm = bpy.data.materials.new("floor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.36, 0.38, 0.42, 1)
fl.data.materials.append(fm); scn.collection.objects.link(fl)
cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); cam.data.lens = 50; scn.collection.objects.link(cam); scn.camera = cam
views = [((-5.6, 9.2, 4.6), (0, 0, 2.7)), ((11.5, 0, 3.4), (0, 0, 2.7))]
f0, f1 = scn.frame_start, scn.frame_end
n = max(2, int(round((f1 - f0) / scn.render.fps * fps)))
frames = []
tmp = tempfile.mkdtemp()
for i in range(n):
    scn.frame_set(f0 + int(round(i * (f1 - f0) / n)))
    row = []
    for j, (loc, tgt) in enumerate(views):
        cam.location = loc
        cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(tmp, f"{i}_{j}.png"); scn.render.filepath = p
        bpy.ops.render.render(write_still=True); row.append(Image.open(p).convert("RGB"))
    sheet = Image.new("RGB", (size * len(row), size)); [sheet.paste(im, (k * size, 0)) for k, im in enumerate(row)]
    frames.append(sheet.convert("P", palette=Image.ADAPTIVE, colors=96))
frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True, disposal=2)
print("gif", out, len(frames), "images", fps, "fps")
