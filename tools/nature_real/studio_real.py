"""Scène de présentation réaliste : ciel Nishita + soleil, sol procédural, caméra, réglages Cycles."""
import math

import bpy
from mathutils import Vector

import rmat
from mathutils import Vector


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0


def cycles(samples=48, res=(1200, 900), denoise=True, volume=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = denoise
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 10
    sc.cycles.volume_bounces = 2
    sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = "AgX - Medium High Contrast"
    except Exception:
        pass
    sc.render.film_transparent = False
    return sc


def sky(sun_elev=38, sun_rot=262, strength=0.32, air=0.55, dust=0.6, sun_energy=5.2, sun_size=0.8):
    sc = bpy.context.scene
    w = bpy.data.worlds.new("Ciel")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    sk = nt.nodes.new("ShaderNodeTexSky")
    sk.sky_type = "MULTIPLE_SCATTERING"
    sk.sun_elevation = math.radians(sun_elev)
    sk.sun_rotation = math.radians(sun_rot)
    sk.sun_size = math.radians(sun_size)
    sk.sun_intensity = 0.0       # le soleil est une vraie lampe (ombres nettes)
    sk.air_density = air
    sk.aerosol_density = dust
    bg.inputs["Strength"].default_value = strength
    nt.links.new(sk.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sun = bpy.data.objects.new("Soleil", bpy.data.lights.new("Soleil", "SUN"))
    sun.data.energy = sun_energy
    sun.data.angle = math.radians(0.6)
    sun.data.color = (1.0, 0.93, 0.82)
    el, az = math.radians(sun_elev), math.radians(sun_rot)
    d = Vector((-math.cos(el) * math.sin(az), -math.cos(el) * math.cos(az), -math.sin(el)))   # direction de la lumière
    sun.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(sun)
    return sk


def ground(kind="grass", size=600, z=0.0, scale_uv=1.0, relief=0.14, near=26.0, res=200):
    """Sol : grand plan lointain + terrain proche subdivisé et modelé (collines douces, zone plate autour de l'origine)."""
    import bmesh, math as _m
    from rgeo import fbm
    mat = rmat.ground("sol-" + kind, kind)
    me = bpy.data.meshes.new("sol-lointain")
    h = size / 2
    me.from_pydata([(-h, -h, z - 0.02), (h, -h, z - 0.02), (h, h, z - 0.02), (-h, h, z - 0.02)], [], [(0, 1, 2, 3)])
    o = bpy.data.objects.new("sol-lointain", me)
    o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=res, y_segments=res, size=near / 2)
    for v in bm.verts:
        r = _m.hypot(v.co.x, v.co.y)
        k = min(1.0, max(0.0, (r - 2.5) / 6.0))
        k = k * k * (3 - 2 * k)
        v.co.z = z + relief * k * (fbm(Vector((v.co.x * 0.22, v.co.y * 0.22, 0.0)), 4, seed=1.0) + 0.25 * fbm(Vector((v.co.x * 1.4, v.co.y * 1.4, 3.0)), 3, seed=2.0))
    bm.normal_update()
    for f in bm.faces:
        f.smooth = True
    me2 = bpy.data.meshes.new("sol")
    bm.to_mesh(me2)
    bm.free()
    o2 = bpy.data.objects.new("sol", me2)
    o2.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o2)
    return o2


def camera(loc, target, lens=50, dof=None):
    cam = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    cam.data.lens = lens
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def link(obj, coll=None):
    (coll or bpy.context.scene.collection).objects.link(obj)
    return obj


def render(path):
    sc = bpy.context.scene
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
