"""python tools/pickaxes_real/render.py <fichier.blend> <sortie.png> [samples] [largeur hauteur]"""
import sys
import bpy
blend, out = sys.argv[1], sys.argv[2]
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 96
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
scn.cycles.samples = samples
if len(sys.argv) > 5:
    scn.render.resolution_x, scn.render.resolution_y = int(sys.argv[4]), int(sys.argv[5])
scn.render.filepath = out
bpy.ops.render.render(write_still=True)
