"""Rend l'aperçu des 8 pioches : python tools/pickaxes/render_pickaxes.py <Pickaxes_All.blend> <sortie.png> [vue]   (vue : front | q)"""
import math, sys
import bpy
blend, out = sys.argv[1], sys.argv[2]
view = sys.argv[3] if len(sys.argv) > 3 else "front"
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
cam = bpy.data.objects["Cam"]
if view == "q":
    cam.location = (-3.2, -9.2, 2.4); cam.rotation_euler = (math.radians(76), 0, math.radians(-19)); cam.data.lens = 52
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
