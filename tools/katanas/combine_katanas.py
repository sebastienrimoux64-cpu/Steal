"""Assemble les 4 katanas réalistes dans un seul .blend (studio + caméra)."""
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import make_real_katanas as K
P = K.P
ROOT = K.OUT
SP = 0.26
P.reset()
for i, n in enumerate(K.ORDER):
    with bpy.data.libraries.load(os.path.join(ROOT, f"Katana_{n}_Realistic.blend")) as (src, dst):
        dst.objects = [o for o in src.objects if o.startswith("Katana")]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
        o.location.x = (i - 1.5) * SP
P.studio()
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.data.size *= 2.5; o.data.energy *= 2.2
        o.location.x *= 1.6; o.location.y *= 1.4
        o.rotation_euler = (Vector((0, 0, 0.5)) - o.location).to_track_quat("-Z", "Y").to_euler()
bpy.data.materials["Floor"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
P.camera((0.0, -3.1, 0.55), (0.0, 0, 0.55), 50)
bpy.context.scene.render.resolution_x = 2000
bpy.context.scene.render.resolution_y = 1000
out = os.path.join(ROOT, "Katanas_Realistic_All.blend")
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out)
