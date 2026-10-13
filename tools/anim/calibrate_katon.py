"""Calcule, avec la vraie géométrie du rig, l'angle de balayage horizontal des bras vers le centre qui amène les DEUX MAINS AU CONTACT
au centre de la poitrine pour chaque sceau du Katon.

    python tools/anim/calibrate_katon.py tools/anim/source/R6IKFIX.blend

Affiche le dictionnaire SEAL_SWING à recopier dans r6_jutsu.py, puis vérifie : écart des mains = HAND_SEPARATION.
Méthode : pour chaque sceau, on pose torse + bras (à la date de maintien), on mesure le bout de chaque bras (centre des sommets les plus
éloignés de l'épaule) exprimé dans le repère du torse, et on cherche (dichotomie) l'angle qui place ce bout à +/- HAND_SEPARATION/2
de l'axe de la poitrine. Les deux mains sont donc jointes même quand le buste se tord."""
import math
import os
import sys

import bpy
from mathutils import Euler, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r6_jutsu as J
from r6_idles import arm, pose_values, clear_pose, track

bpy.ops.wm.open_mainfile(filepath=sys.argv[-1])
A = bpy.data.objects["Armature"]
A.animation_data.action = None
dg_get = bpy.context.evaluated_depsgraph_get


def tip_local(side_name, mesh_name, t, inward_deg, fwd):
    """Bout du bras, exprimé dans le repère du torse (x = vers la droite du personnage, le long de la poitrine)."""
    clear_pose(A)
    d = J.katon(t)
    side = 1 if side_name.startswith("Right") else -1
    d[side_name]["rot"] = arm(side, fwd=fwd, abd=0, twist=side * inward_deg)   # balayage horizontal vers le centre
    vals = pose_values(A, d)
    for bn, v in vals.items():
        pb = A.pose.bones[bn]
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = v["q"]
        pb.location = v["loc"]
    bpy.context.view_layer.update()
    dg = dg_get()
    o = bpy.data.objects[mesh_name].evaluated_get(dg)
    pivot = A.matrix_world @ A.pose.bones[side_name].head
    verts = [o.matrix_world @ v.co for v in o.data.vertices]
    centroid = sum(verts, Vector()) / len(verts)
    axis = (centroid - pivot).normalized()                       # axe du bras, de l'épaule vers le bout
    proj = [(v - pivot).dot(axis) for v in verts]
    top = max(proj)
    end = [v for v, pr in zip(verts, proj) if pr > top - 0.15]   # sommets de la face du bout
    tip = sum(end, Vector()) / len(end)
    # repère du torse : droite = +X tourné par le tangage et le lacet du torse
    pitch = math.radians(track(t, J.PITCH))
    yaw = math.radians(track(t, J.YAW))
    R = Euler((0, 0, yaw)).to_matrix() @ Euler((pitch, 0, 0)).to_matrix()
    right = R @ Vector((1, 0, 0))
    centre = A.matrix_world @ A.pose.bones["Torso"].head
    return (tip - centre).dot(right), tip


result = {}
for name, t0, t1, fwd in J.SEALS:
    t = (t0 + t1) / 2 if t1 - t0 < 0.3 else t0 + 0.08      # date représentative du maintien
    out = {}
    for side_name, mesh in (("RightUpperArm", "Right Arm"), ("LeftUpperArm", "Left Arm")):
        want = +J.HAND_SEPARATION / 2 if side_name.startswith("Right") else -J.HAND_SEPARATION / 2
        lo, hi = 0.0, 80.0
        for _ in range(26):
            mid = (lo + hi) / 2
            x, _tip = tip_local(side_name, mesh, t, mid, fwd)
            if abs(x) > abs(want):       # le bout est encore trop loin du centre -> plus de rapprochement
                lo = mid
            else:
                hi = mid
        out[side_name] = (lo + hi) / 2
    result[name] = out
    xr, tr = tip_local("RightUpperArm", "Right Arm", t, out["RightUpperArm"], fwd)
    xl, tl = tip_local("LeftUpperArm", "Left Arm", t, out["LeftUpperArm"], fwd)
    clear_pose(A)
    dd = J.katon(t)
    dd["RightUpperArm"]["rot"] = arm(1, fwd=fwd, abd=0, twist=out["RightUpperArm"])
    dd["LeftUpperArm"]["rot"] = arm(-1, fwd=fwd, abd=0, twist=-out["LeftUpperArm"])
    for bn, v in pose_values(A, dd).items():
        pb = A.pose.bones[bn]; pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = v["q"]; pb.location = v["loc"]
    bpy.context.view_layer.update()
    dgx = dg_get()
    VR = [(bpy.data.objects["Right Arm"].evaluated_get(dgx).matrix_world @ v.co) for v in bpy.data.objects["Right Arm"].evaluated_get(dgx).data.vertices]
    VL = [(bpy.data.objects["Left Arm"].evaluated_get(dgx).matrix_world @ v.co) for v in bpy.data.objects["Left Arm"].evaluated_get(dgx).data.vertices]
    gap = min((a - b).length for a in VR for b in VL)
    print(f"{name:9s} t={t:.2f}s fwd={fwd:3d}  balayage D={out['RightUpperArm']:5.1f}  G={out['LeftUpperArm']:5.1f}  "
          f"écart des mains={xr - xl:.2f}  (cible {J.HAND_SEPARATION})  hauteur bouts={tr.z:.2f}/{tl.z:.2f}  avance={tr.y:.2f}/{tl.y:.2f}  distance mini entre les bras={gap:.2f}")
print("SEAL_SWING =", {k: round((v['RightUpperArm'] + v['LeftUpperArm']) / 2, 1) for k, v in result.items()})
