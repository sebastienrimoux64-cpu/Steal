"""
Katanas RÉALISTES (non voxel) : bois (bokken), fer, or, diamant.

    python tools/katanas/make_real_katanas.py [Nom ...]      # -> KatanasRealistic/

Origine = bout du manche (z = 0), lame vers +Z (~1,05 m au total), dos de la lame vers +X, courbure (sori) vers +X.
Un .blend par katana (matériaux procéduraux, studio + caméra) ; combine_katanas.py assemble les 4 ensemble.
Lame : section à arête (shinogi), pointe (kissaki), hamon = frontière ondulée modélisée dans la géométrie.
"""
import math
import os
import sys

import bpy
import bmesh  # noqa: E402
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "pickaxes_real"))
import geometry as G
import materials as M
import make_real_pickaxes as P

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "KatanasRealistic")
ORDER = ["Wood", "Iron", "Gold", "Diamond"]

Z_TSUBA = 0.27
Z_BLADE0 = 0.30
L_BLADE = 0.745
W0, T0 = 0.036, 0.0092
SORI = 0.022
TIP_START = 0.93


def hnoise(z):
    return 0.5 + 0.28 * math.sin(z * 150) + 0.14 * math.sin(z * 331 + 1.3) + 0.08 * math.sin(z * 59 + 0.4)


def blade_center(zb):
    s = zb / L_BLADE
    return SORI * s * s


def ring_frame(zb):
    d = 2 * SORI * zb / (L_BLADE ** 2)
    th = math.atan(d)
    return math.cos(th), math.sin(th)


def build_blade(bm, mat_body, mat_edge):
    """Section : spine (u=+w/2), shinogi (u=+0.12w), hamon (ligne ondulée sur le biseau), tranchant (u=-w/2)."""
    rings = []
    n = 150
    for i in range(n + 1):
        s = i / n
        zb = L_BLADE * s
        w = W0 * (1 - 0.30 * s)
        t = T0 * (1 - 0.35 * s)
        k = max(0.0, (s - TIP_START) / (1 - TIP_START))        # kissaki
        # pointe oblique : la section se replie vers le dos
        sc_u = (1 - k) ** 0.8 + 0.015
        sc_v = (1 - k * k) + 0.02
        hm = -w / 2 + w * (0.26 + 0.12 * hnoise(zb))            # position (u) du hamon, ondule
        pts = [(w / 2, t / 2), (w / 2, -t / 2), (0.12 * w, -t / 2), (hm, -t * 0.22), (-w / 2, 0.0), (hm, t * 0.22), (0.12 * w, t / 2)]
        c, sn = ring_frame(zb)
        cx = blade_center(zb)
        ring = []
        for (u, v) in pts:
            u2 = w / 2 - (w / 2 - u) * sc_u
            v2 = v * sc_v
            ring.append(Vector((cx + u2 * c, v2, Z_BLADE0 + zb - u2 * sn)))
        rings.append(ring)
    faces = G.loft(bm, rings, mat=mat_body, flat=True)
    # faces par segment : 7 faces par tranche ; bande hamon = faces (hamon -> tranchant -> hamon) -> indices 3 et 4
    for idx, f in enumerate(faces[:n * 7]):
        if idx % 7 in (3, 4):
            f.material_index = mat_edge
    return faces


def oval_ring(cx, cz, a, b, n=36, p=2.2):
    return [Vector((cx + x, y, cz)) for (x, y) in G.squircle(n, a, b, p)]


def build_tsuka(bm, mat):
    rings = []
    zs = [0.0 + 0.0005 * k for k in range(0)]
    # kashira (pommeau) arrondi puis manche en ovale avec léger ventre
    for k in range(7):
        a = (math.pi / 2) * k / 6
        sc = max(0.5, math.sin(a) ** 0.6)
        rings.append(oval_ring(0, 0.004 * (1 - math.cos(a)) * 0 + 0.0 + 0.0 * k, 0.0215 * sc, 0.0168 * sc))
    z = 0.0
    n = 40
    rings = []
    for k in range(n + 1):
        s = k / n
        z = 0.0005 + (Z_TSUBA - 0.012) * s
        bulge = 1 + 0.07 * math.sin(math.pi * s)
        a, b = 0.0185 * bulge, 0.0148 * bulge
        rings.append(oval_ring(0, z, a, b))
    return G.loft(bm, rings, mat=mat)


def tsuka_radii(z):
    s = (z - 0.0005) / (Z_TSUBA - 0.012 - 0.0005)
    bulge = 1 + 0.07 * math.sin(math.pi * min(max(s, 0), 1))
    return 0.0185 * bulge, 0.0148 * bulge


def build_wrap(bm, mat, z0=0.045, z1=0.245, turns=12, tube=0.0052):
    """Tsuka-ito : deux rubans hélicoïdaux croisés (motif en losanges)."""
    for sgn in (1, -1):
        steps = int(turns * 40)
        rings = []
        for k in range(steps + 1):
            s = k / steps
            z = z0 + (z1 - z0) * s
            ang = sgn * 2 * math.pi * turns * s
            rx, ry = tsuka_radii(z)
            rr = tube * 0.55
            P0 = Vector(((rx + rr) * math.cos(ang), (ry + rr) * math.sin(ang), z))
            ang2 = sgn * 2 * math.pi * turns * (k + 1) / steps
            z2 = z + (z1 - z0) / steps
            rx2, ry2 = tsuka_radii(z2)
            P1 = Vector(((rx2 + rr) * math.cos(ang2), (ry2 + rr) * math.sin(ang2), z2))
            T = (P1 - P0).normalized()
            R = Vector((math.cos(ang), math.sin(ang), 0.0))
            Bn = T.cross(R).normalized()
            Rn = Bn.cross(T).normalized()
            ring = [P0 + Rn * (tube * 0.7 * math.cos(2 * math.pi * j / 8)) + Bn * (tube * math.sin(2 * math.pi * j / 8)) for j in range(8)]
            rings.append(ring)
        G.loft(bm, rings, mat=mat)
    # bandes d'extrémité
    for zc in (z0 - 0.004, z1 + 0.004):
        rx, ry = tsuka_radii(zc)
        G.loft(bm, [oval_ring(0, zc - 0.003, rx + 0.0012, ry + 0.0012), oval_ring(0, zc + 0.003, rx + 0.0012, ry + 0.0012)], mat=mat)


def build_kashira(bm, mat):
    """Pommeau et fuchi (virole sous la garde)."""
    rings = []
    for k in range(10):
        a = (math.pi / 2) * k / 9
        sc = max(0.12, math.sin(a))
        rings.append(oval_ring(0, -0.004 * (1 - math.cos(a)) * 0 + 0.017 * (1 - math.cos(a)) * 0 + 0.0 + 0.0 * k + 0.0 - 0.0, 0.0, 0.0)) if False else None
    rings = []
    for k in range(10):
        a = (math.pi / 2) * k / 9
        sc = max(0.14, math.sin(a))
        z = -0.007 * math.cos(a)
        rings.append(oval_ring(0, z, 0.0212 * sc, 0.0176 * sc))
    for z in (0.012, 0.030, 0.034):
        rx, ry = tsuka_radii(z) if z > 0.0005 else (0.0185, 0.0148)
        rings.append(oval_ring(0, z, 0.0212 if z < 0.03 else rx + 0.0018, 0.0176 if z < 0.03 else ry + 0.0018))
    G.loft(bm, rings, mat=mat)
    # fuchi
    z0, z1 = Z_TSUBA - 0.026, Z_TSUBA - 0.001
    rings = []
    for k in range(5):
        s = k / 4
        z = z0 + (z1 - z0) * s
        r = 1 + 0.006 + 0.1 * s ** 3
        rx, ry = tsuka_radii(min(z, Z_TSUBA - 0.0125))
        rings.append(oval_ring(0, z, (rx + 0.0014) * r, (ry + 0.0014) * r))
    G.loft(bm, rings, mat=mat)


def build_tsuba(bm, mat, mat_inner):
    zc = Z_TSUBA + 0.0035
    rings = []
    prof = [(0.0, 0.88), (0.0012, 0.97), (0.0030, 1.0), (0.0055, 1.0), (0.0068, 0.97), (0.0070, 0.88)]
    for dz, sc in prof:
        rings.append([Vector((x * sc * 1.0, y * sc, Z_TSUBA + dz)) for (x, y) in G.squircle(56, 0.0390, 0.0365, p=2.35)])
    G.loft(bm, rings, mat=mat)
    # bourrelet (mimi) : anneau bombé sur la tranche
    rings = []
    for dz, sc in ((0.0006, 1.0), (0.0020, 1.045), (0.0040, 1.05), (0.0052, 1.045), (0.0064, 1.0)):
        rings.append([Vector((x * sc, y * sc, Z_TSUBA + dz)) for (x, y) in G.squircle(56, 0.0390, 0.0365, p=2.35)])
    G.loft(bm, rings, mat=mat_inner)
    # seppa (rondelles) dessus/dessous
    for dz0 in (-0.0025, 0.0070):
        rings = []
        for sc, d in ((0.92, 0.0), (1.0, 0.0006), (1.0, 0.0019), (0.92, 0.0025)):
            rings.append([Vector((x * sc, y * sc, Z_TSUBA + dz0 + d)) for (x, y) in G.squircle(32, 0.0245, 0.0205, p=2.2)])
        G.loft(bm, rings, mat=mat_inner)


def build_habaki(bm, mat):
    z0, z1 = Z_TSUBA + 0.0072, Z_BLADE0 + 0.044
    rings = []
    for k in range(7):
        s = k / 6
        z = z0 + (z1 - z0) * s
        a = 0.0185 - 0.0035 * s
        b = 0.0102 - 0.0018 * s
        rings.append([Vector((x + SORI * ((z - Z_BLADE0) / L_BLADE) ** 2 * 0 + 0.0 + 0.0, y, z)) for (x, y) in G.squircle(28, a, b, 2.4)])
    G.loft(bm, rings, mat=mat)


def cfg(name):
    ash = ("ash", P.ASH)
    if name == "Wood":
        return dict(body=lambda: M.wood("Blade_Oak", *P.OAK, ring_dir="Z", scale=140), edge=None,
                    tsuba=lambda: M.wood("Tsuba_Walnut", *P.WALNUT, ring_dir="Z", scale=300), tsuba2=lambda: M.wood("Seppa_Walnut", *P.WALNUT, ring_dir="Z", scale=300),
                    habaki=lambda: M.wood("Habaki_Walnut", *P.WALNUT, ring_dir="Z", scale=300),
                    core=lambda: M.wood("Tsuka_Oak", *P.OAK, ring_dir="Z", scale=300), wrap=lambda: M.rope("Wrap_Rope", (0.62, 0.48, 0.28)),
                    kashira=lambda: M.wood("Kashira_Walnut", *P.WALNUT, ring_dir="Z", scale=300), label="bois (bokken)")
    if name == "Iron":
        steel = lambda: M.metal("Steel_Blade", (0.62, 0.64, 0.68), (0.42, 0.44, 0.48), (0.10, 0.22), scratch=0.65, edge=(0.95, 0.96, 1.0), aniso=0.0)
        return dict(body=steel, edge=lambda: M.metal("Steel_Hamon", (0.92, 0.94, 0.98), (0.78, 0.80, 0.85), (0.06, 0.14), scratch=0.4, edge=(1, 1, 1)),
                    tsuba=lambda: M.metal("Tsuba_Iron", (0.16, 0.16, 0.18), (0.09, 0.09, 0.11), (0.28, 0.5), rust=dict(color=(0.35, 0.14, 0.06), amount=0.25)),
                    tsuba2=lambda: M.metal("Seppa_Brass", (0.80, 0.58, 0.22), (0.62, 0.42, 0.14), (0.25, 0.45)),
                    habaki=lambda: M.metal("Habaki_Brass", (0.88, 0.66, 0.26), (0.7, 0.5, 0.17), (0.18, 0.35), scratch=0.3),
                    core=lambda: M.leather("Samegawa", (0.82, 0.80, 0.72)), wrap=lambda: M.leather("Ito_Black", (0.025, 0.025, 0.03)),
                    kashira=lambda: M.metal("Kashira_Iron", (0.16, 0.16, 0.18), (0.09, 0.09, 0.11), (0.28, 0.5)), label="fer (acier)")
    if name == "Gold":
        return dict(body=lambda: M.metal("Gold_Blade", (1.0, 0.78, 0.30), (0.95, 0.64, 0.17), (0.08, 0.2), edge=(1.0, 0.93, 0.62), scratch=0.3),
                    edge=lambda: M.metal("Gold_Hamon", (1.0, 0.88, 0.50), (1.0, 0.78, 0.32), (0.05, 0.12), edge=(1.0, 0.97, 0.78), scratch=0.2),
                    tsuba=lambda: M.metal("Tsuba_Gold", (0.95, 0.70, 0.22), (0.78, 0.52, 0.12), (0.14, 0.32), scratch=0.4),
                    tsuba2=lambda: M.metal("Seppa_Gold", (1.0, 0.8, 0.34), (0.9, 0.62, 0.16), (0.14, 0.3)),
                    habaki=lambda: M.metal("Habaki_Gold", (1.0, 0.8, 0.34), (0.9, 0.62, 0.16), (0.14, 0.3)),
                    core=lambda: M.leather("Samegawa_Cream", (0.85, 0.78, 0.62)), wrap=lambda: M.leather("Ito_Crimson", (0.35, 0.02, 0.04)),
                    kashira=lambda: M.metal("Kashira_Gold", (0.95, 0.70, 0.22), (0.78, 0.52, 0.12), (0.14, 0.32)), label="or")
    if name == "Diamond":
        dia = lambda: M.crystal("Diamond_Blade", (0.92, 0.99, 1.0), (0.35, 0.88, 0.95), ior=2.42)
        return dict(body=dia, edge=lambda: M.crystal("Diamond_Edge", (0.97, 1.0, 1.0), (0.5, 0.93, 0.98), ior=2.42),
                    tsuba=lambda: M.metal("Tsuba_Steel", (0.70, 0.73, 0.78), (0.5, 0.53, 0.58), (0.08, 0.2)),
                    tsuba2=lambda: M.metal("Seppa_Steel", (0.78, 0.80, 0.85), (0.6, 0.62, 0.67), (0.08, 0.2)),
                    habaki=lambda: M.metal("Habaki_Steel", (0.78, 0.80, 0.85), (0.6, 0.62, 0.67), (0.08, 0.2)),
                    core=lambda: M.leather("Samegawa_Pearl", (0.78, 0.82, 0.86)), wrap=lambda: M.leather("Ito_Navy", (0.02, 0.06, 0.20)),
                    kashira=lambda: M.metal("Kashira_Steel", (0.70, 0.73, 0.78), (0.5, 0.53, 0.58), (0.08, 0.2)), label="diamant")
    raise KeyError(name)


def build_katana(name, location=(0, 0, 0)):
    c = cfg(name)
    mats = []
    def slot(fn):
        mats.append(fn())
        return len(mats) - 1
    s_body = slot(c["body"])
    s_edge = slot(c["edge"]) if c["edge"] else s_body
    s_tsuba = slot(c["tsuba"]); s_t2 = slot(c["tsuba2"]); s_hab = slot(c["habaki"])
    s_core = slot(c["core"]); s_wrap = slot(c["wrap"]); s_kas = slot(c["kashira"])
    bm = bmesh.new()
    build_blade(bm, s_body, s_edge)
    build_habaki(bm, s_hab)
    build_tsuba(bm, s_tsuba, s_t2)
    build_tsuka(bm, s_core)
    build_wrap(bm, s_wrap)
    build_kashira(bm, s_kas)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(f"Katana_{name}")
    bm.to_mesh(mesh)
    bm.free()
    for m in mats:
        mesh.materials.append(m)
    obj = bpy.data.objects.new(f"Katana_{name}", mesh)
    obj.location = location
    obj["material_name"] = c["label"]
    return obj


def main(names):
    os.makedirs(OUT, exist_ok=True)
    for name in names:
        P.reset()
        coll = bpy.data.collections.new(f"Katana_{name}"); bpy.context.scene.collection.children.link(coll)
        obj = build_katana(name)
        coll.objects.link(obj)
        try:
            obj.asset_mark(); obj.asset_data.description = f"Katana réaliste : {obj['material_name']}"
        except Exception:
            pass
        P.studio(res=(1200, 1200))
        P.camera((-1.25, -1.85, 0.56), (0.02, 0, 0.5), 62)
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, f"Katana_{name}_Realistic.blend"))
        print(f"Katana_{name}: {len(obj.data.polygons)} faces, {len(obj.data.materials)} matériaux")


if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in ORDER] or ORDER
    main(wanted)
