"""
Techniques / attaques R6 (une action par fichier), sur le rig R6IKFIX.

    python tools/anim/r6_jutsu.py <rig.blend> <dossier_sortie> [Nom ...]

Même repère et mêmes conventions que r6_idles.py (le personnage regarde vers +Y).
Remarque jambes : dans le rig, les jambes IK sont tendues au repos ; on garde donc une posture fléchie (position basse)
dès la première image et jusqu'à la dernière, sans jamais repasser par la jambe droite, pour éviter tout « claquement » de genou.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r6_idles import arm, build, track   # noqa: E402


def katon(t):
    """Katon : Gōkakyū no Jutsu (Grande boule de feu) des Uchiha - d'après la séquence de référence (Obito / Kakashi).
      0.00  position prête : très basse, jambes écartées, buste penché, épaule tournée, bras en « griffes »
      0.50  six mains rapides devant la poitrine (Serpent, Bélier, Singe, Sanglier, Cheval, Tigre), regard sur les mains
      2.10  grande inspiration : le buste se tord et se gonfle, les bras se rentrent contre le corps, la tête regarde la cible
      3.00  le corps se ramasse (accroupi), puis
      3.35  souffle explosif : buste projeté en avant (avec dépassement), tête relevée, bras tirés en arrière, recul d'un pied
      3.75  jet maintenu (balayage lent) -> 4.75 relâchement -> 5.60 retour à la position prête (début = fin : s'enchaîne)."""
    # --- bras (fwd : lever avant ; abd : écarté du corps, négatif = vers l'axe du corps) ---
    seals_t = [0.62, 0.72, 0.82, 0.92, 1.02, 1.12, 1.22, 1.32, 1.42, 1.52, 1.62]
    R_fwd = [(0, 8), (0.30, 8), (0.48, 20), (0.62, 53), (0.72, 53), (0.82, 87), (0.92, 87), (1.02, 65), (1.12, 65), (1.22, 49), (1.32, 49),
             (1.42, 91), (1.52, 91), (1.62, 109), (2.05, 114), (2.70, 36), (3.00, 36), (3.35, 22), (3.50, -30), (3.75, -26), (4.75, -24), (5.20, 6), (5.6, 8)]
    R_abd = [(0, 46), (0.30, 46), (0.48, 12), (0.62, -34), (0.72, -34), (0.82, -38), (0.92, -38), (1.02, -28), (1.12, -28), (1.22, -44), (1.32, -44),
             (1.42, -40), (1.52, -40), (1.62, -42), (2.05, -42), (2.70, -25), (3.00, -25), (3.35, 6), (3.50, 16), (3.75, 14), (4.75, 14), (5.20, 12), (5.6, 46)]
    L_fwd = [(0, 50), (0.30, 50), (0.48, 38), (0.62, 49), (0.72, 49), (0.82, 81), (0.92, 81), (1.02, 59), (1.12, 59), (1.22, 43), (1.32, 43),
             (1.42, 85), (1.52, 85), (1.62, 105), (2.05, 110), (2.70, -20), (3.00, -20), (3.35, -8), (3.50, -34), (3.75, -30), (4.75, -26), (5.20, 6), (5.6, 50)]
    L_abd = [(0, 30), (0.30, 30), (0.48, 10), (0.62, -34), (0.72, -34), (0.82, -38), (0.92, -38), (1.02, -28), (1.12, -28), (1.22, -44), (1.32, -44),
             (1.42, -40), (1.52, -40), (1.62, -42), (2.05, -42), (2.70, 12), (3.00, 12), (3.35, 10), (3.50, 18), (3.75, 16), (4.75, 16), (5.20, 12), (5.6, 30)]
    # --- torse ---
    pitch = [(0, -6), (0.30, -6), (0.48, -10), (0.62, -9), (2.10, -9), (2.70, 10), (3.00, 10), (3.35, -4), (3.50, -43), (3.75, -36), (4.75, -33), (5.20, -12), (5.6, -6)]
    yaw = [(0, 8), (0.30, 8), (0.55, 0), (0.72, 2.5), (0.92, -2.5), (1.12, 2.5), (1.32, -2.5), (1.52, 2.5), (1.70, 0), (2.10, 0), (2.70, 24), (3.00, 24),
           (3.35, 10), (3.50, 0), (3.75, 2), (4.75, -4), (5.20, 0), (5.6, 8)]
    z = [(0, -0.22), (0.30, -0.22), (0.48, -0.27), (2.10, -0.27), (2.70, -0.30), (3.35, -0.34), (3.50, -0.36), (4.75, -0.35), (5.20, -0.27), (5.6, -0.22)]
    recoil = [(0, 0), (3.35, 0), (3.50, -0.10), (3.90, 0.0), (5.6, 0)]
    # --- tête (orientation monde) ---
    h_pitch = [(0, 0), (0.30, 0), (0.48, -8), (0.62, -12), (2.10, -12), (2.70, 8), (3.00, 8), (3.35, -4), (3.50, 8), (3.75, 7), (4.75, 10), (5.20, -4), (5.6, 0)]
    h_yaw = [(0, -8), (0.30, -8), (0.55, 0), (2.10, 0), (2.70, -24), (3.00, -24), (3.35, -8), (3.50, 0), (4.75, 0), (5.20, 0), (5.6, -8)]
    # --- pieds (cibles IK) : appui large, le pied droit recule au souffle ---
    lx = [(0, -0.75), (2.70, -0.75), (3.35, -0.95), (4.75, -0.95), (5.20, -0.80), (5.6, -0.75)]
    ly = [(0, 0.10), (3.35, 0.10), (3.50, 0.22), (4.75, 0.22), (5.20, 0.12), (5.6, 0.10)]
    ry = [(0, -0.10), (3.35, -0.10), (3.50, -0.42), (4.75, -0.42), (5.20, -0.12), (5.6, -0.10)]
    d = {}
    d["Torso"] = dict(rot=(track(t, pitch), 0, track(t, yaw)), loc=(0, track(t, recoil), track(t, z)))
    d["Head"] = dict(rot=(track(t, h_pitch), 0, track(t, h_yaw)))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=track(t, R_fwd), abd=track(t, R_abd)))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=track(t, L_fwd), abd=track(t, L_abd)))
    d["LeftLeg-IKTarget"] = dict(loc=(track(t, lx), track(t, ly), 0))
    d["RightLeg-IKTarget"] = dict(loc=(-track(t, lx), track(t, ry), 0))
    return d


# nom -> (fonction de pose, durée en s, pas entre clés en images, description)
JUTSU = {
    "Katon_GoukakyuuNoJutsu": (katon, 5.6, 2, "Katon : Grande boule de feu (Uchiha)"),
}

if __name__ == "__main__":
    args = sys.argv[1:]
    rig = next(a for a in args if a.endswith(".blend"))
    rest = [a for a in args if a != rig]
    out = rest[0]
    names = [a for a in rest[1:] if a in JUTSU] or list(JUTSU)
    for n in names:
        build(rig, out, n, registry=JUTSU, prefix="Jutsu")
