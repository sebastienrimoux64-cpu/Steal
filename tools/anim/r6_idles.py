"""
Animations "idle" R6 par personnage, pour le rig R6IKFIX (armature de contrôle `Armature` + `__Rig`).

Les parties du corps restent entières (R6 : pas de coude ni de genou) : on ne fait que bouger les os de
contrôle. Chaque personnage a sa personnalité (posture, rythme, tics) décrite dans une fonction `pose(t)`.

    python tools/anim/r6_idles.py <rig.blend> <dossier_sortie> [Tanjiro Nezuko ...]

Génère <dossier_sortie>/Idle_<Nom>.blend : le rig d'origine, inchangé, avec l'action `Idle_<Nom>` sur `Armature`.

Repère (monde) : le personnage regarde vers +Y, le haut est +Z, sa droite est +X.
  rx : tangage      (+ = bras vers l'avant / tête vers le haut ; - = penché en avant / tête baissée)
  ry : roulis       (+ = tête inclinée vers sa droite ; un bras qui pend part vers sa gauche)
  rz : lacet        (+ = tourne vers sa gauche)
Les os de tête et de bras sont pilotés en rotations "monde" converties dans le repère de chaque os.
"""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

FPS = 60


# ----------------------------------------------------------------------------
# Outils d'animation (courbes douces, boucles)
# ----------------------------------------------------------------------------
def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def bump(t, a, b, c, d):
    """0 avant a, monte jusqu'à 1 en b, tient jusqu'en c, redescend à 0 en d (courbes douces)."""
    if t <= a or t >= d:
        return 0.0
    if t < b:
        return ease((t - a) / (b - a))
    if t <= c:
        return 1.0
    return 1.0 - ease((t - c) / (d - c))


def S(t, T, k, phase=0.0):
    """sinus qui fait k cycles complets sur la boucle de durée T (boucle parfaite)."""
    return math.sin(2 * math.pi * (k * t / T + phase))


def sq(t, T, k, sharp=3.0, phase=0.0):
    """quasi-créneau lissé : bascule franchement entre -1 et +1, k fois par boucle."""
    return math.tanh(sharp * S(t, T, k, phase))


def arm(side, fwd=0.0, abd=0.0, twist=0.0):
    """Rotation d'un bras. side=+1 droit / -1 gauche. fwd : lever vers l'avant (°). abd : écarté du corps (°, <0 = vers le corps)."""
    return (fwd, -side * abd, twist)


# ----------------------------------------------------------------------------
# Personnages : pose(t) -> {os: {"rot": (rx, ry, rz) en °, "loc": (x, y, z) en unités}}
# ----------------------------------------------------------------------------
def tanjiro(t):
    """Modeste : posture droite et douce, mains jointes devant, tête légèrement baissée,
    petite révérence polie et regard attentif sur le côté."""
    T = 6.0
    br = S(t, T, 2)                       # respiration lente (3 s)
    sway = S(t, T, 1)
    bow = bump(t, 1.5, 2.4, 2.8, 3.8)     # petite révérence polie
    glance = bump(t, 4.3, 4.8, 5.1, 5.7)  # regard attentif vers la gauche
    d = {}
    d["Torso"] = dict(rot=(-(1.5 + 10 * bow) + 0.5 * br, 0, 2.0 * sway - 3 * glance), loc=(0.07 * sway, 0, 0.02 * br - 0.03 * bow))
    d["Head"] = dict(rot=(-(6 + 13 * bow) + 0.8 * br, 3 + 2 * S(t, T, 1, 0.25) - 2 * glance, 16 * glance - 2.5 * sway))
    for s, name in ((1, "RightUpperArm"), (-1, "LeftUpperArm")):
        d[name] = dict(rot=arm(s, fwd=20 + 2.5 * br + 7 * bow + 1.5 * s * sway, abd=-15 - 1.0 * br))
    d["LeftLeg-IKTarget"] = dict(loc=(0.07, 0, 0.0))
    d["RightLeg-IKTarget"] = dict(loc=(-0.07, 0, 0.0))
    return d


def nezuko(t):
    """Timide : épaules rentrées, mains serrées contre la poitrine, tête baissée et penchée, genoux qui se touchent,
    petits regards furtifs puis elle détourne les yeux, un pied qui se frotte."""
    T = 4.0
    br = S(t, T, 3)                         # respiration rapide et superficielle
    sw = S(t, T, 1)
    peek = bump(t, 0.7, 1.1, 1.6, 2.0)      # relève la tête et jette un coup d'œil
    avert = bump(t, 2.0, 2.35, 3.0, 3.5)    # détourne vite le regard, se recroqueville
    d = {}
    d["Torso"] = dict(rot=(-(7 - 2 * peek + 3 * avert) + 0.6 * br, 0, 2 * sw - 7 * avert + 3 * peek),
                      loc=(0.05 * sw, 0, -0.05 + 0.015 * br))
    d["Head"] = dict(rot=(-(21 - 14 * peek + 7 * avert) + 0.8 * br, 10 - 5 * peek + 3 * avert + 2 * sw,
                          17 * peek - 22 * avert))
    for s, name in ((1, "RightUpperArm"), (-1, "LeftUpperArm")):
        fidget = 4 * S(t, T, 2) * s
        d[name] = dict(rot=arm(s, fwd=48 + fidget + 5 * avert + 1.5 * br, abd=-34 - 8 * avert - 3 * peek))
    rub = S(t, T, 2)
    d["LeftLeg-IKTarget"] = dict(loc=(0.2, 0.09 * rub, 0.05 * max(0.0, rub)))
    d["RightLeg-IKTarget"] = dict(loc=(-0.2, 0, 0))
    return d


def inosuke(t):
    """Excité, sauvage : rebond permanent, torse penché en avant façon bête, tête qui claque d'un côté à l'autre,
    bras écartés comme des griffes, coups de poing dans le vide et piétinements."""
    T = 2.0
    bounce = S(t, T, 4)
    d = {}
    d["Torso"] = dict(rot=(-15 + 3 * bounce, 0, 7 * S(t, T, 2)), loc=(0.05 * S(t, T, 1), 0, -0.1 + 0.09 * bounce))
    d["Head"] = dict(rot=(3 + 3 * bounce, 7 * S(t, T, 2, 0.25), 36 * sq(t, T, 1, 3.0)))
    pr = bump(t, 0.18, 0.30, 0.38, 0.55)        # coup de poing droit
    pl = bump(t, 1.18, 1.30, 1.38, 1.55)        # coup de poing gauche
    for s, name, p in ((1, "RightUpperArm", pr), (-1, "LeftUpperArm", pl)):
        base_f = 22 + 9 * bounce * s
        base_a = 38 + 6 * bounce
        d[name] = dict(rot=arm(s, fwd=base_f * (1 - p) + 85 * p, abd=base_a * (1 - p) + 4 * p, twist=0))
    st_l = bump(t, 0.50, 0.58, 0.64, 0.78)
    st_r = bump(t, 1.50, 1.58, 1.64, 1.78)
    d["LeftLeg-IKTarget"] = dict(loc=(-0.22, 0.05, 0.22 * st_l))
    d["RightLeg-IKTarget"] = dict(loc=(0.22, 0.05, 0.22 * st_r))
    return d


def muzan(t):
    """Froid, arrogant, maître de lui : presque immobile, menton levé, épaules en arrière, une main devant à la taille,
    respiration très lente, regard qui balaie la pièce, puis une inclinaison de tête menaçante."""
    T = 8.0
    br = S(t, T, 2)
    menace = bump(t, 4.6, 5.6, 6.4, 7.5)
    flick = bump(t, 2.5, 2.8, 3.0, 3.5)
    d = {}
    d["Torso"] = dict(rot=(2 + 0.4 * br, 0, -6 * menace + 1.5 * S(t, T, 1)), loc=(0.06 + 0.03 * S(t, T, 1), 0, 0.012 * br))
    d["Head"] = dict(rot=(11 + 0.5 * br - 5 * menace, 3 + 17 * menace, 11 * S(t, T, 1) - 20 * menace))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=34 + 1.3 * S(t, T, 3) + 8 * flick, abd=-17))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-5 + 0.8 * br, abd=7 + 0.8 * br))
    d["LeftLeg-IKTarget"] = dict(loc=(-0.1, 0.1, 0))
    d["RightLeg-IKTarget"] = dict(loc=(0.1, 0, 0))
    return d


def gon(t):
    """Joyeux, énergique, curieux : petits rebonds sur la pointe des pieds, bras qui se balancent, tête qui regarde partout,
    poing levé de joie."""
    T = 4.0
    bounce = S(t, T, 4)
    swing = S(t, T, 2)
    cheer = bump(t, 2.3, 2.5, 2.7, 3.0)
    d = {}
    d["Torso"] = dict(rot=(-3 - 3 * cheer + 1.2 * bounce, 0, 3 * S(t, T, 1)), loc=(0.04 * S(t, T, 1), 0, 0.05 * abs(bounce) - 0.03 * cheer))
    d["Head"] = dict(rot=(5 + 3 * bounce + 8 * cheer, 5 * S(t, T, 2, 0.25), 20 * S(t, T, 1) + 5 * S(t, T, 3)))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=(10 + 14 * swing) * (1 - cheer) + 115 * cheer, abd=8 + 2 * bounce + 4 * cheer))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=10 - 14 * swing, abd=8 + 2 * bounce))
    d["LeftLeg-IKTarget"] = dict(loc=(-0.12, 0.04, 0.05 * max(0.0, bounce)))
    d["RightLeg-IKTarget"] = dict(loc=(0.12, 0.04, 0.05 * max(0.0, -bounce)))
    return d


def killua(t):
    """Cool et nonchalant, un peu blasé : mains dans les poches, affalé sur une jambe, pied qui tape, tête penchée,
    regard félin soudain puis étirement de nuque."""
    T = 6.0
    br = S(t, T, 2)
    glance = bump(t, 3.2, 3.35, 3.6, 3.85)
    stretch = bump(t, 4.4, 5.0, 5.2, 5.8)
    tap = bump(t, 0.6, 0.8, 2.0, 2.3) * max(0.0, S(t, T, 5))
    d = {}
    d["Torso"] = dict(rot=(-5 + 0.5 * br - 2 * stretch, 0, 4 * S(t, T, 1) + 5 * glance), loc=(0.12 + 0.03 * S(t, T, 1), 0, 0.012 * br))
    d["Head"] = dict(rot=(-3 + 6 * glance + 12 * stretch, 10 - 3 * glance - 24 * stretch, 4 * S(t, T, 1) + 30 * glance))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=-10 + 0.8 * br, abd=-5))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-10 + 0.8 * br, abd=-5))
    d["LeftLeg-IKTarget"] = dict(loc=(0.05, 0.14, 0.12 * tap))
    d["RightLeg-IKTarget"] = dict(loc=(0.1, -0.03, 0))
    return d


def kurapika(t):
    """Sérieux, maître de lui, toujours en alerte : très droit, bras collés, poing droit légèrement avancé,
    balayage lent du regard, puis un éclair de tension (colère contenue)."""
    T = 6.0
    br = S(t, T, 2)
    tense = bump(t, 3.6, 3.9, 4.4, 5.0)
    d = {}
    d["Torso"] = dict(rot=(1 + 0.5 * br - 2 * tense, 0, 2 * S(t, T, 1)), loc=(0, 0, 0.012 * br))
    d["Head"] = dict(rot=(2 + 0.4 * br - 13 * tense, 1.5, 21 * S(t, T, 1) * (1 - tense) - 5 * tense))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=9 + 0.8 * br + 8 * tense, abd=2 - 6 * tense))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-2 + 0.8 * br + 5 * tense, abd=4 - 6 * tense))
    d["LeftLeg-IKTarget"] = dict(loc=(0.12, 0, 0))
    d["RightLeg-IKTarget"] = dict(loc=(-0.12, 0, 0))
    return d


def leorio(t):
    """Adulte fier, un peu fanfaron et soupe au lait : poings sur les hanches, torse bombé, menton levé, gros éclat de rire
    qui secoue les épaules, puis il rajuste ses lunettes d'un air important."""
    T = 5.0
    laugh = bump(t, 1.0, 1.2, 2.3, 2.6)
    glasses = bump(t, 3.2, 3.6, 4.0, 4.4)
    d = {}
    shake = math.sin(2 * math.pi * 7 * t) * laugh
    d["Torso"] = dict(rot=(3 - 4 * laugh + 1.0 * shake, 0, 4 * S(t, T, 1) + 2.5 * shake), loc=(0.10 * S(t, T, 1), 0, 0.03 * shake + 0.01 * S(t, T, 2)))
    d["Head"] = dict(rot=(8 + 10 * laugh - 10 * glasses, 3 * S(t, T, 1), -4 * S(t, T, 1) + 6 * glasses))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=-12 * (1 - glasses) + 120 * glasses + 3 * shake, abd=38 * (1 - glasses) - 24 * glasses))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-12 + 3 * shake, abd=38 + 1.5 * shake))
    d["LeftLeg-IKTarget"] = dict(loc=(-0.15, 0, 0))
    d["RightLeg-IKTarget"] = dict(loc=(0.15, 0, 0))
    return d


def meruem(t):
    """Roi souverain, puissance écrasante et curiosité d'intellectuel : debout, torse bombé, respiration lente et profonde,
    léger tremblement de puissance, regard qui domine la pièce, pose pensive (main au menton), puis tête qui s'incline."""
    T = 10.0
    br = S(t, T, 2)
    think = bump(t, 2.8, 4.0, 6.0, 7.0)
    menace = bump(t, 7.6, 8.4, 9.0, 9.7)
    aura = S(t, T, 60)                          # tremblement de puissance, très discret (6 Hz)
    d = {}
    d["Torso"] = dict(rot=(3 + 1.1 * br - 2 * think + 0.2 * aura, 0, 3 * S(t, T, 1) + 6 * menace),
                      loc=(0.04 * S(t, T, 1), 0, 0.03 * br + 0.006 * aura))
    d["Head"] = dict(rot=(9 + 0.6 * br - 8 * think - 4 * menace, 12 * think - 11 * menace, 18 * S(t, T, 1) * (1 - think) + 10 * think - 10 * menace))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=-2 + 128 * think + 0.4 * aura, abd=14 * (1 - think) - 30 * think))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-2 + 0.5 * br + 0.4 * aura, abd=15 + 1.0 * br))
    d["LeftLeg-IKTarget"] = dict(loc=(-0.12, 0, 0))
    d["RightLeg-IKTarget"] = dict(loc=(0.12, 0, 0))
    return d


def hisoka(t):
    """Joueur, dérangeant, séducteur et menaçant : balancement de hanches nonchalant, main à la hanche, carte en main
    près du menton qu'il claque d'un geste vif, tête penchée, petit rire qui secoue le torse."""
    T = 6.0
    sway = S(t, T, 1)
    flick = bump(t, 1.8, 1.9, 2.0, 2.3)
    giggle = bump(t, 2.8, 2.95, 3.6, 3.95)
    shake = math.sin(2 * math.pi * 9 * t) * giggle
    d = {}
    d["Torso"] = dict(rot=(-4 + 4 * S(t, T, 2) - 2 * giggle + 1.0 * shake, 6 * sway, 9 * S(t, T, 1, 0.25) + 2.5 * shake), loc=(0.18 * sway, 0, 0.02 * shake))
    d["Head"] = dict(rot=(-2 + 6 * giggle, 14 + 6 * sway + 4 * giggle, 12 * S(t, T, 1, 0.5) - 6 * flick))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=(62 + 2 * S(t, T, 6)) * (1 - flick) + 108 * flick, abd=-28 * (1 - flick) - 6 * flick))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=-10 + 1.5 * shake, abd=30 + 2 * sway))
    d["LeftLeg-IKTarget"] = dict(loc=(0.16, 0.2, 0))
    d["RightLeg-IKTarget"] = dict(loc=(0.0, 0, 0))
    return d


# Registre : nom -> (fonction de pose, durée de boucle en s, pas entre clés en images, description)
CHARACTERS = {
    "Tanjiro": (tanjiro, 6.0, 6, "modeste, doux et poli"),
    "Nezuko": (nezuko, 4.0, 4, "timide"),
    "Inosuke": (inosuke, 2.0, 3, "excité et sauvage"),
    "Muzan": (muzan, 8.0, 8, "froid, arrogant, sûr de lui"),
    "Gon": (gon, 4.0, 3, "joyeux, énergique, curieux"),
    "Killua": (killua, 6.0, 5, "cool, nonchalant, félin"),
    "Kurapika": (kurapika, 6.0, 6, "sérieux, maître de lui, en alerte"),
    "Leorio": (leorio, 5.0, 2, "fier, fanfaron, soupe au lait"),
    "Meruem": (meruem, 10.0, 3, "roi souverain, puissant et curieux"),
    "Hisoka": (hisoka, 6.0, 2, "joueur, dérangeant, séducteur"),
}


# ----------------------------------------------------------------------------
# Application au rig
# ----------------------------------------------------------------------------
def rest_rot(arm_obj, pb):
    return arm_obj.matrix_world.to_3x3() @ pb.bone.matrix_local.to_3x3()


def clear_pose(arm_obj):
    for pb in arm_obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def pose_values(arm_obj, pose):
    """Calcule (sans toucher à la pose) les valeurs d'os : {os: {"q": (w,x,y,z), "loc": (x,y,z)}}.
    Rotations monde -> repère de chaque os."""
    out = {}
    for name, ch in pose.items():
        pb = arm_obj.pose.bones[name]
        rr = rest_rot(arm_obj, pb)
        v = {"q": (1.0, 0.0, 0.0, 0.0), "loc": (0.0, 0.0, 0.0)}
        if "rot" in ch:
            rx, ry, rz = (math.radians(a) for a in ch["rot"])
            R = Euler((0, 0, rz)).to_matrix() @ Euler((0, ry, 0)).to_matrix() @ Euler((rx, 0, 0)).to_matrix()
            v["q"] = tuple((rr.inverted() @ R @ rr).to_quaternion())
        if "loc" in ch:
            v["loc"] = tuple(rr.inverted() @ Vector(ch["loc"]))
        out[name] = v
    return out


def channelbag_of(act):
    return act.layers[0].strips[0].channelbags[0]


def build(rig_path, out_dir, name):
    fn, T, step, desc = CHARACTERS[name]
    bpy.ops.wm.open_mainfile(filepath=rig_path)
    arm = bpy.data.objects["Armature"]
    n_frames = int(round(T * FPS))
    base = bpy.data.actions.get("ArmatureAction")
    act = base.copy()
    act.name = f"Idle_{name}"
    arm.animation_data_create()
    arm.animation_data.action = act
    if hasattr(arm.animation_data, "action_slot") and act.slots:
        try:
            arm.animation_data.action_slot = act.slots[0]
        except Exception:
            pass
    first, last = fn(0.0), fn(T)
    for b in first:                                      # contrôle de boucle : la dernière pose doit égaler la première
        for k in first[b]:
            for a, c in zip(first[b][k], last[b][k]):
                assert abs(a - c) < 1e-6, f"{name}: la boucle ne ferme pas ({b} {k})"
    frames = list(range(0, n_frames, step)) + [n_frames]
    cb = channelbag_of(act)
    animated = list(first.keys())
    series = {b: {"q": [], "loc": []} for b in animated}
    prev = {b: None for b in animated}
    for f in frames:
        vals = pose_values(arm, fn(f / FPS))
        for b in animated:
            q = vals[b]["q"]
            if prev[b] is not None and sum(x * y for x, y in zip(q, prev[b])) < 0:   # continuité du quaternion (chemin le plus court)
                q = tuple(-x for x in q)
            prev[b] = q
            series[b]["q"].append(q)
            series[b]["loc"].append(vals[b]["loc"])
    for b in animated:
        for prop, size in (("rotation_quaternion", 4), ("location", 3)):
            key = "q" if prop == "rotation_quaternion" else "loc"
            for i in range(size):
                fc = cb.fcurves.find(f'pose.bones["{b}"].{prop}', index=i)
                assert fc is not None, (b, prop, i)
                fc.keyframe_points.clear()
                for f, v in zip(frames, series[b][key]):
                    kp = fc.keyframe_points.insert(f, v[i], options={"FAST"})
                    kp.interpolation = "BEZIER"
                fc.update()
    clear_pose(arm)
    scn = bpy.context.scene
    scn.render.fps = FPS
    scn.frame_start, scn.frame_end = 0, n_frames
    try:
        act.use_frame_range = True
        act.frame_start, act.frame_end = 0, n_frames
        act.use_cyclic = True
    except Exception:
        pass
    if base.users == 0:
        bpy.data.actions.remove(base)
    scn.frame_set(0)
    arm.animation_data.action = act
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"Idle_{name}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path)
    print(f"Idle_{name}: {n_frames} images @ {FPS} fps ({T:.0f} s), {len(frames)} clés par os animé - {desc}")
    return path


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    rig = next(a for a in args if a.endswith(".blend"))
    rest = [a for a in args if a != rig]
    out = rest[0]
    names = [a for a in rest[1:] if a in CHARACTERS] or list(CHARACTERS)
    for n in names:
        build(rig, out, n)
