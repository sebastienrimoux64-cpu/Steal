"""Forme voxel d'une pioche (grille 20x20, y vers le haut) : manche en diagonale + tête en croissant, avec rotation en 3 couches de profondeur.
Retourne un dict {(x, y, z): (rôle, ombrage, bruit)} ; rôle in {"head", "handle", "bind", "pommel"}."""
import math

N = 20                  # taille de la grille
C = (8.0, 8.0)          # centre du croissant
R = 10.6                # rayon extérieur
HALF = 64.0             # demi-ouverture de l'arc autour de la diagonale (°)
LIGHT = (-0.55, 0.83)   # lumière venant d'en haut à gauche


def hash01(x, y, z=0, seed=0):
    n = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (seed * 2654435761)
    n = (n ^ (n >> 13)) * 1274126177 & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def build():
    vox = {}
    # --- tête : croissant ---
    for x in range(N):
        for y in range(N):
            dx, dy = x + 0.5 - C[0] - 0.5, y + 0.5 - C[1] - 0.5
            r = math.hypot(dx, dy)
            ang = math.degrees(math.atan2(dy, dx))
            off = ang - 45.0
            while off > 180: off -= 360
            while off < -180: off += 360
            if abs(off) > HALF:
                continue
            t = 1.0 - (abs(off) / HALF) ** 1.7            # épaisseur : max au centre, pointe aux extrémités
            thick = 1.4 + 3.2 * t
            if not (R - thick <= r <= R + 0.15):
                continue
            u = (r - (R - thick)) / max(thick, 1e-6)       # 0 = bord intérieur, 1 = bord extérieur
            n = (dx / max(r, 1e-6), dy / max(r, 1e-6))
            shade = n[0] * LIGHT[0] + n[1] * LIGHT[1]       # normale extérieure . lumière
            if u > 0.6:   s = 0.55 + 0.45 * shade           # bord extérieur : éclairé en haut à gauche
            elif u < 0.35: s = 0.35 - 0.45 * shade          # bord intérieur : éclairé en bas à droite
            else:         s = 0.5 + 0.15 * shade
            depth = [-1, 0] if (u < 0.22 or u > 0.82 or t < 0.25) else [-2, -1, 0, 1]
            for z in depth:
                vox[(x, y, z)] = ("head", max(0.0, min(1.0, s)), hash01(x, y, z))
    # --- manche : diagonale épaisse de 2, de (0,0) jusqu'au centre du croissant ---
    for i in range(0, 15):
        for (x, y) in ((i, i), (i + 1, i)):
            if 0 <= x < N:
                for z in (-1, 0):
                    if (x, y, z) not in vox or i < 11:
                        vox[(x, y, z)] = ("handle", 0.6 if x == i else 0.35, hash01(x, y, z, 1))
    # --- ligature (là où le manche rejoint la tête) ---
    for i in (11, 12):
        for (x, y) in ((i, i), (i + 1, i), (i, i + 1)):
            for z in (-1, 0):
                if (x, y, z) in vox:
                    vox[(x, y, z)] = ("bind", 0.5, hash01(x, y, z, 2))
    # --- pommeau en bas du manche ---
    for z in (-1, 0):
        for (x, y) in ((0, 0), (1, 0)):
            vox[(x, y, z)] = ("pommel", 0.4, hash01(x, y, z, 3))
    return vox


if __name__ == "__main__":
    v = build()
    for y in range(N - 1, -1, -1):
        row = ""
        for x in range(N):
            cells = [v.get((x, y, z)) for z in (-2, -1, 0, 1)]
            c = next((c for c in cells if c), None)
            row += {"head": "#", "handle": "s", "bind": "b", "pommel": "o"}[c[0]] if c else "."
        print(row)
    print(len(v), "voxels")
