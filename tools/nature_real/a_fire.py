"""Feu de camp réaliste animé : foyer de pierres, bûches carbonisées, lit de braises, flammes volumétriques, fumée, étincelles, lumière vacillante."""
import math
import random

import bpy
from mathutils import Vector, Euler

import rmat
from rgeo import RB, V


def foyer(b, seed=4):
    """Pierres, bûches, braises (maillage) — un seul objet."""
    r = random.Random(seed)
    stone = rmat.rock("PierreFoyer", dark=(0.07, 0.065, 0.06), mid=(0.24, 0.22, 0.2), light=(0.45, 0.42, 0.38), crack=0.5, scale=1.2, lichen=0.1, grain=1.3)
    # suie : les pierres sont noircies côté feu (dégradé par la distance, via un second matériau n'est pas nécessaire : teinte sombre globale)
    burnt = rmat.burnt_log()
    endg = rmat.end_grain("BoutDeBuche", rings=14)
    ember = rmat.ember_bed()
    # lit de braises / cendres
    b.rock(V(0, 0, 0.0), (0.58, 0.58, 0.07), ember, seed=3, sub=6, planes=0, amp=0.1, ridge=0.0, detail=0.012, sharp=80)
    # couronne de pierres
    n = 11
    for k in range(n):
        a = 2 * math.pi * k / n + r.uniform(-0.12, 0.12)
        d = 0.66 + r.uniform(-0.04, 0.05)
        s = r.uniform(0.15, 0.22)
        b.rock(V(math.cos(a) * d, math.sin(a) * d, s * 0.38), (s * 1.15, s * 0.95, s * 0.8), stone, seed=20 + k, sub=5, planes=8, depth=(0.7, 0.92), amp=0.14,
               kcut=0.1, detail=0.03, rot=Euler((r.uniform(-.2, .2), r.uniform(-.2, .2), a + r.uniform(-.4, .4))).to_quaternion())
    # bûches en étoile, bouts intérieurs surélevés et noircis
    for k in range(5):
        a = 2 * math.pi * k / 5 + 0.3 + r.uniform(-0.1, 0.1)
        d = V(math.cos(a), math.sin(a), 0)
        Lr = r.uniform(0.85, 1.0)
        rad = r.uniform(0.055, 0.075)
        p_out = d * 0.78 + V(0, 0, rad * 0.9)
        p_in = d * 0.02 + V(0, 0, 0.12 + 0.07 * (k % 2))
        pts = []
        for i in range(9):
            t = i / 8
            pt = p_out.lerp(p_in, t)
            pt.z += 0.03 * math.sin(math.pi * t)
            pt += V(0, 0, 0) + V(-d.y, d.x, 0) * 0.015 * math.sin(t * 6 + k)
            pts.append(pt)
        b.tube(pts, lambda t, rad=rad: rad * (0.92 + 0.1 * math.sin(t * 5)) * (0.9 + 0.1 * t), burnt, sides=14, noise_amp=0.12, noise_f=1.4, seed=k, cap_a=True, cap_b=True,
               cap_mat=endg, cap_disc=True, uv_len=1.0, flute=0.03, flute_n=3)
    # petit bois croisé sur le dessus
    for k in range(4):
        a = r.uniform(0, 6.28)
        d = V(math.cos(a), math.sin(a), 0)
        c = V(r.uniform(-0.06, 0.06), r.uniform(-0.06, 0.06), 0.2 + 0.03 * k)
        pts = [c - d * 0.33, c, c + d * 0.33]
        b.tube(pts, [0.016, 0.018, 0.014], burnt, sides=8, noise_amp=0.1, cap_a=True, cap_b=True, cap_mat=burnt, seed=k + 10)
    return b


def add_effects(scene_coll, with_smoke=True, n_sparks=26, frames=120):
    """Flammes (3 domaines volumétriques), fumée, étincelles animées, lumière vacillante. Retourne la liste des objets."""
    objs = []
    flame = rmat.flame_volume()
    for name, loc, sc, rot in (("flamme-centre", (0.0, 0.0, 0.1), 1.05, 0.0), ("flamme-gauche", (-0.2, 0.1, 0.1), 0.78, 1.1), ("flamme-droite", (0.21, -0.1, 0.1), 0.7, 2.3),
                               ("flamme-fond", (0.05, 0.22, 0.1), 0.6, 4.0), ("flamme-avant", (-0.06, -0.2, 0.1), 0.48, 5.2)):
        me = bpy.data.meshes.new(name)
        w, h = 0.4, 1.05
        vs = [(-w, -w, 0), (w, -w, 0), (w, w, 0), (-w, w, 0), (-w, -w, h), (w, -w, h), (w, w, h), (-w, w, h)]
        me.from_pydata(vs, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        o = bpy.data.objects.new(name, me)
        o.location = loc
        o.scale = (sc, sc, sc)
        o.rotation_euler = (0, 0, rot)
        me.materials.append(flame)
        o.visible_shadow = False
        scene_coll.objects.link(o)
        objs.append(o)
    if with_smoke:
        me = bpy.data.meshes.new("fumee")
        w, h = 0.9, 2.4
        vs = [(-w, -w, 0.1), (w, -w, 0.1), (w, w, 0.1), (-w, w, 0.1), (-w, -w, h), (w, -w, h), (w, w, h), (-w, w, h)]
        me.from_pydata(vs, [], [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)])
        o = bpy.data.objects.new("fumee", me)
        o.location = (0, 0, 0.5)
        me.materials.append(rmat.smoke_volume())
        scene_coll.objects.link(o)
        objs.append(o)
    # lumière du feu
    ld = bpy.data.lights.new("lumiere-feu", "POINT")
    ld.energy = 70
    ld.color = (1.0, 0.52, 0.2)
    ld.shadow_soft_size = 0.18
    lo = bpy.data.objects.new("lumiere-feu", ld)
    lo.location = (0.0, 0.0, 0.42)
    scene_coll.objects.link(lo)
    ld.animation_data_create()
    ld.keyframe_insert("energy", frame=1)
    ld.energy = 70
    ld.keyframe_insert("energy", frame=frames)
    for fc in ld.animation_data.action.layers[0].strips[0].channelbags[0].fcurves:
        mod = fc.modifiers.new("NOISE")
        mod.scale = 5.0
        mod.strength = 24.0
        mod.phase = 3.0
    objs.append(lo)
    # étincelles
    r = random.Random(5)
    sp_mat = rmat.spark()
    for k in range(n_sparks):
        me = bpy.data.meshes.new(f"etincelle{k}")
        import bmesh
        bm = bmesh.new()
        bmesh.ops.create_icosphere(bm, subdivisions=2, radius=r.uniform(0.004, 0.009))
        bm.to_mesh(me)
        bm.free()
        me.materials.append(sp_mat)
        o = bpy.data.objects.new(f"etincelle{k}", me)
        o.visible_shadow = False
        scene_coll.objects.link(o)
        life = r.choice([30, 40, 60, 60, 120])
        phase = r.randrange(0, life)
        a0 = r.uniform(0, 6.28)
        d0 = r.uniform(0.0, 0.12)
        drift = V(r.gauss(0, 0.25), r.gauss(0, 0.25), 0)
        rise = r.uniform(0.9, 1.9)
        wob = r.uniform(0.05, 0.14)
        cycles = frames // life
        for c in range(cycles + 1):
            f0 = 1 + c * life - phase
            for s in (0, 1, 2, 3, 4, 5):
                f = f0 + int(life * s / 5)
                if f < 1 or f > frames + life:
                    continue
                t = s / 5
                pos = V(math.cos(a0) * d0 + drift.x * t + wob * math.sin(t * 9 + a0), math.sin(a0) * d0 + drift.y * t + wob * math.cos(t * 7), 0.25 + rise * t ** 0.85)
                o.location = pos
                sc = 0.0 if s in (0, 5) else (1.0 if s in (1, 2) else 0.6)
                o.scale = (sc, sc, sc)
                o.keyframe_insert("location", frame=f)
                o.keyframe_insert("scale", frame=f)
        objs.append(o)
    return objs
