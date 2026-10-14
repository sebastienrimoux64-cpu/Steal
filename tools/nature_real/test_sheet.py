"""Planche contact : python test_sheet.py -- <sortie.png> <w> <h> <sol> <cam x y z> <cible x y z> <lens> <samples> mod.fn@x[@y] ..."""
import importlib, os, sys
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rgeo, studio_real as S
a = sys.argv[sys.argv.index("--") + 1:]
out, w, h, gk = a[0], int(a[1]), int(a[2]), a[3]
cam = [float(x) for x in a[4:7]]; tgt = [float(x) for x in a[7:10]]; lens = float(a[10]); samples = int(a[11])
S.reset(); S.cycles(samples, (w, h)); S.sky(); 
if gk != "none":
    S.ground(gk)
S.camera(cam, tgt, lens)
for spec in a[12:]:
    parts = spec.split("@")
    mod, fn = parts[0].split(".")
    f = getattr(importlib.import_module(mod), fn)
    b = rgeo.RB(fn, seed=1); f(b); o = b.finish(); S.link(o)
    o.location = (float(parts[1]) if len(parts) > 1 else 0.0, float(parts[2]) if len(parts) > 2 else 0.0, 0.0)
    print(fn, "faces", len(o.data.polygons), "dim", tuple(round(d, 2) for d in o.dimensions))
S.render(out)
