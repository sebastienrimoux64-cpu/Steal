"""Génère HomeKit/ASSET_LIST.csv (dimensions, polys, matériaux) à partir de la bibliothèque."""
import csv
import os
import bpy
from mathutils import Vector

root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "HomeKit")
bpy.ops.wm.open_mainfile(filepath=os.path.join(root, "HomeBuilderKit_Library.blend"))
rows = []
for o in sorted(bpy.data.objects, key=lambda o: (o.get("hk_category", ""), o.name)):
    if not o.get("hk_category"):
        continue
    me = o.data
    me.calc_loop_triangles()
    d = o.dimensions
    rows.append([o["hk_category"][3:], o.name, f"{d.x:.2f}", f"{d.y:.2f}", f"{d.z:.2f}", len(me.loop_triangles),
                 ", ".join(m.name[3:] for m in me.materials)])
with open(os.path.join(root, "ASSET_LIST.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Catégorie", "Asset", "Largeur X (m)", "Profondeur Y (m)", "Hauteur Z (m)", "Triangles", "Matériaux"])
    w.writerows(rows)
tot = sum(r[5] for r in rows)
print(len(rows), "assets,", tot, "triangles au total")
cats = {}
for r in rows:
    cats.setdefault(r[0], []).append(r)
with open(os.path.join(root, "_stats.txt"), "w", encoding="utf-8") as f:
    f.write(f"{len(rows)} {tot} {max(r[5] for r in rows)} {sum(r[5] for r in rows)//len(rows)}\n")
    for c, rs in cats.items():
        f.write(f"{c}: " + ", ".join(r[1] for r in rs) + "\n")
