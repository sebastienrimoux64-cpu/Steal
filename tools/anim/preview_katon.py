"""Aperçu GIF du Katon avec une boule de feu AJOUTÉE UNIQUEMENT À L'APERÇU (le .blend livré ne contient que l'animation du personnage).
    python tools/anim/preview_katon.py <Jutsu_Katon_...blend> <sortie.gif> [fps] [taille]"""
import math, os, sys, tempfile
import bpy
from mathutils import Vector
from PIL import Image

blend, out = sys.argv[1], sys.argv[2]
fps = int(sys.argv[3]) if len(sys.argv) > 3 else 20
size = int(sys.argv[4]) if len(sys.argv) > 4 else 280
bpy.ops.wm.open_mainfile(filepath=blend)
scn = bpy.context.scene
body = {"Head": (0.96, 0.82, 0.68), "Torso": (0.22, 0.46, 0.82), "Left Arm": (0.90, 0.32, 0.26), "Right Arm": (0.26, 0.72, 0.32),
        "Left Leg": (0.92, 0.76, 0.22), "Right Leg": (0.62, 0.32, 0.72)}
for o in bpy.data.objects:
    if o.type == "MESH":
        if o.name in body:
            m = bpy.data.materials.new(o.name); m.use_nodes = True
            m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = body[o.name] + (1,)
            o.data.materials.clear(); o.data.materials.append(m)
        else:
            o.hide_render = True
scn.render.engine = "CYCLES"; scn.cycles.device = "CPU"; scn.cycles.samples = 12; scn.cycles.use_denoising = False
scn.render.resolution_x = scn.render.resolution_y = size
w = bpy.data.worlds.new("w"); scn.world = w; w.use_nodes = True
w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.52, 0.58, 0.68, 1)
w.node_tree.nodes["Background"].inputs["Strength"].default_value = 1.0
sun = bpy.data.objects.new("s", bpy.data.lights.new("s", "SUN")); sun.data.energy = 3.6; sun.rotation_euler = (0.9, 0.3, 2.4); scn.collection.objects.link(sun)
fl = bpy.data.objects.new("f", bpy.data.meshes.new("f")); fl.data.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
fm = bpy.data.materials.new("floor"); fm.use_nodes = True
fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.42, 0.43, 0.46, 1)
fl.data.materials.append(fm); scn.collection.objects.link(fl)

# --- boule de feu (aperçu seulement) ---
def fire_mat(name, col, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = col + (1,); b.inputs["Emission Color"].default_value = col + (1,); b.inputs["Emission Strength"].default_value = strength
    return m
def sphere(name, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=24, ring_count=12)
    o = bpy.context.object; o.name = name; o.data.materials.append(mat); bpy.ops.object.shade_smooth(); return o
def make_blob(tag):
    return (sphere(tag + "_outer", fire_mat(tag + "o", (1.0, 0.18, 0.02), 2.4)), sphere(tag + "_inner", fire_mat(tag + "i", (1.0, 0.55, 0.08), 4.2)))
jet, ball = make_blob("jet"), make_blob("ball")
light = bpy.data.objects.new("fl", bpy.data.lights.new("fl", "POINT")); light.data.energy = 0; light.data.color = (1.0, 0.45, 0.1); scn.collection.objects.link(light)
def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def show(blob, center, sc, vis):
    for k, o in enumerate(blob):
        o.hide_render = not vis
        if vis:
            f = 1.0 if k == 0 else 0.62
            o.location = center; o.scale = (sc[0] * f, sc[1] * f, sc[2] * f)
def mouth_pos():
    bpy.context.view_layer.update()
    h = bpy.data.objects["Head"].evaluated_get(bpy.context.evaluated_depsgraph_get())
    pts = [h.matrix_world @ v.co for v in h.data.vertices]
    c = sum(pts, Vector()) / len(pts)
    return c + Vector((0, 0.75, -0.2))
def fire(t):
    t0 = 3.45
    m = mouth_pos() if t >= t0 - 0.05 else Vector((0, 1.0, 4.0))
    # jet : sort de la bouche et s'allonge
    if t0 <= t <= 4.7:
        u = smooth((t - t0) / 0.9); fade = 1 - smooth((t - 4.2) / 0.5)
        L = (0.2 + 3.6 * u) ; r = (0.16 + 0.8 * u) * (0.3 + 0.7 * fade)
        show(jet, m + Vector((0, L / 2, 0)), (r, L / 2 + r * 0.4, r), True)
    else:
        show(jet, m, (1, 1, 1), False)
    # boule : grossit et file vers l'avant
    if 4.0 <= t <= 5.6:
        v = (t - 4.0) / 1.6; fade = 1 - smooth((t - 5.0) / 0.6)
        r = (0.5 + 1.5 * smooth(v * 1.5)) * (0.25 + 0.75 * fade)
        c = Vector((0, m.y + 2.8 + 7.5 * smooth(v), m.z - 0.2 + 0.2 * v))
        show(ball, c, (r, r * 1.2, r), True)
        light.location = c; light.data.energy = 4500 * (r / 2.0) ** 2 * fade
    else:
        show(ball, m, (1, 1, 1), False)
        light.data.energy = 3000 * (1 - abs(smooth((t - 3.9) / 0.4) * 2 - 1)) if 3.45 <= t <= 4.35 else 0
        if 3.45 <= t <= 4.35: light.location = m + Vector((0, 1.5, 0))

cam = bpy.data.objects.new("c", bpy.data.cameras.new("c")); cam.data.lens = 36; scn.collection.objects.link(cam); scn.camera = cam
views = [((-2.2, 10.0, 4.6), (0, 2.4, 3.0)), ((16.0, 3.5, 4.0), (0, 3.5, 3.2))]
f0, f1 = scn.frame_start, scn.frame_end
n = int(round((f1 - f0) / scn.render.fps * fps))
tmp = tempfile.mkdtemp(); frames = []
for i in range(n):
    fr = f0 + int(round(i * (f1 - f0) / n)); scn.frame_set(fr); fire(fr / scn.render.fps)
    row = []
    for j, (loc, tgt) in enumerate(views):
        cam.location = loc; cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
        p = os.path.join(tmp, f"{i}_{j}.png"); scn.render.filepath = p; bpy.ops.render.render(write_still=True); row.append(Image.open(p).convert("RGB"))
    sheet = Image.new("RGB", (size * len(row), size)); [sheet.paste(im, (k * size, 0)) for k, im in enumerate(row)]
    frames.append(sheet.convert("P", palette=Image.ADAPTIVE, colors=128))
frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True, disposal=2)
print("gif", out, len(frames), "images")
