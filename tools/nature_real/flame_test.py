import math, os, sys, importlib
import bpy
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import studio_real as S, rmat, a_fire
a = sys.argv[sys.argv.index("--") + 1:]
out = a[0]; frames = [int(x) for x in a[1].split(",")]; samples = int(a[2])
S.reset(); sc = S.cycles(samples, (260, 390))
sc.cycles.volume_step_rate = 0.5
w = bpy.data.worlds.new("n"); sc.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.004, 0.004, 0.006, 1)
objs = a_fire.add_effects(sc.collection, with_smoke=False, n_sparks=0)
S.camera((0, -2.4, 0.62), (0, 0, 0.58), 40)
from PIL import Image
imgs = []
for f in frames:
    sc.frame_set(f); S.render(out.replace(".png", f"_{f}.png"))
    imgs.append(Image.open(out.replace(".png", f"_{f}.png")).convert("RGB"))
W = sum(i.width for i in imgs); sheet = Image.new("RGB", (W, imgs[0].height))
x = 0
for i in imgs:
    sheet.paste(i, (x, 0)); x += i.width
sheet.save(out)
