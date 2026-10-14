"""Rend l'animation du feu de camp (boucle de 120 images) : python render_fire.py <feu-de-camp.blend> <dossier sortie> [pas=5] [taille=540] [samples=24]"""
import os
import sys

import bpy
from PIL import Image

path, out = sys.argv[-5] if len(sys.argv) > 5 else sys.argv[-2], None
args = sys.argv[sys.argv.index("--") + 1:]
blend, outdir = args[0], args[1]
step = int(args[2]) if len(args) > 2 else 5
size = int(args[3]) if len(args) > 3 else 540
samples = int(args[4]) if len(args) > 4 else 24
bpy.ops.wm.open_mainfile(filepath=blend)
sc = bpy.context.scene
sc.render.resolution_x = sc.render.resolution_y = size
sc.render.resolution_percentage = 100
sc.cycles.samples = samples
os.makedirs(outdir, exist_ok=True)
frames = []
for f in range(1, 121, step):
    sc.frame_set(f)
    p = os.path.join(outdir, f"feu_{f:03d}.png")
    sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    frames.append(p)
ims = [Image.open(p).convert("P", palette=Image.ADAPTIVE, colors=128) for p in frames]
gif = os.path.join(os.path.dirname(outdir.rstrip("/")), "feu-de-camp.gif")
ims[0].save(gif, save_all=True, append_images=ims[1:], duration=int(1000 * step / 24), loop=0, optimize=True)
print("GIF", gif)
