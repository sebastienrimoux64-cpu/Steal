"""Assemble tous les assets réalistes dans un seul .blend (une rangée par famille, ciel + sol + une caméra par famille)."""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import studio_real as S
import build_real as BR

OUT = BR.OUT
FAMS = ["Arbres", "Plantes", "Accessoires", "Décor"]


def main():
    S.reset()
    sc = S.cycles(48, (1920, 960))
    sc.frame_start, sc.frame_end = 1, 120
    S.sky()
    y = 0.0
    cams = {}
    for fam in FAMS:
        names = [a[0] for a in BR.ASSETS if a[4] == fam]
        coll = bpy.data.collections.new(fam)
        sc.collection.children.link(coll)
        x = 0.0
        row_objs = []
        for name in names:
            path = os.path.join(OUT, fam, f"{name}.blend")
            with bpy.data.libraries.load(path) as (src, dst):
                dst.objects = [o for o in src.objects if o not in ("sol", "sol-lointain", "Soleil", "Camera")]
            objs = [o for o in dst.objects if o is not None]
            # largeur de l'asset (emprise des maillages)
            meshes = [o for o in objs if o.type == "MESH"]
            lo = Vector((1e9, 1e9, 1e9))
            hi = Vector((-1e9, -1e9, -1e9))
            for o in meshes:
                if o.name.startswith(("flamme", "fumee", "etincelle")):
                    continue
                for c in o.bound_box:
                    p = o.matrix_world @ Vector(c)
                    lo = Vector((min(lo.x, p.x), min(lo.y, p.y), min(lo.z, p.z)))
                    hi = Vector((max(hi.x, p.x), max(hi.y, p.y), max(hi.z, p.z)))
            w = max(hi.x - lo.x, 0.5)
            cx = (lo.x + hi.x) / 2
            for o in objs:
                coll.objects.link(o)
                if o.parent is None:
                    o.location = (o.location.x + x + w / 2 - cx, o.location.y + y, o.location.z)
            x += w + 2.0
            row_objs.extend(meshes)
        # caméra de la famille
        total = x - 2.0
        cam = bpy.data.objects.new(f"Camera-{fam}", bpy.data.cameras.new(f"Camera-{fam}"))
        cam.data.lens = 40
        hmax = max((max((o.matrix_world @ Vector(c)).z for c in o.bound_box) for o in row_objs if not o.name.startswith(("flamme", "fumee", "etincelle"))), default=2)
        dist = total * 0.5 / math.tan(math.atan(18 / 40)) * 1.08
        cam.location = (total / 2, y - dist, min(hmax * 0.55, 4.0))
        tgt = Vector((total / 2, y, hmax * 0.4))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.collection.objects.link(cam)
        cams[fam] = cam
        y -= 24.0
    S.ground("grass", size=800, relief=0.0, near=2.0, res=2)
    sc.camera = cams["Arbres"]
    path = os.path.join(OUT, "NaturePack_Realiste.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print("combiné :", path, os.path.getsize(path) // 1000000, "Mo")


main()
