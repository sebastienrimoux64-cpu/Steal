"""Rend une miniature PNG par asset : python tools/render_home_kit.py <lib.blend> <dossier_sortie> <i> <n> [taille]
(i/n : tranche de la liste, pour paralléliser)."""
import sys
import bpy
from mathutils import Vector

lib, out, idx, nproc = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
size = int(sys.argv[5]) if len(sys.argv) > 5 else 480
bpy.ops.wm.open_mainfile(filepath=lib)
scn = bpy.context.scene
scn.render.engine = "CYCLES"
scn.cycles.device = "CPU"
scn.cycles.samples = 20
scn.cycles.use_denoising = False
scn.render.resolution_x = scn.render.resolution_y = size
scn.render.film_transparent = False
world = bpy.data.worlds.new("w"); scn.world = world
world.use_nodes = True
bg = world.node_tree.nodes["Background"]
bg.inputs["Color"].default_value = (0.40, 0.44, 0.50, 1)
bg.inputs["Strength"].default_value = 1.4
sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN"))
sun.data.energy = 3.0
sun.rotation_euler = (0.9, 0.3, -0.7)
scn.collection.objects.link(sun)
floor = bpy.data.objects.new("floor", bpy.data.meshes.new("floor"))
floor.data.from_pydata([(-60, -60, -0.001), (60, -60, -0.001), (60, 60, -0.001), (-60, 60, -0.001)], [], [(0, 1, 2, 3)])
fm = bpy.data.materials.new("floor"); fm.diffuse_color = (0.9, 0.9, 0.9, 1)
fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.42, 0.41, 1)
floor.data.materials.append(fm)
scn.collection.objects.link(floor)
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
cam.data.lens = 50
scn.collection.objects.link(cam)
scn.camera = cam

objs = sorted([o for o in bpy.data.objects if o.get("hk_category")], key=lambda o: o.name)
for i, o in enumerate(objs):
    if i % nproc != idx:
        continue
    for p in objs:
        p.hide_render = p is not o
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    mx = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    c = (mn + mx) / 2
    r = max((mx - mn).length, 0.3)
    cam.location = c + Vector((-0.75, -1.0, 0.6)).normalized() * r * 1.35
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    scn.render.filepath = f"{out}/{o['hk_category']}__{o.name}.png"
    bpy.ops.render.render(write_still=True)
