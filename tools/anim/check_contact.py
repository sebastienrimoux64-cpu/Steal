"""Vérifie le contact entre les deux bras (distance entre surfaces) dans une animation : python tools/anim/check_contact.py <fichier.blend> <t0> <t1>"""
import sys
import bpy
from mathutils.bvhtree import BVHTree

path, t0, t1 = sys.argv[-3], float(sys.argv[-2]), float(sys.argv[-1])
bpy.ops.wm.open_mainfile(filepath=path)
scn = bpy.context.scene
fps = scn.render.fps
rows = []
t = t0
while t <= t1 + 1e-9:
    scn.frame_set(int(round(t * fps)))
    dg = bpy.context.evaluated_depsgraph_get()
    def tree(name):
        o = bpy.data.objects[name].evaluated_get(dg)
        verts = [o.matrix_world @ v.co for v in o.data.vertices]
        polys = [tuple(p.vertices) for p in o.data.polygons]
        return BVHTree.FromPolygons(verts, polys), verts
    tr, vr = tree("Right Arm"); tl, vl = tree("Left Arm")
    # distance surface-surface (approx.) : plus proche point de L pour chaque sommet de R, et inverse
    d = min(min((tl.find_nearest(v)[3] for v in vr)), min((tr.find_nearest(v)[3] for v in vl)))
    overlap = len(tr.overlap(tl))
    rows.append((t, d, overlap))
    t += 0.05
bad = [r for r in rows if r[1] > 0.06 and r[2] == 0]
print(f"{len(rows)} instants testés de {t0:.2f} s à {t1:.2f} s ; contact (distance < 6 cm ou mailles qui se croisent) : {len(rows) - len(bad)}/{len(rows)}")
if bad:
    print("sans contact :", ", ".join(f"{r[0]:.2f}s (écart {r[1]:.2f})" for r in bad))
print("écart maximal :", f"{max(r[1] for r in rows):.3f}")
