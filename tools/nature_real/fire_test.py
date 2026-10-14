import math, os, sys
import bpy
from mathutils import Vector
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import rgeo, studio_real as S, a_fire, rmat
a = sys.argv[sys.argv.index("--") + 1:]
frame = int(a[0]); out = a[1]; samples = int(a[2]); res = (int(a[3]), int(a[4]))
S.reset(); sc = S.cycles(samples, res)
sc.frame_start, sc.frame_end = 1, 120
sc.cycles.volume_step_rate = 0.6
S.sky(sun_elev=-3, sun_rot=262, strength=0.9, sun_energy=0.0)
S.ground("dirt")
b = rgeo.RB("foyer", seed=2); a_fire.foyer(b); obj = b.finish(); S.link(obj)
a_fire.add_effects(sc.collection)
S.camera((1.5, -2.6, 0.95), (0, 0, 0.5), 38)
sc.frame_set(frame)
S.render(out)
