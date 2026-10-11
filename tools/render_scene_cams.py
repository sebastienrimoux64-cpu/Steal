"""Rend des caméras d'un .blend : python tools/render_scene_cams.py <blend> <dossier> <cam1,cam2,...|all> [samples]"""
import os, sys
import bpy
blend, out, names = sys.argv[1], sys.argv[2], sys.argv[3]
samples = int(sys.argv[4]) if len(sys.argv) > 4 else None
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
os.makedirs(out, exist_ok=True)
cams = [o for o in bpy.data.objects if o.type == "CAMERA"]
if names != "all":
    wanted = set(names.split(","))
    cams = [c for c in cams if c.name in wanted]
if samples:
    scn.cycles.samples = samples
for cam in cams:
    scn.camera = cam
    if "res_x" in cam:
        scn.render.resolution_x, scn.render.resolution_y = int(cam["res_x"]), int(cam["res_y"])
    scn.render.filepath = os.path.join(out, cam.name + ".png")
    bpy.ops.render.render(write_still=True)
