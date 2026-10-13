"""Assemble les 8 pioches réalistes dans un seul .blend (alignées, studio)."""
import bpy, os, sys
from mathutils import Vector
sys.path.insert(0, os.path.dirname(__file__))
import make_real_pickaxes as M
ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "PickaxesRealistic")
SP = 0.62
M.reset()
for i, n in enumerate(M.ORDER):
    path = os.path.abspath(os.path.join(ROOT, f"Pickaxe_{n}_Realistic.blend"))
    with bpy.data.libraries.load(path) as (src, dst):
        dst.objects = [o for o in src.objects if o.startswith("Pickaxe")]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
        o.location.x = (i - 3.5) * SP
        o.rotation_euler[1] = 0
M.studio()
for o in bpy.data.objects:
    if o.type == "LIGHT":
        o.data.size *= 3.5; o.data.energy *= 5
        o.location.x *= 2.2; o.location.y *= 1.6
        o.rotation_euler = (Vector((0, 0, 0.47)) - o.location).to_track_quat('-Z', 'Y').to_euler()
bpy.data.materials["Floor"].node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.9
M.camera((0.0, -8.2, 0.62), (0.0, 0, 0.47), 50)
bpy.context.scene.render.resolution_x = 2400
bpy.context.scene.render.resolution_y = 900
out = os.path.abspath(os.path.join(ROOT, "Pickaxes_Realistic_All.blend"))
bpy.ops.wm.save_as_mainfile(filepath=out)
print("saved", out, [o.name for o in bpy.data.objects if o.type=="MESH"])
