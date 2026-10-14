"""
Géométrie RÉALISTE du NaturePack : roches sculptées, arches, tubes à écorce cannelée, feuilles, planches, cristaux.
Toutes les primitives écrivent dans un seul bmesh (un objet par asset) avec un indice de matériau par face
et des UV adaptés au matériau (cylindriques pour les troncs, mètres pour les planches / feuilles).
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion, Euler, noise

def V(*a):
    if not a:
        return Vector((0.0, 0.0, 0.0))
    return Vector(a) if len(a) > 1 else Vector(a[0])


def smin(a, b, k):
    """Minimum lisse (polynomial)."""
    h = max(k - abs(a - b), 0.0) / k
    return min(a, b) - h * h * k * 0.25


def fbm(p, octaves=5, lac=2.07, gain=0.5, seed=0.0):
    s, amp, f, tot = 0.0, 1.0, 1.0, 0.0
    off = V((seed * 13.7, seed * 7.3, seed * 3.1))
    for _ in range(octaves):
        s += amp * noise.noise(p * f + off)
        tot += amp
        amp *= gain
        f *= lac
    return s / tot


def ridged(p, octaves=4, lac=2.1, gain=0.5, seed=0.0):
    s, amp, f, tot = 0.0, 1.0, 1.0, 0.0
    off = V((seed * 5.7, seed * 11.3, seed * 2.9))
    for _ in range(octaves):
        s += amp * (1.0 - abs(noise.noise(p * f + off))) ** 2
        tot += amp
        amp *= gain
        f *= lac
    return s / tot


class RB:
    def __init__(self, name, seed=1):
        self.name = name
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.col = self.bm.loops.layers.float_color.new("rand")
        self.mats = []
        self.rnd = random.Random(seed)
        self.seed = seed

    def use(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    # ------------------------------------------------------------ bas niveau
    def _faces_uv(self, faces, uvfn=None, rand=None, smooth=True, mat=0):
        for f in faces:
            f.smooth = smooth
            f.material_index = mat
            for l in f.loops:
                if uvfn is not None:
                    l[self.uv].uv = uvfn(l)
                if rand is not None:
                    l[self.col] = (rand, rand, rand, 1.0)

    def sharp_by_angle(self, faces, deg):
        lim = math.radians(deg)
        es = set()
        for f in faces:
            es.update(f.edges)
        for e in es:
            if len(e.link_faces) == 2:
                e.smooth = e.calc_face_angle(0.0) < lim

    # ------------------------------------------------------------ roche sculptée
    def rock(self, c, R, mat, seed=0, sub=6, planes=7, depth=(0.72, 0.92), amp=0.16, freq=1.25, ridge=0.18, kcut=0.18, rot=None,
             strata=0.0, strata_f=6.0, flat_bottom=None, sharp=38, detail=0.045, extra_planes=(), sph_uv=False):
        """Rocher : icosphère très subdivisée, déformée par bruit fractal + crêtes + plans de coupe (facettes anguleuses) + strates."""
        c = V(c)
        rx, ry, rz = R if isinstance(R, (tuple, list)) else (R, R, R)
        r = random.Random(seed * 977 + self.seed)
        res = bmesh.ops.create_icosphere(self.bm, subdivisions=sub, radius=1.0)
        verts = res["verts"]
        pls = []
        for _ in range(planes):
            n = V((r.gauss(0, 1), r.gauss(0, 1), r.gauss(0, 1) * 0.8)).normalized()
            pls.append((n, r.uniform(*depth)))
        pls.extend((V(n).normalized(), h) for n, h in extra_planes)
        M = rot.to_matrix() if rot is not None else Matrix.Identity(3)
        sv = seed * 3.7
        faces = set()
        for v in verts:
            d = v.co.normalized()
            rr = 1.0 + amp * fbm(d * freq, 5, seed=sv) + ridge * (ridged(d * freq * 1.7, 3, seed=sv) - 0.5)
            for n, h in pls:
                dn = d.dot(n)
                if dn > 1e-3:
                    rr = smin(rr, h / dn, kcut)
            p = V((d.x * rx * rr, d.y * ry * rr, d.z * rz * rr))
            if detail:
                p += d * detail * fbm(p * 3.1, 4, seed=sv + 1.7) * max(rx, ry, rz)
            if strata:
                p.z += strata * math.sin(p.z * strata_f * 6.283 + 2.2 * fbm(p * 0.7, 2, seed=sv + 4.0)) * 0.1
            if flat_bottom is not None and p.z < flat_bottom:
                p.z = flat_bottom + (p.z - flat_bottom) * 0.12
            v.co = c + M @ p
            faces.update(v.link_faces)
        mi = self.use(mat)
        if sph_uv:
            def uvf(l):
                d = (l.vert.co - c)
                d = (M.inverted() @ d).normalized()
                return (0.5 + math.atan2(d.y, d.x) / (2 * math.pi), 0.5 + math.asin(max(-1.0, min(1.0, d.z))) / math.pi)
        else:
            uvf = lambda l: (0.0, 0.0)
        self._faces_uv(faces, uvf, mat=mi)
        self.sharp_by_angle(faces, sharp)
        return list(faces)

    # ------------------------------------------------------------ tube à écorce
    def tube(self, path, radii, mat, sides=12, flute=0.0, flute_n=5, flute_f=1.0, seed=0, cap_a=False, cap_b=True, twist=0.0, ex=1.0,
             uv_len=1.0, rand=None, smooth=True, up=None, noise_amp=0.0, noise_f=2.0, cap_mat=None, cap_disc=False, vstart=0.0):
        """Tube le long d'une polyligne. radii : liste ou f(t). flute : cannelures du tronc ; noise_amp : bosses irrégulières.
        UV : u = angle (0..1), v = longueur cumulée en mètres * uv_len."""
        bm = self.bm
        path = [V(p) for p in path]
        n = len(path)
        T = (path[1] - path[0]).normalized()
        ref = V(up) if up is not None else (V(0, 1, 0) if abs(T.y) < 0.9 else V(1, 0, 0))
        Nn = ref.cross(T).normalized()
        Bn = T.cross(Nn).normalized()
        rings, ls = [], []
        acc = 0.0
        for i, p in enumerate(path):
            if 0 < i < n - 1:
                Tn = (path[i + 1] - path[i - 1]).normalized()
            elif i == 0:
                Tn = (path[1] - path[0]).normalized()
            else:
                Tn = (path[-1] - path[-2]).normalized()
            if i > 0:
                acc += (path[i] - path[i - 1]).length
                q = T.rotation_difference(Tn)
                Nn, Bn, T = q @ Nn, q @ Bn, Tn
            t = i / max(1, n - 1)
            r = radii(t) if callable(radii) else radii[i]
            rx, ry = (r if isinstance(r, (tuple, list)) else (r, r / ex))
            ring = []
            for s in range(sides):
                a = 2 * math.pi * s / sides + twist * t
                k = 1.0
                if flute:
                    k += flute * (math.sin(flute_n * a + 6.0 * t * flute_f + seed) * 0.6 + 0.4 * math.sin((flute_n * 2 + 1) * a - 3.1 * t * flute_f + seed * 2))
                if noise_amp:
                    cx, cy = math.cos(a) * noise_f, math.sin(a) * noise_f
                    k += noise_amp * noise.noise(V((cx + seed, cy, acc * noise_f * 0.7)))
                ring.append(p + Nn * (math.cos(a) * rx * k) + Bn * (math.sin(a) * ry * k))
            rings.append(ring)
            ls.append(acc)
        mi = self.use(mat)
        vs = [[bm.verts.new(p) for p in ring] for ring in rings]
        faces = []
        for i in range(n - 1):
            for j in range(sides):
                j2 = (j + 1) % sides
                f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
                faces.append(f)
                f.smooth = smooth
                f.material_index = mi
                for l in f.loops:
                    v = l.vert
                    ii = i + (1 if v in (vs[i + 1][j2], vs[i + 1][j]) else 0)
                    jj = j + (1 if v in (vs[i][j2], vs[i + 1][j2]) else 0)
                    l[self.uv].uv = (jj / sides, vstart + ls[ii] * uv_len)
                    if rand is not None:
                        l[self.col] = (rand, rand, rand, 1.0)
        for cap, ring_vs, flip, idx in ((cap_a, vs[0], True, 0), (cap_b, vs[-1], False, -1)):
            if not cap:
                continue
            f = bm.faces.new(list(reversed(ring_vs)) if flip else ring_vs)
            f.smooth = False
            cmi = self.use(cap_mat) if cap_mat is not None else mi
            f.material_index = cmi
            c = sum((v.co for v in ring_vs), V()) / len(ring_vs)
            Rm = max((v.co - c).length for v in ring_vs) or 1e-6
            e1 = (ring_vs[0].co - c).normalized()
            e2 = f.normal.cross(e1)
            for l in f.loops:
                d = l.vert.co - c
                if cap_disc:
                    l[self.uv].uv = (0.5 + d.dot(e1) / Rm * 0.5, 0.5 + d.dot(e2) / Rm * 0.5)
                else:
                    l[self.uv].uv = (0.0, 0.0)
            faces.append(f)
        return faces

    # ------------------------------------------------------------ grille générique (surfaces)
    def loft(self, rings, mat, uvfn=None, closed=True, smooth=True, rand=None, cap_a=False, cap_b=False):
        bm = self.bm
        mi = self.use(mat)
        m, n = len(rings), len(rings[0])
        vs = [[bm.verts.new(p) for p in ring] for ring in rings]
        faces = []
        span = n if closed else n - 1
        for i in range(m - 1):
            for j in range(span):
                j2 = (j + 1) % n
                try:
                    f = bm.faces.new((vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]))
                except ValueError:
                    continue
                faces.append(f)
                f.smooth = smooth
                f.material_index = mi
                for l in f.loops:
                    v = l.vert
                    ii = i + (1 if v in (vs[i + 1][j2], vs[i + 1][j]) else 0)
                    jj = j + (1 if v in (vs[i][j2], vs[i + 1][j2]) else 0)
                    if uvfn is not None:
                        l[self.uv].uv = uvfn(ii / max(1, m - 1), jj / (n if closed else max(1, n - 1)), v.co)
                    if rand is not None:
                        l[self.col] = (rand, rand, rand, 1.0)
        for cap, ring_vs, flip in ((cap_a, vs[0], True), (cap_b, vs[-1], False)):
            if cap:
                f = bm.faces.new(list(reversed(ring_vs)) if flip else ring_vs)
                f.smooth = False
                f.material_index = mi
                faces.append(f)
        return faces

    # ------------------------------------------------------------ feuille
    def leaf(self, base, direction, up, length, width, mat, curl=0.25, twist=0.0, rand=0.5, seg=5, shape="ovate", fold=0.25, droop=0.0):
        """Feuille : bande pliée en V le long de la nervure, courbée vers le bas ; UV u = longueur (0..1), v = largeur (0..1)."""
        bm = self.bm
        d = V(direction).normalized()
        u = V(up).normalized()
        side = d.cross(u).normalized()
        u = side.cross(d).normalized()
        rings = []
        for i in range(seg + 1):
            t = i / seg
            if shape == "ovate":
                w = math.sin(math.pi * t ** 0.8) ** 0.85 * (1 - 0.15 * t)
            elif shape == "lance":
                w = math.sin(math.pi * (0.12 + 0.88 * t) ** 0.95) ** 0.9 * (1 - 0.2 * t)
            elif shape == "round":
                w = math.sin(math.pi * t ** 0.7) ** 0.6
            elif shape == "rect":
                w = 1.0
            elif shape == "grass":
                w = (1.0 - t) ** 0.75 * (0.55 + 0.45 * min(1.0, t * 6))
            else:
                w = math.sin(math.pi * t)
            ang = curl * t * t - droop * t
            cp = base + d * (length * (t - 0.5 * curl * t * t * t * 0.2)) - u * (length * (math.sin(ang) * 0.5 * t))
            sw = side * math.cos(twist * t) + u * math.sin(twist * t)
            ring = [cp + sw * (width * 0.5 * w) + u * (width * fold * 0.5 * w), cp, cp - sw * (width * 0.5 * w) + u * (width * fold * 0.5 * w)]
            rings.append(ring)
        mi = self.use(mat)
        vs = [[bm.verts.new(p) for p in ring] for ring in rings]
        faces = []
        for i in range(seg):
            for j in range(2):
                f = bm.faces.new((vs[i][j], vs[i][j + 1], vs[i + 1][j + 1], vs[i + 1][j]))
                faces.append(f)
                f.smooth = True
                f.material_index = mi
                for l in f.loops:
                    v = l.vert
                    ii = i + (1 if v in (vs[i + 1][j], vs[i + 1][j + 1]) else 0)
                    jj = j + (1 if v in (vs[i][j + 1], vs[i + 1][j + 1]) else 0)
                    l[self.uv].uv = (ii / seg, 1.0 - jj / 2.0)
                    l[self.col] = (rand, rand, rand, 1.0)
        return faces

    # ------------------------------------------------------------ planche / poutre
    def plank(self, c, size, mat, rot=None, bevel=0.006, bow=0.0, seed=0, uv_off=None, warp=0.0, noise_amp=0.0):
        """Planche (L, l, e) avec chanfrein, léger gauchissement ; UV en mètres : u le long de la longueur, v sur la largeur, décalage aléatoire."""
        r = random.Random(seed + 31 * self.seed)
        L, W, T = size
        off = uv_off if uv_off is not None else (r.uniform(0, 5), r.uniform(0, 5))
        nx = max(2, int(L / 0.1))
        ny = 3
        verts_top = []
        bm = self.bm
        mi = self.use(mat)
        M = (rot.to_matrix() if rot is not None else Matrix.Identity(3))

        def P(x, y, z):
            if warp:
                z += warp * math.sin(x * 2.3 + seed) * (y / max(W, 1e-6)) * 0.5
            if bow:
                z += bow * (1 - (2 * x / L) ** 2)
            return V(c) + M @ V((x, y, z))

        faces = []
        # six faces : sommets partagés par face pour des normales franches, chanfrein simulé par deux rangées
        def quad(a, b, c_, d, uvs):
            f = bm.faces.new((bm.verts.new(a), bm.verts.new(b), bm.verts.new(c_), bm.verts.new(d)))
            f.smooth = False
            f.material_index = mi
            for l, uv in zip(f.loops, uvs):
                l[self.uv].uv = (uv[0] + off[0], uv[1] + off[1])
            faces.append(f)
        hx, hy, hz = L / 2, W / 2, T / 2
        b = min(bevel, hy * 0.5, hz * 0.5)
        # dessus (z = +hz) sous-divisé le long de x pour le gauchissement
        xs = [-hx + L * i / nx for i in range(nx + 1)]
        for i in range(nx):
            x0, x1 = xs[i], xs[i + 1]
            quad(P(x0, -hy + b, hz), P(x1, -hy + b, hz), P(x1, hy - b, hz), P(x0, hy - b, hz), [(x0, -hy), (x1, -hy), (x1, hy), (x0, hy)])
            quad(P(x0, -hy, hz - b), P(x1, -hy, hz - b), P(x1, -hy + b, hz), P(x0, -hy + b, hz), [(x0, -hy), (x1, -hy), (x1, -hy), (x0, -hy)])
            quad(P(x0, hy - b, hz), P(x1, hy - b, hz), P(x1, hy, hz - b), P(x0, hy, hz - b), [(x0, hy), (x1, hy), (x1, hy), (x0, hy)])
            quad(P(x0, hy, -hz), P(x1, hy, -hz), P(x1, hy, hz - b), P(x0, hy, hz - b), [(x0, hy), (x1, hy), (x1, hy), (x0, hy)])
            quad(P(x0, -hy, hz - b), P(x1, -hy, hz - b), P(x1, -hy, -hz), P(x0, -hy, -hz), [(x0, -hy), (x1, -hy), (x1, -hy), (x0, -hy)])
            quad(P(x0, -hy, -hz), P(x0, hy, -hz), P(x1, hy, -hz), P(x1, -hy, -hz), [(x0, -hy), (x0, hy), (x1, hy), (x1, -hy)])
        # bouts (grain coupé)
        for sx in (-hx, hx):
            q = [P(sx, -hy, -hz), P(sx, hy, -hz), P(sx, hy, hz - b), P(sx, -hy, hz - b)]
            if sx > 0:
                q = list(reversed(q))
            quad(*q, [(0, 0), (0.1, 0), (0.1, 0.1), (0, 0.1)])
        return faces

    # ------------------------------------------------------------ prisme extrudé (panneaux, pointes de planche)
    def prism(self, poly, y0, y1, mat, rot=None, c=(0, 0, 0), uvscale=1.0, uv_off=(0.0, 0.0)):
        """Prisme : poly = [(x, z)...] dans le plan XZ, de y0 à y1 ; UV en mètres (planche : u le long de x)."""
        bm = self.bm
        mi = self.use(mat)
        M = rot.to_matrix() if rot is not None else Matrix.Identity(3)

        def T(x, y, z):
            return V(c) + M @ V((x, y, z))
        fr = [bm.verts.new(T(x, y0, z)) for x, z in poly]
        bk = [bm.verts.new(T(x, y1, z)) for x, z in poly]
        n = len(poly)
        faces = [bm.faces.new(list(reversed(fr))), bm.faces.new(bk)]
        for i in range(n):
            faces.append(bm.faces.new((fr[i], fr[(i + 1) % n], bk[(i + 1) % n], bk[i])))
        for f in faces:
            f.smooth = False
            f.material_index = mi
            for l in f.loops:
                co = M.inverted() @ (l.vert.co - V(c))
                l[self.uv].uv = (co.x * uvscale + uv_off[0], co.z * uvscale + co.y * 0.5 + uv_off[1])
        return faces

    # ------------------------------------------------------------ cristal hexagonal
    def crystal(self, base, axis, length, radius, mat, taper=0.9, tip=0.28, sides=6, seed=0, twist=0.0, elong=1.0, facet_noise=0.04, sub=2):
        """Prisme hexagonal à terminaison pyramidale (facettes rhomboédriques), rayon variable, bords nets."""
        r = random.Random(seed * 131 + self.seed)
        bm = self.bm
        mi = self.use(mat)
        ax = V(axis).normalized()
        ref = V(0, 0, 1) if abs(ax.z) < 0.9 else V(1, 0, 0)
        e1 = ref.cross(ax).normalized()
        e2 = ax.cross(e1).normalized()
        rot_a = r.uniform(0, 6.28)
        rings = []
        stations = [(0.0, 1.0), (0.45, 0.97), (1.0 - tip, taper), (1.0, 0.0)]
        pw = [r.uniform(0.9, 1.1) for _ in range(sides)]
        for z, k in stations:
            ring = []
            for s in range(sides):
                a = rot_a + 2 * math.pi * s / sides + twist * z
                rr = radius * k * pw[s] * (1.0 if z < 1.0 else 0.0)
                ring.append(V(base) + ax * (length * z) + (e1 * math.cos(a) + e2 * math.sin(a) * elong) * rr)
            rings.append(ring)
        faces = []
        vs = [[bm.verts.new(p) for p in ring] for ring in rings]
        for i in range(len(rings) - 1):
            for j in range(sides):
                j2 = (j + 1) % sides
                quad = [vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]]
                uniq = []
                for v in quad:
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) < 3:
                    continue
                f = bm.faces.new(uniq)
                f.smooth = False
                f.material_index = mi
                for l in f.loops:
                    l[self.uv].uv = (0.0, 0.0)
                faces.append(f)
        cap = bm.faces.new(list(reversed(vs[0])))
        cap.smooth = False
        cap.material_index = mi
        for l in cap.loops:
            l[self.uv].uv = (0.0, 0.0)
        faces.append(cap)
        return faces

    # ------------------------------------------------------------ fin
    def finish(self, extra_sharp=None):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        bm.free()
        for m in self.mats:
            mesh.materials.append(m)
        obj = bpy.data.objects.new(self.name, mesh)
        return obj


def displace_surface(obj, fn):
    """Déplace chaque sommet selon fn(co, normal) -> Vector offset (utile pour l'érosion après coup)."""
    me = obj.data
    me.calc_normals() if hasattr(me, "calc_normals") else None
    for v in me.vertices:
        v.co += fn(v.co.copy(), v.normal.copy())
    me.update()
