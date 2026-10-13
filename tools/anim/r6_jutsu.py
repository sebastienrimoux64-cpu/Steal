"""
Techniques / attaques R6 (une action par fichier), sur le rig R6IKFIX.

    python tools/anim/r6_jutsu.py <rig.blend> <dossier_sortie> [Nom ...]

Même repère et mêmes conventions que r6_idles.py (le personnage regarde vers +Y).
Remarque jambes : dans le rig, les jambes IK sont tendues au repos ; on garde donc une posture légèrement fléchie
dès la première image (jamais de passage par la jambe droite) pour éviter tout « claquement » de genou.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r6_idles import arm, build, track   # noqa: E402


def katon(t):
    """Katon : Gōkakyū no Jutsu (Grande boule de feu) des Uchiha.
    Position prête (jambes écartées, fléchies) -> 6 mains rapides (Serpent, Bélier, Singe, Sanglier, Cheval, Tiger) ->
    grande inspiration (buste en arrière, tête levée) -> souffle explosif (buste projeté en avant, mains devant la bouche,
    recul d'un pied) -> maintien du jet -> retour à la position prête (début = fin : peut s'enchaîner / boucler)."""
    # --- bras : lever vers l'avant (fwd) et rapprochement vers l'axe du corps (inward) ---
    fwd = [(0, 10), (0.35, 10), (0.52, 52), (0.68, 52),      # Serpent
           (0.78, 84), (0.92, 84),                           # Bélier
           (1.02, 62), (1.16, 62),                           # Singe
           (1.26, 46), (1.40, 46),                           # Sanglier
           (1.50, 88), (1.64, 88),                           # Cheval
           (1.76, 108), (2.15, 112),                         # Tigre, tenu pendant l'inspiration
           (2.40, 124), (3.30, 118),                         # souffle
           (3.95, 10), (4.4, 10)]
    inward = [(0, 6), (0.35, 6), (0.52, 34), (0.68, 34), (0.78, 38), (0.92, 38), (1.02, 28), (1.16, 28),
              (1.26, 44), (1.40, 44), (1.50, 40), (1.64, 40), (1.76, 42), (2.15, 42), (2.40, 40), (3.30, 38),
              (3.95, 6), (4.4, 6)]
    f = track(t, fwd)
    a = track(t, inward)
    # --- torse (tangage : - = penché en avant, + = en arrière) ---
    pitch = track(t, [(0, -3), (0.35, -3), (0.52, -5), (1.64, -5), (1.76, -4), (2.20, 14), (2.40, -24), (3.30, -19), (3.95, -3), (4.4, -3)])
    yaw = track(t, [(0, 0), (0.52, 2), (0.78, -2), (1.02, 2), (1.26, -2), (1.50, 2), (1.76, 0), (2.20, 0), (2.40, 4), (3.30, -3), (3.95, 0), (4.4, 0)])
    z = track(t, [(0, -0.10), (1.76, -0.10), (2.20, -0.08), (2.40, -0.16), (3.30, -0.14), (3.95, -0.10), (4.4, -0.10)])
    # --- tête (orientation monde) : regarde ses mains, se renverse à l'inspiration, fixe la cible ---
    head = track(t, [(0, -6), (0.35, -6), (0.52, -10), (1.64, -10), (1.76, -8), (2.20, 12), (2.40, 3), (3.30, 9), (3.95, -4), (4.4, -6)])
    # --- pieds (cibles IK) : appui large, le pied droit recule au moment du souffle ---
    lx = track(t, [(0, -0.25), (2.20, -0.25), (2.40, -0.35), (3.30, -0.35), (3.95, -0.25), (4.4, -0.25)])
    ly = track(t, [(0, 0.12), (2.20, 0.12), (2.40, 0.20), (3.30, 0.20), (3.95, 0.12), (4.4, 0.12)])
    ry = track(t, [(0, -0.12), (2.20, -0.12), (2.40, -0.38), (3.30, -0.38), (3.95, -0.12), (4.4, -0.12)])
    d = {}
    d["Torso"] = dict(rot=(pitch, 0, yaw), loc=(0, 0, z))
    d["Head"] = dict(rot=(head, 0, 0))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=f + 3, abd=-a))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=f - 3, abd=-a))
    d["LeftLeg-IKTarget"] = dict(loc=(lx, ly, 0))
    d["RightLeg-IKTarget"] = dict(loc=(-lx, ry, 0))
    return d


# nom -> (fonction de pose, durée en s, pas entre clés en images, description)
JUTSU = {
    "Katon_GoukakyuuNoJutsu": (katon, 4.4, 2, "Katon : Grande boule de feu (Uchiha)"),
}

if __name__ == "__main__":
    args = sys.argv[1:]
    rig = next(a for a in args if a.endswith(".blend"))
    rest = [a for a in args if a != rig]
    out = rest[0]
    names = [a for a in rest[1:] if a in JUTSU] or list(JUTSU)
    for n in names:
        build(rig, out, n, registry=JUTSU, prefix="Jutsu")
