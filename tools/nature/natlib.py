"""
Bibliothèque de modélisation « NaturePack » : primitives (blob, tube, lathe, boîte), peinture par atlas, rig de vent.

Tout est UV-mappé sur l'atlas de textures du pack (1024 px) :
    ligne du haut  : palette (aplats 8x6) | dégradé A (8 colonnes) | dégradé B (8 colonnes) | coupe de tronc
    colonnes       : bouleau | écorce sombre | écorce orange | herbe / osier / pierre (3 carrés à droite)
Les couleurs sont donc choisies en pointant une case de la palette ou une colonne de dégradé (clair en haut -> sombre en bas).
"""
import math
import os
import random

import bpy
import bmesh
from mathutils import Vector, Matrix, Quaternion, noise

ATLAS_PNG = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "NaturePack", "high", "nature-atlas-1024.png")

PX = 1.0 / 1024.0
RECTS = {  # (u0, v0, u1, v1), origine en bas à gauche
    "pal": (0, .75, .25, 1), "gradA": (.25, .75, .5, 1), "gradB": (.5, .75, .75, 1), "log": (.75, .75, 1, 1),
    "birch": (0, 0, .25, .75), "bark": (.25, 0, .5, .75), "orange": (.5, 0, .75, .75),
    "grass": (.75, .5, 1, .75), "wicker": (.75, .25, 1, .5), "stone": (.75, 0, 1, .25),
}

# cases de la palette (colonne, ligne) — voir l'atlas
PAL = dict(brown=(0, 0), dkbrown=(1, 0), tan=(2, 0), cream=(3, 0), black=(4, 0), lime=(5, 0), green=(6, 0), dkgreen=(7, 0),
           teal=(0, 1), forest=(1, 1), orange=(2, 1), rust=(3, 1), yellow=(4, 1), pink=(5, 1), palepink=(6, 1), grey=(7, 1),
           stone=(0, 2), dkstone=(1, 2), olive=(2, 2), leaf=(3, 2), red=(4, 2), sun=(5, 2), white=(6, 2), red2=(7, 2),
           sand=(0, 3), violet=(1, 3), moss=(2, 3), wood=(3, 3), green2=(4, 3), rose=(5, 3), crimson=(6, 3), amber=(7, 3),
           bark=(0, 4), taupe=(1, 4), chestnut=(2, 4), sage=(3, 4), beige=(4, 4), ivory=(5, 4), magenta=(6, 4), darkwood=(7, 4),
           purple=(0, 5), fuchsia=(1, 5), ivory2=(2, 5))
GRAD_A = dict(leaf=0, green=1, autumn=2, cherry=3, pine=4, fresh=5, lime=6, olive=7)
GRAD_B = dict(stone=0, earth=1, grass=2, green=3, green2=4, sage=5, deep=6, green3=7)


def pingpong(x):
    x = x % 2.0
    return x if x <= 1 else 2 - x


class Paint:
    """Associe une position / des paramètres de grille à une coordonnée UV de l'atlas."""

    def __init__(self, kind, **kw):
        self.kind = kind
        self.kw = kw

    def __call__(self, co, n, pu, pv):
        k, kw = self.kind, self.kw
        if k == "pal":
            c, r = kw["cell"]
            return ((c + .5) * 32 * PX, 1 - (r + .5) * 32 * PX)
        if k == "grad":
            x0 = RECTS["gradA" if kw["tile"] == "A" else "gradB"][0]
            u = x0 + (kw["col"] + .5) * 32 * PX
            d = kw.get("dir")
            h = co.dot(d) if d is not None else co.z
            t = (h - kw["lo"]) / max(1e-6, kw["hi"] - kw["lo"])
            t = min(1.0, max(0.0, t))
            if kw.get("flip"):
                t = 1 - t
            y = 4 + (1 - t) * 247
            return (u, 1 - y * PX)
        if k == "tex":
            u0, v0, u1, v1 = RECTS[kw["tile"]]
            ins = 5 * PX
            u0 += ins; v0 += ins; u1 -= ins; v1 -= ins
            if pu is None or kw.get("tri"):
                nn = n if n is not None else Vector((0, 0, 1))
                ax = max(range(3), key=lambda i: abs(nn[i]))
                s = kw["su"]
                a, b = [(co.y, co.z), (co.x, co.z), (co.x, co.y)][ax]
                s_, t_ = pingpong(a * s + .31), pingpong(b * kw["sv"] + .17)
            else:
                s_, t_ = pingpong(pu * kw["su"]), pingpong(pv * kw["sv"])
            return (u0 + s_ * (u1 - u0), v0 + t_ * (v1 - v0))
        raise KeyError(k)


def pal(name):
    return Paint("pal", cell=PAL[name])


def grad(tile, name, lo, hi, dir=None, flip=False):
    col = (GRAD_A if tile == "A" else GRAD_B)[name]
    return Paint("grad", tile=tile, col=col, lo=lo, hi=hi, dir=dir, flip=flip)


def tex(tile, su=1.0, sv=1.0, tri=False):
    return Paint("tex", tile=tile, su=su, sv=sv, tri=tri)


QUAL = (1.0, 0.62, 0.4)


def catmull(pts, n):
    """Rééchantillonne une polyligne (r, z) avec une spline de Catmull-Rom (n points par segment)."""
    P = [Vector((a, b)) for a, b in pts]
    out = [P[0]]
    for i in range(len(P) - 1):
        p0, p1, p2, p3 = P[max(0, i - 1)], P[i], P[i + 1], P[min(len(P) - 1, i + 2)]
        for k in range(1, n + 1):
            t = k / n
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            out.append(q)
    return [(max(0.0, q.x), q.y) for q in out]


class B:
    """Constructeur de maillage (un objet = une qualité LOD : 0 haute, 1 moyenne, 2 basse)."""

    def __init__(self, name, q=0, seed=1):
        self.name = name
        self.q = q
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.l_pid = self.bm.verts.layers.int.new("pid")
        self.parts = {}            # nom de chaîne -> dict
        self.part_ids = {}
        self.cur = -1
        self.rnd = random.Random(seed)
        self.seed = seed

    # ---- utilitaires
    def n(self, x, lo=3):
        return max(lo, int(round(x * QUAL[self.q])))

    def sub(self, s):
        return max(1, s - self.q)

    def chain(self, name, base, tip, n=2, parent="racine", names=None, amp=1.0, lag=0.35, phase=None):
        base, tip = Vector(base), Vector(tip)
        if names is None:
            names = [name] if n == 1 else [f"{name}{'abcdefgh'[i]}" for i in range(n)]
        self.parts[name] = dict(names=names, base=base, tip=tip, parent=parent, amp=amp, lag=lag,
                                phase=self.rnd.random() * 6.28 if phase is None else phase)
        self.part_ids[name] = len(self.part_ids)
        return name

    def part(self, name):
        self.cur = self.part_ids[name] if name is not None else -1

    def nearest_part(self, pos, candidates):
        pos = Vector(pos)
        return min(candidates, key=lambda c: (self.parts[c]["tip"] - pos).length)

    # ---- création de faces
    def _finish_faces(self, faces, paint, smooth, center=None):
        for f in faces:
            f.smooth = smooth
            for l in f.loops:
                co = l.vert.co
                nn = (co - center).normalized() if center is not None else f.normal
                l[self.uv].uv = paint(co, nn, None, None)

    def grid(self, rings, paint, closed=True, smooth=True, cap_a=True, cap_b=True, part=None, flipuv=False, cap_log=False):
        """rings : liste d'anneaux (listes de Vector). Les anneaux réduits à un point deviennent des pôles."""
        if part is not None:
            self.part(part)
        bm = self.bm
        m = len(rings)
        nrow = len(rings[0])
        vs = []
        for ring in rings:
            p0 = ring[0]
            if all((p - p0).length < 1e-7 for p in ring):
                v = bm.verts.new(p0)
                v[self.l_pid] = self.cur
                vs.append([v] * nrow)
            else:
                row = []
                for p in ring:
                    v = bm.verts.new(p)
                    v[self.l_pid] = self.cur
                    row.append(v)
                vs.append(row)
        faces = []
        span = nrow if closed else nrow - 1
        for i in range(m - 1):
            for j in range(span):
                j2 = (j + 1) % nrow
                quad = [vs[i][j], vs[i][j2], vs[i + 1][j2], vs[i + 1][j]]
                uniq = []
                for v in quad:
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) < 3:
                    continue
                try:
                    f = bm.faces.new(uniq)
                except ValueError:
                    continue
                f.smooth = smooth
                # uv par sommet (u autour, v le long)
                pu_map = {}
                for l in f.loops:
                    v = l.vert
                    # retrouver (i,j) du sommet dans le quad
                    idx = quad.index(v)
                    ii = i + (1 if idx >= 2 else 0)
                    jj = j if idx in (0, 3) else j + 1
                    pu = jj / (nrow if closed else max(1, nrow - 1))
                    pv = ii / max(1, m - 1)
                    nn = f.normal
                    l[self.uv].uv = paint(v.co, nn, pu, pv)
                faces.append(f)
        if closed:
            for cap, ring_vs, flip in ((cap_a, vs[0], True), (cap_b, vs[-1], False)):
                if not cap:
                    continue
                uniq = []
                for v in ring_vs:
                    if v not in uniq:
                        uniq.append(v)
                if len(uniq) < 3:
                    continue
                f = bm.faces.new(list(reversed(uniq)) if flip else uniq)
                f.smooth = smooth and not cap_log
                if cap_log:
                    c = sum((v.co for v in uniq), Vector()) / len(uniq)
                    R = max((v.co - c).length for v in uniq) or 1e-6
                    e1 = (uniq[0].co - c).normalized()
                    e2 = f.normal.cross(e1)
                    for l in f.loops:
                        d = l.vert.co - c
                        l[self.uv].uv = (0.875 + d.dot(e1) / R * 0.105, 0.875 + d.dot(e2) / R * 0.105)
                else:
                    for l in f.loops:
                        l[self.uv].uv = paint(l.vert.co, f.normal, None, None)
                faces.append(f)
        return faces

    # ---- primitives
    def blob(self, c, r, paint, amp=0.12, freq=1.6, squash=(1, 1, 1), seed=0, sub=3, part=None, smooth=True, rot=None):
        if part is not None:
            self.part(part)
        bm = self.bm
        c = Vector(c)
        res = bmesh.ops.create_icosphere(bm, subdivisions=self.sub(sub), radius=1.0)
        sv = Vector((seed * 7.31, seed * 3.17, seed * 5.53))
        rx, ry, rz = (r * squash[0], r * squash[1], r * squash[2]) if not isinstance(r, (tuple, list)) else r
        faces = set()
        rm = rot.to_matrix() if rot is not None else None
        for v in res["verts"]:
            p = v.co.copy()
            d = noise.noise(p * freq + sv) * 0.7 + noise.noise(p * freq * 2.3 + sv + Vector((9, 1, 4))) * 0.3
            k = 1 + amp * d
            q = Vector((p.x * rx * k, p.y * ry * k, p.z * rz * k))
            if rm is not None:
                q = rm @ q
            v.co = c + q
            v[self.l_pid] = self.cur
            faces.update(v.link_faces)
        for f in faces:
            f.smooth = smooth
            for l in f.loops:
                co = l.vert.co
                nn = (co - c).normalized()
                l[self.uv].uv = paint(co, nn, None, None)
        return list(faces)

    def tube(self, path, radii, paint, sides=8, ex=1.0, cap_a=True, cap_b=True, part=None, smooth=True, closed_top=True, twist=0.0, up=None, cap_log=False):
        """Tube le long d'une polyligne. radii : liste ou fonction(t). ex : aplatissement de la section (largeur x épaisseur)."""
        if part is not None:
            self.part(part)
        path = [Vector(p) for p in path]
        if not callable(radii):
            radii = list(radii)
        if self.q > 0 and len(path) > 4:
            m = max(3, int(round(len(path) * QUAL[self.q])))
            idx = [round(i * (len(path) - 1) / (m - 1)) for i in range(m)]
            if not callable(radii):
                radii = [radii[i] for i in idx]
            path = [path[i] for i in idx]
        n = len(path)
        sides = self.n(sides, 3) if sides > 3 else sides
        rings = []
        T = (path[1] - path[0]).normalized()
        ref = Vector(up) if up is not None else (Vector((0, 1, 0)) if abs(T.y) < 0.9 else Vector((1, 0, 0)))
        Nn = ref.cross(T).normalized()
        Bn = T.cross(Nn).normalized()
        for i, p in enumerate(path):
            if 0 < i < n - 1:
                Tn = (path[i + 1] - path[i - 1]).normalized()
            elif i == 0:
                Tn = (path[1] - path[0]).normalized()
            else:
                Tn = (path[-1] - path[-2]).normalized()
            if i > 0:
                rot = T.rotation_difference(Tn)
                Nn = rot @ Nn
                Bn = rot @ Bn
                T = Tn
            t = i / max(1, n - 1)
            r = radii(t) if callable(radii) else radii[i]
            if isinstance(r, (tuple, list)):
                rx, ry = r
            else:
                rx, ry = r, r / ex
            ang0 = twist * t
            ring = []
            for s in range(sides):
                a = 2 * math.pi * s / sides + ang0
                ring.append(p + Nn * (math.cos(a) * rx) + Bn * (math.sin(a) * ry))
            rings.append(ring)
        return self.grid(rings, paint, smooth=smooth, cap_a=cap_a, cap_b=cap_b, cap_log=cap_log)

    def lathe(self, profile, paint, center=(0, 0, 0), sides=16, mod=None, part=None, smooth=True, tilt=None, spline=0):
        """Solide de révolution autour de l'axe Z. profile : [(rayon, z)...] ; mod(angle, t) -> facteur de rayon."""
        if part is not None:
            self.part(part)
        c = Vector(center)
        sides = self.n(sides, 4) if sides > 4 else sides
        if spline:
            profile = catmull(profile, max(1, int(round(spline * (1.0 if self.q == 0 else 0.6 if self.q == 1 else 0.4)))))
        rings = []
        m = len(profile)
        M = tilt.to_matrix() if tilt is not None else None
        for i, (r, z) in enumerate(profile):
            ring = []
            for s in range(sides):
                a = 2 * math.pi * s / sides
                k = mod(a, i / max(1, m - 1)) if mod else 1.0
                p = Vector((math.cos(a) * r * k, math.sin(a) * r * k, z))
                if M is not None:
                    p = M @ p
                ring.append(c + p)
            rings.append(ring)
        return self.grid(rings, paint, smooth=smooth, cap_a=True, cap_b=True)

    def box(self, c, size, paint, rot=None, smooth=False, bevel=0.0, part=None):
        if part is not None:
            self.part(part)
        bm = self.bm
        res = bmesh.ops.create_cube(bm, size=1.0)
        M = Matrix.Diagonal(Vector((size[0], size[1], size[2], 1.0)))
        if rot is not None:
            M = rot.to_matrix().to_4x4() @ M
        M = Matrix.Translation(Vector(c)) @ M
        for v in res["verts"]:
            v.co = M @ v.co
            v[self.l_pid] = self.cur
        faces = set()
        for v in res["verts"]:
            faces.update(v.link_faces)
        for f in faces:
            f.smooth = smooth
            for l in f.loops:
                l[self.uv].uv = paint(l.vert.co, f.normal, None, None)
        return list(faces)

    def prism(self, poly, y0, y1, paint, part=None, smooth=False, rot=None, c=(0, 0, 0)):
        """Prisme extrudé : poly = [(x, z)...] dans le plan XZ, de y0 à y1 (planches, panneaux...)."""
        if part is not None:
            self.part(part)
        bm = self.bm
        M = rot.to_matrix() if rot is not None else None
        def T(x, y, z):
            p = Vector((x, y, z))
            if M is not None:
                p = M @ p
            return p + Vector(c)
        fr = [bm.verts.new(T(x, y0, z)) for x, z in poly]
        bk = [bm.verts.new(T(x, y1, z)) for x, z in poly]
        for v in fr + bk:
            v[self.l_pid] = self.cur
        n = len(poly)
        faces = [bm.faces.new(list(reversed(fr))), bm.faces.new(bk)]
        for i in range(n):
            faces.append(bm.faces.new((fr[i], fr[(i + 1) % n], bk[(i + 1) % n], bk[i])))
        for f in faces:
            f.smooth = smooth
            for l in f.loops:
                l[self.uv].uv = paint(l.vert.co, f.normal, None, None)
        return faces

    def finish(self, material, rig_name=None):
        bm = self.bm
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        mesh = bpy.data.meshes.new(self.name)
        bm.to_mesh(mesh)
        # faces lisses = attribut ; arêtes vives gérées par sharp_face
        pid_layer = None
        pids = [v[self.l_pid] for v in bm.verts]
        pos = [v.co.copy() for v in bm.verts]
        bm.free()
        mesh.materials.append(material)
        obj = bpy.data.objects.new(self.name, mesh)
        # groupes de sommets
        if self.parts:
            names = ["racine"] + [nm for p in self.parts.values() for nm in p["names"]]
            vgs = {nm: obj.vertex_groups.new(name=nm) for nm in names}
            pname = {i: k for k, i in self.part_ids.items()}
            for vi, (pid, co) in enumerate(zip(pids, pos)):
                if pid < 0:
                    vgs["racine"].add([vi], 1.0, "REPLACE")
                    continue
                p = self.parts[pname[pid]]
                dvec = p["tip"] - p["base"]
                L = dvec.length
                t = min(1.0, max(0.0, (co - p["base"]).dot(dvec) / (L * L))) if L > 1e-6 else 0.0
                k = len(p["names"])
                ws = [max(0.0, 1 - abs(t * k - (i + .5))) for i in range(k)]
                tot = sum(ws) or 1.0
                for nm, w in zip(p["names"], ws):
                    if w > 1e-4:
                        vgs[nm].add([vi], w / tot, "REPLACE")
        return obj

    # ---- armature + vent
    def make_rig(self, obj, rig_name, collection, wind=1.0):
        if not self.parts:
            return None
        arm = bpy.data.armatures.new(rig_name)
        rig = bpy.data.objects.new(rig_name, arm)
        collection.objects.link(rig)
        bpy.context.view_layer.objects.active = rig
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        rig.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        eb = arm.edit_bones
        root = eb.new("racine"); root.head = (0, 0, 0); root.tail = (0, 0, 0.25)
        order = []
        for pname, p in self.parts.items():
            k = len(p["names"])
            prev = eb.get(p["parent"]) if p["parent"] != "racine" else root
            if prev is None:   # parent défini plus tard (chaîne de branche) -> racine
                prev = root
            for i, nm in enumerate(p["names"]):
                b = eb.new(nm)
                b.head = p["base"].lerp(p["tip"], i / k)
                b.tail = p["base"].lerp(p["tip"], (i + 1) / k)
                if (b.tail - b.head).length < 1e-4:
                    b.tail = b.head + Vector((0, 0, 0.01))
                b.parent = prev
                prev = b
                order.append((nm, pname, i))
        # resolution des parents de chaînes (parent = nom d'os existant, ex. tronc2)
        for pname, p in self.parts.items():
            if p["parent"] != "racine" and eb.get(p["parent"]) is not None:
                eb[p["names"][0]].parent = eb[p["parent"]]
        bpy.ops.object.mode_set(mode="OBJECT")
        # modificateur + parentage
        obj.parent = rig
        md = obj.modifiers.new("Armature", "ARMATURE"); md.object = rig
        # animation de vent (boucle de 120 images, clés toutes les 5 images)
        for pb in rig.pose.bones:
            pb.rotation_mode = "QUATERNION"
        for nm, pname, i in order:
            p = self.parts[pname]
            pb = rig.pose.bones[nm]
            a0 = 0.010 * p["amp"] * wind
            amp = a0 * (1 + 1.4 * i)
            ph = p["phase"] - i * p["lag"]
            for f in range(0, 121, 5):
                s = math.sin(2 * math.pi * f / 120 + ph)
                x = amp * (0.62 + 0.38 * s)
                y = amp * 0.18 * math.sin(2 * math.pi * f / 120 + ph + 1.1)
                z = -0.28 * x
                q = Quaternion((math.sqrt(max(0.0, 1 - x * x - y * y - z * z)), x, y, z))
                pb.rotation_quaternion = q
                pb.keyframe_insert("rotation_quaternion", frame=f)
        rig.animation_data.action.name = f"{rig_name}-vent"
        return rig
