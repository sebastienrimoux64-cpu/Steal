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


# ---------------------------------------------------------------------------------------------------
# Katon : pistes (temps en s, valeur)
# Pendant les sceaux, les deux mains se touchent au centre de la poitrine : l'angle de rapprochement
# (SEAL_INWARD) est calculé avec la vraie géométrie du rig par tools/anim/calibrate_katon.py
# (jamais à la main) : relancer ce script si vous changez les angles de lever des bras ou la pose du torse.
# ---------------------------------------------------------------------------------------------------
HAND_SEPARATION = 0.4     # écart entre les centres des deux bouts de bras (en unités du rig ; un bras fait 1 de large)

# (nom, début, fin, lever des bras en °) : les bras sont tenus à ces valeurs pendant [début, fin]
SEALS = [("Serpent", 0.62, 0.72, 74), ("Bélier", 0.82, 0.92, 90), ("Singe", 1.02, 1.12, 82),
         ("Sanglier", 1.22, 1.32, 66), ("Cheval", 1.42, 1.52, 94), ("Tigre", 1.62, 2.45, 118)]

# balayage horizontal des bras vers le centre (°) qui amène les deux mains au contact pour chaque sceau
# (rempli par calibrate_katon.py ; les bras sont rapprochés comme quand on croise les mains devant soi)
SEAL_SWING = {"Serpent": 63.0, "Bélier": 61.1, "Singe": 61.5, "Sanglier": 65.4, "Cheval": 61.2, "Tigre": 67.1}

PITCH = [(0, -6), (0.30, -6), (0.48, -10), (0.62, -9), (2.10, -9), (2.70, 10), (3.00, 10), (3.35, -4), (3.50, -43), (3.75, -36), (4.75, -33), (5.20, -12), (5.6, -6)]
YAW = [(0, 8), (0.30, 8), (0.55, 0), (0.72, 2.5), (0.92, -2.5), (1.12, 2.5), (1.32, -2.5), (1.52, 2.5), (1.70, 0), (2.10, 0), (2.70, 24), (3.00, 24),
       (3.35, 10), (3.50, 0), (3.75, 2), (4.75, -4), (5.20, 0), (5.6, 8)]
Z = [(0, -0.22), (0.30, -0.22), (0.48, -0.27), (2.10, -0.27), (2.70, -0.30), (3.35, -0.34), (3.50, -0.36), (4.75, -0.35), (5.20, -0.27), (5.6, -0.22)]
RECOIL = [(0, 0), (3.35, 0), (3.50, -0.10), (3.90, 0.0), (5.6, 0)]
H_PITCH = [(0, 0), (0.30, 0), (0.48, -8), (0.62, -12), (2.10, -12), (2.70, 8), (3.00, 8), (3.35, -4), (3.50, 8), (3.75, 7), (4.75, 10), (5.20, -4), (5.6, 0)]
H_YAW = [(0, -8), (0.30, -8), (0.55, 0), (2.10, 0), (2.70, -24), (3.00, -24), (3.35, -8), (3.50, 0), (4.75, 0), (5.20, 0), (5.6, -8)]
LX = [(0, -0.75), (2.70, -0.75), (3.35, -0.95), (4.75, -0.95), (5.20, -0.80), (5.6, -0.75)]
LY = [(0, 0.10), (3.35, 0.10), (3.50, 0.22), (4.75, 0.22), (5.20, 0.12), (5.6, 0.10)]
RY = [(0, -0.10), (3.35, -0.10), (3.50, -0.42), (4.75, -0.42), (5.20, -0.12), (5.6, -0.10)]


def arm_tracks():
    """Pistes des bras : lever (fwd), écart latéral (abd) et balayage horizontal vers le centre (swing), pour chaque bras."""
    R_fwd = [(0, 8), (0.30, 8), (0.48, 20)]
    R_abd = [(0, 46), (0.30, 46), (0.48, 12)]
    R_sw = [(0, 0), (0.30, 0), (0.48, 0)]
    L_fwd = [(0, 50), (0.30, 50), (0.48, 38)]
    L_abd = [(0, 30), (0.30, 30), (0.48, 10)]
    L_sw = [(0, 0), (0.30, 0), (0.48, 0)]
    for name, t0, t1, f in SEALS:
        sw = SEAL_SWING[name]
        for fwd, abd, swing in ((R_fwd, R_abd, R_sw), (L_fwd, L_abd, L_sw)):
            fwd += [(t0, f), (t1, f)]
            abd += [(t0, 0), (t1, 0)]
            swing += [(t0, sw), (t1, sw)]
    # inspiration : mains toujours jointes pendant la torsion du buste (jusqu'à 2,45 s), puis les bras se rentrent contre le corps
    R_fwd += [(2.80, 36), (3.00, 36), (3.35, 22), (3.50, -30), (3.75, -26), (4.75, -24), (5.20, 6), (5.6, 8)]
    R_abd += [(2.80, -25), (3.00, -25), (3.35, 6), (3.50, 16), (3.75, 14), (4.75, 14), (5.20, 12), (5.6, 46)]
    R_sw += [(2.80, 0), (5.6, 0)]
    L_fwd += [(2.80, -20), (3.00, -20), (3.35, -8), (3.50, -34), (3.75, -30), (4.75, -26), (5.20, 6), (5.6, 50)]
    L_abd += [(2.80, 12), (3.00, 12), (3.35, 10), (3.50, 18), (3.75, 16), (4.75, 16), (5.20, 12), (5.6, 30)]
    L_sw += [(2.80, 0), (5.6, 0)]
    return R_fwd, R_abd, R_sw, L_fwd, L_abd, L_sw


def katon(t):
    """Katon : Gōkakyū no Jutsu (Grande boule de feu) des Uchiha - d'après la séquence de référence (Obito / Kakashi).
      0.00  position prête : très basse, jambes écartées, buste penché, épaule tournée, bras en « griffes »
      0.50  six mains rapides, MAINS AU CONTACT au centre de la poitrine (Serpent, Bélier, Singe, Sanglier, Cheval, Tigre)
      2.10  grande inspiration : le buste se tord et se gonfle (mains toujours jointes), puis les bras se rentrent contre le corps
      3.00  le corps se ramasse (accroupi), puis
      3.35  souffle explosif : buste projeté en avant (avec dépassement), tête relevée, bras tirés en arrière, recul d'un pied
      3.75  jet maintenu (balayage lent) -> 4.75 relâchement -> 5.60 retour à la position prête (début = fin : s'enchaîne)."""
    R_fwd, R_abd, R_sw, L_fwd, L_abd, L_sw = arm_tracks()
    d = {}
    d["Torso"] = dict(rot=(track(t, PITCH), 0, track(t, YAW)), loc=(0, track(t, RECOIL), track(t, Z)))
    d["Head"] = dict(rot=(track(t, H_PITCH), 0, track(t, H_YAW)))
    d["RightUpperArm"] = dict(rot=arm(1, fwd=track(t, R_fwd), abd=track(t, R_abd), twist=track(t, R_sw)))
    d["LeftUpperArm"] = dict(rot=arm(-1, fwd=track(t, L_fwd), abd=track(t, L_abd), twist=-track(t, L_sw)))
    d["LeftLeg-IKTarget"] = dict(loc=(track(t, LX), track(t, LY), 0))
    d["RightLeg-IKTarget"] = dict(loc=(-track(t, LX), track(t, RY), 0))
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
