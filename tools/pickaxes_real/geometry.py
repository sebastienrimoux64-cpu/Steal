"""Géométrie d'une pioche réaliste (m). Axe Z = manche (0 = bout, ~0.92 = haut). La tête court le long de X, courbée vers le bas.
Toutes les pièces sont des « lofts » (anneaux de points reliés) : manche ovale, tête effilée en pointes, virole, rivets, cale, ligature."""
import math
from mathutils import Vector

H_TOP = 0.915          # haut du manche
Z_HEAD = 0.862         # hauteur du centre de la tête
R_ARC = 0.42           # rayon de courbure de la tête
THETA = 0.60           # demi-ouverture de l'arc (rad) -> tête d'environ 50 cm


def squircle(n_pts, a, b, p=2.6, rot=0.0):
    """Section arrondie (superellipse) de demi-largeur a, demi-hauteur b."""
    pts = []
    for k in range(n_pts):
        phi = 2 * math.pi * k / n_pts + rot
        c, s = math.cos(phi), math.sin(phi)
        pts.append((a * math.copysign(abs(c) ** (2 / p), c), b * math.copysign(abs(s) ** (2 / p), s)))
    return pts


def loft(bm, rings, smooth=True, caps=True, mat=0, flat=False):
    """rings : liste d'anneaux (listes de Vector de même longueur). Crée les faces ; retourne les faces créées."""
    vs = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    faces = []
    for i in range(len(rings) - 1):
        for j in range(n):
            f = bm.faces.new((vs[i][j], vs[i][(j + 1) % n], vs[i + 1][(j + 1) % n], vs[i + 1][j]))
            faces.append(f)
    if caps:
        faces.append(bm.faces.new(list(reversed(vs[0]))))
        faces.append(bm.faces.new(vs[-1]))
    for f in faces:
        f.material_index = mat
        f.smooth = not flat
    return faces


# ------------------------------------------------------------------ manche
def handle_radii(z):
    """(rx, ry) du manche à la hauteur z : ovale de prise, renflement au pommeau, cou renforcé sous la tête."""
    rx, ry = 0.0158, 0.0128
    rx += 0.0012 * math.sin(math.pi * min(max(z, 0) / 0.45, 1.0))             # léger ventre
    ry += 0.0010 * math.sin(math.pi * min(max(z, 0) / 0.45, 1.0))
    if z < 0.075:                                                              # pommeau évasé
        k = 1 - z / 0.075
        rx += 0.0042 * k ** 1.6
        ry += 0.0035 * k ** 1.6
    if z > 0.76:                                                               # cou qui s'épaissit vers la tête
        k = min((z - 0.76) / 0.10, 1.0)
        k = k * k * (3 - 2 * k)
        rx += 0.0068 * k
        ry += 0.0058 * k
    return rx, ry


def handle_center(z):
    return Vector((0.0032 * math.sin(2 * math.pi * z / 0.92), 0.0, z))   # très légère courbure en S


def build_handle(bm, mat=0, n_sec=28):
    zs = []
    # bout arrondi : quart de cercle de rayon ~ rx
    r_end = 0.0198
    for k in range(8):
        a = (math.pi / 2) * k / 7
        zs.append(("end", -0.0075 + 0.0075 * (1 - math.cos(a)) - 0.0 , math.sin(a)))
    rings = []
    # anneaux du bout (tangent à z=0) : z de -0.0075 à 0, échelle de 0.2 à 1
    for k in range(8):
        a = (math.pi / 2) * k / 7
        z = -0.0085 * math.cos(a)
        sc = max(0.12, math.sin(a))
        rx, ry = handle_radii(0.0)
        c = handle_center(0.0)
        rings.append([Vector((c.x + x * sc, y * sc, z)) for (x, y) in squircle(n_sec, rx, ry, 2.2)])
    z = 0.0
    while z < H_TOP - 1e-9:
        z += 0.006 if z < 0.1 or z > 0.78 else 0.014
        z = min(z, H_TOP)
        rx, ry = handle_radii(z)
        c = handle_center(z)
        rings.append([Vector((c.x + x, y, z)) for (x, y) in squircle(n_sec, rx, ry, 2.2)])
    # sommet légèrement arrondi
    rx, ry = handle_radii(H_TOP)
    c = handle_center(H_TOP)
    for sc, dz in ((0.93, 0.0015), (0.8, 0.0028), (0.55, 0.0036)):
        rings.append([Vector((c.x + x * sc, y * sc, H_TOP + dz)) for (x, y) in squircle(n_sec, rx, ry, 2.2)])
    return loft(bm, rings, mat=mat)


# ------------------------------------------------------------------ tête
def head_frame(theta):
    """position du centre de la tête, normale (haut/extérieur), binormale (Y)."""
    p = Vector((R_ARC * math.sin(theta), 0.0, Z_HEAD - R_ARC * (1 - math.cos(theta))))
    N = Vector((math.sin(theta), 0.0, math.cos(theta)))
    B = Vector((0.0, 1.0, 0.0))
    return p, N, B


def taper(t, q=1.5, r=0.9, floor=0.012):
    return max(floor, (1 - abs(t) ** q) ** r)


def build_head(bm, mat=1, kind="smooth", n_rings=None):
    """kind = 'smooth' (métal, bois, pierre polie) ou 'crystal' (taillé à facettes)."""
    if kind == "crystal":
        n_sec, p, n_rings = 6, 2.0, n_rings or 15
        w0, h0 = 0.022, 0.032
    else:
        n_sec, p, n_rings = 24, 2.6, n_rings or 120
        w0, h0 = 0.022, 0.031
    rings = []
    for i in range(n_rings + 1):
        s = -1 + 2 * i / n_rings
        t = math.copysign(1 - (1 - abs(s)) ** 1.9, s) if kind != "crystal" else s * 0.999
        th = t * THETA
        pos, N, B = head_frame(th)
        f = taper(t, 1.7 if kind != "crystal" else 1.4, 0.85 if kind != "crystal" else 0.8)
        # boss central : épaississement autour du manche
        boss = 1 + 0.30 * math.exp(-(t / 0.13) ** 2)
        a, b = w0 * f * boss, h0 * f * boss
        sec = squircle(n_sec, a, b, p, rot=math.pi / n_sec if kind == "crystal" else 0.0)
        ring = [pos + B * x + N * y for (x, y) in sec]
        rings.append(ring)
    # pointes : on referme sur un point
    return loft(bm, rings, mat=mat, flat=(kind == "crystal"))


# ------------------------------------------------------------------ virole, rivets, cale
def build_collar(bm, mat=2, z0=0.826, z1=0.900):
    rings = []
    n = 14
    zs = [z0 + (z1 - z0) * k / 11 for k in range(12)]
    for k, z in enumerate(zs):
        edge = min(k, 11 - k)
        sc = (0.86, 0.95, 1.0, 1.0, 1.0, 1.0)[min(edge, 5)]
        rx, ry = 0.0318 * sc, 0.0268 * sc
        c = handle_center(z)
        rings.append([Vector((c.x + x, y, z)) for (x, y) in squircle(n, rx, ry, 3.2)])
    return loft(bm, rings, mat=mat)


def build_sphere(bm, center, radius, mat, squash=(1, 1, 1)):
    import bmesh
    res = bmesh.ops.create_uvsphere(bm, u_segments=14, v_segments=8, radius=radius)
    faces = set()
    for v in res["verts"]:
        v.co = Vector((v.co.x * squash[0], v.co.y * squash[1], v.co.z * squash[2])) + center
        faces.update(v.link_faces)
    for f in faces:
        f.material_index = mat
        f.smooth = True
    return list(faces)


def build_rivets(bm, mat=2):
    for z in (0.842, 0.884):
        for sx in (-1, 1):
            c = handle_center(z)
            build_sphere(bm, Vector((c.x + sx * 0.0318, 0, z)), 0.0050, mat, (0.55, 1, 1))


def build_wedge(bm, mat=3):
    c = handle_center(H_TOP)
    rings = []
    for z, sx in ((H_TOP - 0.004, 0.019), (H_TOP + 0.004, 0.0185), (H_TOP + 0.012, 0.016), (H_TOP + 0.016, 0.0)):
        w = 0.0025 * (1 if sx > 0 else 0.2)
        rings.append([Vector((c.x + x, y, z)) for (x, y) in ((-sx, -w), (sx, -w), (sx, w), (-sx, w))])
    return loft(bm, rings, mat=mat, flat=True)


# ------------------------------------------------------------------ hélices (cuir, corde)
def build_helix(bm, z0, z1, turns, tube_r, mat, pad=0.0015, n_around=8, per_turn=24, follow_handle=True, wobble=0.0):
    steps = int(turns * per_turn)
    rings = []
    for k in range(steps + 1):
        s = k / steps
        z = z0 + (z1 - z0) * s
        ang = 2 * math.pi * turns * s
        rx, ry = handle_radii(z)
        c = handle_center(z)
        rr = tube_r + pad
        P = Vector((c.x + (rx + rr) * math.cos(ang), (ry + rr) * math.sin(ang), z))
        # repère local : radial R, tangent T (approximé), binormale
        dz = (z1 - z0) / steps
        ang2 = 2 * math.pi * turns * (k + 1) / steps
        rx2, ry2 = handle_radii(z + dz)
        c2 = handle_center(z + dz)
        P2 = Vector((c2.x + (rx2 + rr) * math.cos(ang2), (ry2 + rr) * math.sin(ang2), z + dz))
        T = (P2 - P).normalized()
        R = Vector((math.cos(ang), math.sin(ang), 0.0))
        Bn = T.cross(R).normalized()
        Rn = Bn.cross(T).normalized()
        ring = []
        for j in range(n_around):
            a = 2 * math.pi * j / n_around
            ring.append(P + Rn * (tube_r * math.cos(a)) + Bn * (tube_r * 0.8 * math.sin(a)))
        rings.append(ring)
    return loft(bm, rings, mat=mat, caps=True)
