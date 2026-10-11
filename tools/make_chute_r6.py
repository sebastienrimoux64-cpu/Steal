"""Animation « chute » pour le personnage R6 (style Roblox).

Usage :
    python tools/make_chute_r6.py ENTREE.blend SORTIE.blend

Le fichier d'entrée doit contenir les 6 pièces `Head`, `Torso`, `Left Arm`,
`Right Arm`, `Left Leg`, `Right Leg`. Les rigs d'origine (`Armature`, `__Rig`)
ne sont pas modifiés ; leurs contraintes CHILD_OF sur les pièces sont simplement
mises en sourdine (mute) et remplacées par un squelette d'empties aux bons pivots
(cou, épaules, hanches). Le script ajoute aussi une falaise, un sol, une lumière
et une caméra qui suit le personnage.

Timeline (60 i/s, images 1 à 240) :
    0.0 - 0.7 s   debout au bord de la falaise (respiration)
    0.7 - 1.4 s   déséquilibre : recule, moulinet de bras, bascule en avant
    1.4 - 3.1 s   chute libre (g = 27 u/s²), culbute, bras et jambes qui s'agitent
    3.1 - 4.0 s   impact au sol, rebonds amortis, membres qui retombent
"""
import math
import sys

import bpy
from mathutils import Euler, Vector

FPS = 60
F_START, F_END = 1, 240
G = 27.0                    # gravité en unités/s² (personnage = 5 u de haut)
GROUND_Z = -40.0            # hauteur du sol
EDGE_Y = -0.7               # arête de la falaise
TOE_Y = -0.5                # pointe des pieds (pivot de la bascule)
C0 = Vector((0.0, 0.0, 3.0))  # centre du torse au repos
REL_T = 1.38                # instant où les pieds quittent la falaise
REL_THETA = 35.0            # angle (deg) à ce moment
REL_OMEGA = 110.0           # vitesse angulaire (deg/s) à ce moment
CAM_DIST = 30.0             # distance de la caméra latérale
LAND_THETA = 270.0          # angle à l'impact : sur le dos, tête vers la falaise

PARTS = ["Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg"]
# pivots articulaires (monde, position de repos)
PIVOTS = {
    "Head": Vector((0, 0, 4.0)),
    "Left Arm": Vector((-1.5, 0, 3.6)),
    "Right Arm": Vector((1.5, 0, 3.6)),
    "Left Leg": Vector((-0.5, 0, 1.9)),
    "Right Leg": Vector((0.5, 0, 1.9)),
}
SIDE = {"Left Arm": 1.0, "Right Arm": -1.0, "Left Leg": 1.0, "Right Leg": -1.0}


# ---------------------------------------------------------------- maths utiles
def clamp01(x):
    return max(0.0, min(1.0, x))


def smooth(a, b, x):
    t = clamp01((x - a) / (b - a))
    return t * t * (3 - 2 * t)


def lerp(a, b, w):
    return a + (b - a) * w


def rad(d):
    return math.radians(d)


def rot_x(v, th):
    c, s = math.cos(th), math.sin(th)
    return Vector((v.x, v.y * c - v.z * s, v.y * s + v.z * c))


# ---------------------------------------------------- trajectoire du centre
# angle de bascule avant l'envol : Hermite par morceaux (deg)
WAY = [(0.0, 0.0), (0.55, 0.0), (0.85, -10.0), (1.12, -2.0), (REL_T, REL_THETA)]


def _tangents():
    tg = []
    for i, (t, _) in enumerate(WAY):
        if i == 0:
            tg.append(0.0)
        elif i == len(WAY) - 1:
            tg.append(REL_OMEGA)
        else:
            tg.append((WAY[i + 1][1] - WAY[i - 1][1]) / (WAY[i + 1][0] - WAY[i - 1][0]))
    return tg


TANG = _tangents()


def theta_ground(t):
    """Angle (deg) pendant que les pieds sont encore sur la falaise."""
    t = min(t, REL_T)
    for i in range(len(WAY) - 1):
        t0, p0 = WAY[i]
        t1, p1 = WAY[i + 1]
        if t <= t1:
            h = t1 - t0
            u = (t - t0) / h
            h00 = 2 * u**3 - 3 * u**2 + 1
            h10 = u**3 - 2 * u**2 + u
            h01 = -2 * u**3 + 3 * u**2
            h11 = u**3 - u**2
            return h00 * p0 + h10 * h * TANG[i] + h01 * p1 + h11 * h * TANG[i + 1]
    return REL_THETA


def com_ground(t):
    th = rad(theta_ground(t) + 1.2 * math.sin(2 * math.pi * 0.9 * t) * (1 - smooth(0.5, 0.8, t)))
    # pivot : pointe des pieds quand il penche en avant, talons quand il penche en arrière
    pivot_y = TOE_Y * max(-1.0, min(1.0, math.degrees(th) / 4.0))
    pv = Vector((0, pivot_y, 0))
    return pv + rot_x(C0 - pv, th), th


def _release_state():
    p, th = com_ground(REL_T)
    eps = 1e-4
    p2, _ = com_ground(REL_T - eps)
    v = (p - p2) / eps
    return p, v


P_REL, V_REL = _release_state()
# durée de la chute libre : le centre arrive à GROUND_Z + 0.5 (corps à plat)
_a, _b, _c = -0.5 * G, V_REL.z, P_REL.z - (GROUND_Z + 0.5)
FALL_T = (-_b - math.sqrt(_b * _b - 4 * _a * _c)) / (2 * _a)
T_IMPACT = REL_T + FALL_T
ALPHA = 2 * (LAND_THETA - REL_THETA - REL_OMEGA * FALL_T) / FALL_T**2   # deg/s²


def body_state(t):
    """Position du centre du corps et angle (rad) autour de X au temps t (s)."""
    if t <= REL_T:
        return com_ground(t)
    tau = min(t, T_IMPACT) - REL_T
    pos = P_REL + V_REL * tau + Vector((0, 0, -0.5 * G * tau * tau))
    th = REL_THETA + REL_OMEGA * tau + 0.5 * ALPHA * tau * tau
    if t > T_IMPACT:
        s = t - T_IMPACT
        # rebonds amortis + petite oscillation de roulis sur le dos
        bounce = 1.9 * abs(math.sin(math.pi * s / 0.34)) * math.exp(-4.5 * s)
        pos = Vector((pos.x, pos.y + 0.9 * (1 - math.exp(-6 * s)), GROUND_Z + 0.5 + bounce))
        th = LAND_THETA + 9.0 * math.exp(-6 * s) * math.sin(2 * math.pi * 2.6 * s)
    return pos, rad(th)


# ------------------------------------------------------------ poses des membres
def limb_pose(name, t):
    sg = SIDE.get(name, 1.0)
    ph = 0.0 if sg > 0 else 1.9
    w_bal = smooth(0.55, 0.85, t)
    w_fall = smooth(REL_T - 0.05, REL_T + 0.22, t)
    w_land = smooth(T_IMPACT - 0.03, T_IMPACT + 0.16, t)
    s = max(0.0, t - T_IMPACT)

    if name == "Head":
        idle = (0.0, 0.0, 0.0)
        bal = (rad(8) * math.sin(2 * math.pi * 1.8 * t), 0.0, rad(6) * math.sin(2 * math.pi * 1.8 * t + 1))
        fall = (rad(20) * math.sin(2 * math.pi * 1.3 * t + 1.0), 0.0, rad(10) * math.sin(2 * math.pi * 1.7 * t))
        land = (rad(-14) * math.exp(-5 * s) * math.sin(2 * math.pi * 3 * s), 0.0, rad(14))
    elif "Arm" in name:
        idle = (rad(3) * math.sin(2 * math.pi * 0.7 * t + ph), sg * rad(3), 0.0)
        a = math.sin(2 * math.pi * 2.0 * (t - 0.5) + ph)
        spread_b = 40 + 15 * math.sin(2 * math.pi * 2.0 * t + ph + 1.0)
        bal = (-rad(15) - rad(50) * a, sg * rad(spread_b), -sg * rad(spread_b) * 0.35)
        sw = math.sin(2 * math.pi * 2.2 * t + ph)
        spread_f = 35 + 25 * math.sin(2 * math.pi * 2.2 * t + ph + 1.5)
        fall = (-rad(115 + 55 * sw), sg * rad(spread_f), -sg * rad(spread_f) * 0.6)
        land = (-rad(25) + rad(12) * math.exp(-5 * s) * math.sin(2 * math.pi * 3 * s + ph),
                sg * rad(65), 0.0)
    else:  # jambes
        idle = (0.0, 0.0, 0.0)
        bal = (rad(6) * sg * math.sin(2 * math.pi * 1.8 * t), sg * rad(3), 0.0)
        kick = rad(38) * math.sin(2 * math.pi * 1.7 * t) * sg
        fall = (kick, sg * rad(10), 0.0)
        land = (rad(14) * sg + rad(8) * math.exp(-5 * s) * math.sin(2 * math.pi * 3 * s), sg * rad(13), 0.0)

    out = []
    for i in range(3):
        v = lerp(idle[i], bal[i], w_bal)
        v = lerp(v, fall[i], w_fall)
        v = lerp(v, land[i], w_land)
        out.append(v)
    return tuple(out)


# ----------------------------------------------------------------- construction
def new_empty(name, loc, parent=None, size=0.4):
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = size
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    if parent is not None:
        bpy.context.view_layer.update()
        e.parent = parent
        e.matrix_parent_inverse = parent.matrix_world.inverted()
    return e


def make_material(name, color, rough=0.8):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = rough
    return m


def textured(name, c1, c2, kind):
    """Matériau avec un motif procédural (briques pour la falaise, damier pour le sol)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.9
    coord = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "brick":
        tex = nt.nodes.new("ShaderNodeTexBrick")
        tex.inputs["Color1"].default_value = (*c1, 1)
        tex.inputs["Color2"].default_value = (*c2, 1)
        tex.inputs["Mortar"].default_value = (0.08, 0.07, 0.06, 1)
        tex.inputs["Scale"].default_value = 0.35
        tex.inputs["Mortar Size"].default_value = 0.02
        tex.inputs["Brick Width"].default_value = 1.6
        tex.inputs["Row Height"].default_value = 0.5
        out = tex.outputs["Color"]
    else:
        tex = nt.nodes.new("ShaderNodeTexChecker")
        tex.inputs["Color1"].default_value = (*c1, 1)
        tex.inputs["Color2"].default_value = (*c2, 1)
        tex.inputs["Scale"].default_value = 0.12
        out = tex.outputs["Color"]
    if kind == "brick":
        # la face visible de la falaise est dans le plan YZ : on y plaque le motif
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        com = nt.nodes.new("ShaderNodeCombineXYZ")
        nt.links.new(coord.outputs["Object"], sep.inputs["Vector"])
        nt.links.new(sep.outputs["Y"], com.inputs["X"])
        nt.links.new(sep.outputs["Z"], com.inputs["Y"])
        nt.links.new(sep.outputs["X"], com.inputs["Z"])
        nt.links.new(com.outputs["Vector"], tex.inputs["Vector"])
    else:
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
    nt.links.new(out, bsdf.inputs["Base Color"])
    return m


def add_box(name, lo, hi, mat):
    verts = [(x, y, z) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_scene():
    sc = bpy.context.scene
    # 1) squelette d'empties : le corps entier + une articulation par membre
    root = new_empty("Chute_Root", tuple(C0), size=0.8)
    pivots = {}
    for part, p in PIVOTS.items():
        pivots[part] = new_empty(f"Chute_{part.replace(' ', '')}_Pivot", tuple(p), root)
        pivots[part].rotation_mode = "XYZ"
    root.rotation_mode = "XYZ"
    bpy.context.view_layer.update()
    for part in PARTS:
        ob = bpy.data.objects[part]
        for c in ob.constraints:
            if c.type == "CHILD_OF":
                c.mute = True
        parent = pivots.get(part, root)
        ob.parent = parent
        ob.matrix_parent_inverse = parent.matrix_world.inverted()

    # 2) décor : falaise, sol, lumière
    cliff_mat = textured("Falaise", (0.42, 0.30, 0.20), (0.34, 0.24, 0.16), "brick")
    ground_mat = textured("Sol", (0.30, 0.45, 0.22), (0.26, 0.40, 0.19), "checker")
    add_box("Falaise", (-18, EDGE_Y, GROUND_Z), (18, 60, 0), cliff_mat)
    add_box("Sol", (-300, -300, GROUND_Z - 1), (300, 300, GROUND_Z), ground_mat)

    sun_data = bpy.data.lights.new("Soleil", "SUN")
    sun_data.energy = 3.5
    sun = bpy.data.objects.new("Soleil", sun_data)
    sun.rotation_euler = (rad(50), rad(15), rad(40))
    sc.collection.objects.link(sun)

    world = sc.world or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.45, 0.62, 0.85, 1)
    bg.inputs["Strength"].default_value = 0.9

    # 3) caméra de côté (vue depuis +X), qui suit le personnage en glissant
    cam_data = bpy.data.cameras.new("Camera_Chute")
    cam_data.lens = 35
    cam = bpy.data.objects.new("Camera_Chute", cam_data)
    cam.rotation_euler = (rad(90), 0, rad(90))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return root, pivots, cam


def animate(root, pivots, cam):
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = F_START, F_END
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"

    # les rigs d'origine ne servent plus : on les cache pour ne pas gêner la vue
    for n in ("Armature", "__Rig", "__RigMeta"):
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_viewport = True
            bpy.data.objects[n].hide_render = True

    cam_z = 2.5
    cam_y = -2.0
    for f in range(F_START, F_END + 1):
        t = (f - F_START) / FPS
        pos, th = body_state(t)
        root.location = pos
        root.rotation_euler = Euler((th, 0, 0), "XYZ")
        root.keyframe_insert("location", frame=f)
        root.keyframe_insert("rotation_euler", frame=f)
        for part, piv in pivots.items():
            piv.rotation_euler = Euler(limb_pose(part, t), "XYZ")
            piv.keyframe_insert("rotation_euler", frame=f)

        # caméra : suivi amorti en hauteur, ne descend pas sous le sol visible
        target_z = max(pos.z + 1.0, GROUND_Z + 5.5)
        kz = 1 - math.exp(-1 / FPS / 0.10)   # suivi vertical serré (la chute va vite)
        ky = 1 - math.exp(-1 / FPS / 0.25)
        cam_z += (target_z - cam_z) * kz
        cam_y += ((pos.y * 0.8 - 2.0) - cam_y) * ky
        shake = 0.0
        if t > T_IMPACT:
            s = t - T_IMPACT
            shake = 0.7 * math.exp(-9 * s) * math.sin(2 * math.pi * 11 * s)
        cam.location = (CAM_DIST, cam_y, cam_z + shake)
        cam.keyframe_insert("location", frame=f)


def main():
    src, dst = sys.argv[-2], sys.argv[-1]
    bpy.ops.wm.open_mainfile(filepath=src)
    root, pivots, cam = build_scene()
    animate(root, pivots, cam)
    bpy.context.scene.frame_set(F_START)
    bpy.ops.wm.save_as_mainfile(filepath=dst)
    print(f"OK: {dst}  (impact à t={T_IMPACT:.2f}s, image {F_START + round(T_IMPACT * FPS)})")


if __name__ == "__main__":
    main()
