"""Rend un aperçu PNG (Workbench) d'un .blend de bijū : python tools/render_preview.py models/Kurama.blend out.png [frame] [action]"""
import sys
import bpy
from mathutils import Vector

src, out = sys.argv[1], sys.argv[2]
frame = int(sys.argv[3]) if len(sys.argv) > 3 else 1
action = sys.argv[4] if len(sys.argv) > 4 else None
bpy.ops.wm.open_mainfile(filepath=src)
scn = bpy.context.scene
if action:
    for o in bpy.data.objects:
        if o.type == "ARMATURE" and action in bpy.data.actions:
            o.animation_data.action = bpy.data.actions[action]
scn.frame_set(frame)
scn.render.engine = "CYCLES"  # Workbench/Eevee demandent un GPU ; Cycles CPU marche en headless
scn.cycles.device = "CPU"
scn.cycles.samples = 24
scn.cycles.use_denoising = False
scn.render.resolution_x, scn.render.resolution_y = 900, 700
world = bpy.data.worlds.new("w"); scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.55, 0.62, 0.72, 1)
bg.inputs["Strength"].default_value = 1.0
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.5
sun.rotation_euler = (0.9, 0.2, 0.6)
scn.collection.objects.link(sun)
floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
floor.data.from_pydata([(-80, -80, 0), (80, -80, 0), (80, 80, 0), (-80, 80, 0)], [], [(0, 1, 2, 3)])
scn.collection.objects.link(floor)
pts = []
for o in bpy.data.objects:
    if o.type == "MESH" and o.name != "floor":
        dg = bpy.context.evaluated_depsgraph_get()
        eo = o.evaluated_get(dg)
        pts += [eo.matrix_world @ Vector(c) for c in eo.bound_box]
mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
center = (mn + mx) / 2
size = max((mx - mn).length, 1)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
scn.collection.objects.link(cam)
cam.data.lens = 50
d = Vector((-0.8, -1.0, 0.55)).normalized() * size * 1.15
cam.location = center + d
direction = center - cam.location
cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
scn.camera = cam
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
