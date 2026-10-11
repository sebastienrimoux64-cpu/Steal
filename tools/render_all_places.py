"""Rend toutes les caméras des deux scènes (4 processus en parallèle) : python tools/render_all_places.py <dossier_sortie> [samples]"""
import os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor
import bpy
here = os.path.dirname(os.path.abspath(__file__))
root = os.path.dirname(here)
out = sys.argv[-2] if len(sys.argv) > 2 else os.path.join(root, "HomeKit", "Scenes", "Renders")
samples = sys.argv[-1] if sys.argv[-1].isdigit() else "32"
jobs = []
for name in ("Showroom", "Example_Place"):
    blend = os.path.join(root, "HomeKit", "Scenes", name + ".blend")
    bpy.ops.wm.open_mainfile(filepath=blend)
    for o in bpy.data.objects:
        if o.type == "CAMERA":
            jobs.append((blend, name, o.name))
def run(j):
    blend, scene, cam = j
    d = os.path.join(out, scene)
    os.makedirs(d, exist_ok=True)
    subprocess.run([sys.executable, os.path.join(here, "render_scene_cams.py"), blend, d, cam, samples],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("ok", scene, cam, flush=True)
with ThreadPoolExecutor(4) as ex:
    list(ex.map(run, jobs))
