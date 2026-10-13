"""Mesure les vibrations (énergie haute fréquence) des animations R6 : python tools/anim/jitter_check.py <fichier.blend> [...]
Pour chaque partie du corps, on évalue la position/orientation monde à chaque image, puis on regarde quelle part
de l'énergie du mouvement se trouve au-dessus de 3 Hz (un geste franc fait < 3 Hz ; une vibration est plus rapide)."""
import sys
import numpy as np
import bpy

PARTS = ["Head", "Torso", "Left Arm", "Right Arm", "Left Leg", "Right Leg"]
CUT = 3.0   # Hz


def analyse(path):
    bpy.ops.wm.open_mainfile(filepath=path)
    scn = bpy.context.scene
    fps = scn.render.fps
    f0, f1 = scn.frame_start, scn.frame_end
    traj = {p: [] for p in PARTS}
    for f in range(f0, f1 + 1):
        scn.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        for p in PARTS:
            o = bpy.data.objects[p].evaluated_get(dg)
            m = o.matrix_world
            pts = [m @ v.co for v in list(o.data.vertices)[:8]]      # 8 sommets suffisent (blocs)
            traj[p].append(np.array([c for q in pts for c in q]))
    res = {}
    for p in PARTS:
        X = np.array(traj[p])[:-1]                     # on retire la dernière image (= la première) pour l'FFT circulaire
        X = X - X.mean(axis=0)
        F = np.abs(np.fft.rfft(X, axis=0)) ** 2
        freqs = np.fft.rfftfreq(X.shape[0], 1 / fps)
        tot = F[1:].sum()
        hi = F[freqs > CUT].sum()
        res[p] = hi / tot if tot > 0 else 0.0
    return res, fps


if __name__ == "__main__":
    for path in sys.argv[1:]:
        r, fps = analyse(path)
        worst = max(r, key=r.get)
        print(f"{path.split('/')[-1]:22s} " + " ".join(f"{p.split()[-1][:4]}:{100*r[p]:5.2f}%" for p in PARTS) + f"  | max {100*r[worst]:.2f}% ({worst})")
