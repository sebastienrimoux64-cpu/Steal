"""Banc d'essai réaliste : python test_real.py -- <module.fonction> <sol> <cam x y z> <cible x y z> <lens> <sortie.png> [samples] [w h]"""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rgeo
import studio_real as S


def main():
    a = sys.argv[sys.argv.index("--") + 1:]
    spec, gkind = a[0], a[1]
    cam = [float(x) for x in a[2:5]]
    tgt = [float(x) for x in a[5:8]]
    lens = float(a[8])
    out = a[9]
    samples = int(a[10]) if len(a) > 10 else 32
    res = (int(a[11]), int(a[12])) if len(a) > 12 else (900, 675)
    S.reset()
    S.cycles(samples, res)
    S.sky()
    S.ground(gkind)
    mod, fn = spec.split(".")
    f = getattr(importlib.import_module(mod), fn)
    b = rgeo.RB(fn, seed=int(os.environ.get("SEED", "1")))
    f(b)
    obj = b.finish()
    S.link(obj)
    if cam[0] == 0 and cam[1] == 0 and cam[2] == 0:
        import mathutils
        bb = [obj.matrix_world @ mathutils.Vector(c) for c in obj.bound_box]
        lo = mathutils.Vector((min(v.x for v in bb), min(v.y for v in bb), min(v.z for v in bb)))
        hi = mathutils.Vector((max(v.x for v in bb), max(v.y for v in bb), max(v.z for v in bb)))
        ctr = (lo + hi) / 2
        size = max(hi.x - lo.x, hi.z - lo.z)
        dist = size * 0.95 / (res[0] / res[1] if res[0] < res[1] else 1.0) * 1.0 / math.tan(math.atan(18 / lens)) * 0.72 * (1.0 if res[0] >= res[1] else res[1] / res[0])
        S.camera((ctr.x + dist * 0.15, ctr.y - dist, ctr.z + size * 0.05), (ctr.x, ctr.y, ctr.z * 0.95), lens)
    else:
        S.camera(cam, tgt, lens)
    print("faces", len(obj.data.polygons), "dim", tuple(round(d, 2) for d in obj.dimensions))
    S.render(out)


main()
