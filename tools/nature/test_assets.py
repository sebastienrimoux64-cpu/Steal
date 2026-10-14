"""Banc d'essai : python test_assets.py <module.fonction> ... -> rend une planche contact."""
import importlib
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import natlib as N
from PIL import Image


def atlas_material(path):
    m = bpy.data.materials.new("Atlas"); m.use_nodes = True
    t = m.node_tree.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path); t.interpolation = "Linear"
    b = m.node_tree.nodes["Principled BSDF"]; b.inputs["Roughness"].default_value = 0.85
    m.node_tree.links.new(t.outputs["Color"], b.inputs["Base Color"])
    return m


def main():
    out = sys.argv[-1]
    q = int(os.environ.get("Q", "0"))
    specs = [a for a in sys.argv[sys.argv.index("--") + 1:-1]]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat = atlas_material(N.ATLAS_PNG)
    scn = bpy.context.scene
    coll = scn.collection
    x = 0.0
    spans = []
    for s in specs:
        mod, fn = s.split(".")
        f = getattr(importlib.import_module(mod), fn)
        b = N.B(fn, q=q, seed=3)
        f(b)
        obj = b.finish(mat)
        coll.objects.link(obj)
        w = max(obj.dimensions.x, obj.dimensions.y)
        x += w * 0.5 + 0.3
        obj.location.x = x
        spans.append((x, obj.dimensions.z, w, len(obj.data.polygons)))
        x += w * 0.5 + 0.3
        print(fn, "faces", len(obj.data.polygons), "dim", tuple(round(d, 2) for d in obj.dimensions))
    width = x
    hmax = max(s[1] for s in spans)
    # sol
    g = bpy.data.objects.new("g", bpy.data.meshes.new("g"))
    g.data.from_pydata([(-5, -8, 0), (width + 5, -8, 0), (width + 5, 12, 0), (-5, 12, 0)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("gm"); gm.use_nodes = True
    gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.12, 0.2, 0.06, 1)
    g.data.materials.append(gm); coll.objects.link(g)
    sun = bpy.data.objects.new("sun", bpy.data.lights.new("sun", "SUN")); sun.data.energy = 4; sun.rotation_euler = (1.0, 0.2, -0.7); coll.objects.link(sun)
    w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.55, 0.7, 0.9, 1); w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
    cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); cam.data.lens = 40
    dist = max(width * 1.25, hmax * 2.4)
    cam.location = (width / 2, -dist, hmax * 0.55); tgt = Vector((width / 2, 0, hmax * 0.45))
    cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(cam); scn.camera = cam
    scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 32; scn.cycles.use_denoising = True
    scn.view_settings.view_transform = "AgX"
    scn.render.resolution_x = int(os.environ.get("RW", "1500")); scn.render.resolution_y = int(os.environ.get("RH", "700"))
    scn.render.filepath = out
    bpy.ops.render.render(write_still=True)


main()
