"""
Matériaux procéduraux RÉALISTES (Cycles) pour le NaturePack réaliste : roche, écorces, bois, mousse, feuillage, améthyste, feu, sols.
Aucune image : tout est généré par nœuds (textures « maison »). Coordonnées :
 - objets « libres » (roche, sol)  -> coordonnées Objet (triplanaires, pas d'UV)
 - troncs / bûches / branches      -> UV cylindriques (u = angle 0..1, v = longueur en m) transformées en coordonnées 3D sans couture
 - planches / feuilles             -> UV en mètres
"""
import math

import bpy


def lin(c):
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3])


def L(c):
    return lin(c) + (1.0,)


class M:
    """Constructeur de nœuds : toutes les méthodes renvoient le nœud ; n.outputs[...] pour brancher."""

    def __init__(self, name, principled=True):
        self.m = bpy.data.materials.new(name)
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = None
        if principled:
            self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
            self.nt.links.new(self.bsdf.outputs["BSDF"], self.out.inputs["Surface"])
        self._n = 0

    # --- briques
    def N(self, kind, props=None, **inp):
        node = self.nt.nodes.new(kind)
        node.location = (-300 * (self._n % 8), -200 * (self._n // 8))
        self._n += 1
        for k, v in (props or {}).items():
            setattr(node, k, v)
        for k, v in inp.items():
            self.set(node, k.replace("_", " "), v)
        return node

    def set(self, node, name, v):
        s = node.inputs[name] if isinstance(name, str) else node.inputs[name]
        if isinstance(v, bpy.types.NodeSocket):
            self.nt.links.new(v, s)
        elif isinstance(v, bpy.types.Node):
            self.nt.links.new(v.outputs[0], s)
        else:
            try:
                s.default_value = v
            except TypeError:
                s.default_value = tuple(v)

    def to(self, src, node, name):
        self.set(node, name, src)

    def math(self, op, a=None, b=None, c=None, clamp=False):
        n = self.N("ShaderNodeMath", props=dict(operation=op, use_clamp=clamp))
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.set(n, i, v)
        return n.outputs[0]

    def vmath(self, op, a, b=None):
        n = self.N("ShaderNodeVectorMath", props=dict(operation=op))
        self.set(n, 0, a)
        if b is not None:
            self.set(n, 1, b)
        return n

    def mix(self, fac, a, b, blend="MIX"):
        n = self.N("ShaderNodeMix", props=dict(data_type="RGBA", blend_type=blend))
        self.set(n, "Factor", fac)
        self.set(n, "A", a if isinstance(a, (bpy.types.NodeSocket, bpy.types.Node)) else tuple(a) + ((1.0,) if len(a) == 3 else ()))
        self.set(n, "B", b if isinstance(b, (bpy.types.NodeSocket, bpy.types.Node)) else tuple(b) + ((1.0,) if len(b) == 3 else ()))
        return n.outputs["Result"]

    def ramp(self, fac, stops, interp="LINEAR"):
        r = self.N("ShaderNodeValToRGB")
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) > len(stops):
            els.remove(els[-1])
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = tuple(col) + ((1.0,) if len(col) == 3 else ())
        self.set(r, "Fac", fac)
        return r.outputs["Color"]

    def map_range(self, v, a0, a1, b0=0.0, b1=1.0, clamp=True):
        n = self.N("ShaderNodeMapRange", props=dict(clamp=clamp))
        self.set(n, "Value", v); self.set(n, "From Min", a0); self.set(n, "From Max", a1); self.set(n, "To Min", b0); self.set(n, "To Max", b1)
        return n.outputs["Result"]

    def noise(self, vec, scale, detail=5.0, rough=0.55, dist=0.0, w=None):
        n = self.N("ShaderNodeTexNoise", props=dict(noise_dimensions="3D" if w is None else "4D"))
        self.set(n, "Vector", vec); self.set(n, "Scale", scale); self.set(n, "Detail", detail); self.set(n, "Roughness", rough); self.set(n, "Distortion", dist)
        if w is not None:
            self.set(n, "W", w)
        return n.outputs["Fac"]

    def voronoi(self, vec, scale, feature="F1", out="Distance", rand=1.0, w=None):
        n = self.N("ShaderNodeTexVoronoi", props=dict(voronoi_dimensions="3D" if w is None else "4D", feature=feature))
        self.set(n, "Vector", vec); self.set(n, "Scale", scale); self.set(n, "Randomness", rand)
        if w is not None:
            self.set(n, "W", w)
        return n.outputs[out]

    def wave(self, vec, scale, dist=0.0, detail=2.0, kind="BANDS", direction="X", profile="SIN"):
        n = self.N("ShaderNodeTexWave", props=dict(wave_type=kind, bands_direction=direction, rings_direction=direction, wave_profile=profile))
        self.set(n, "Vector", vec); self.set(n, "Scale", scale); self.set(n, "Distortion", dist); self.set(n, "Detail", detail)
        return n.outputs["Fac"]

    def mapping(self, vec, scale=(1, 1, 1), loc=(0, 0, 0), rot=(0, 0, 0)):
        n = self.N("ShaderNodeMapping")
        self.set(n, "Vector", vec); self.set(n, "Scale", scale); self.set(n, "Location", loc); self.set(n, "Rotation", rot)
        return n.outputs["Vector"]

    def sep(self, vec):
        n = self.N("ShaderNodeSeparateXYZ")
        self.set(n, "Vector", vec)
        return n.outputs["X"], n.outputs["Y"], n.outputs["Z"]

    def comb(self, x, y, z):
        n = self.N("ShaderNodeCombineXYZ")
        self.set(n, "X", x); self.set(n, "Y", y); self.set(n, "Z", z)
        return n.outputs["Vector"]

    def texcoord(self, which="Object"):
        n = self.N("ShaderNodeTexCoord")
        return n.outputs[which]

    def attr(self, name, kind="GEOMETRY"):
        n = self.N("ShaderNodeAttribute", props=dict(attribute_name=name, attribute_type=kind))
        return n

    def uv(self):
        n = self.N("ShaderNodeUVMap")
        return n.outputs["UV"]

    def cyl(self, k=1.0, vscale=1.0, voff=0.0):
        """UV (u = angle, v = longueur m) -> vecteur 3D sans couture : (cos·k, sin·k, v·vscale)."""
        x, y, _ = self.sep(self.uv())
        ang = self.math("MULTIPLY", x, 2 * math.pi)
        c = self.math("MULTIPLY", self.math("COSINE", ang), k)
        s = self.math("MULTIPLY", self.math("SINE", ang), k)
        v = self.math("ADD", self.math("MULTIPLY", y, vscale), voff)
        return self.comb(c, s, v)

    def bump(self, height, strength=0.5, dist=0.02, invert=False, normal=None):
        n = self.N("ShaderNodeBump", props=dict(invert=invert))
        self.set(n, "Height", height); self.set(n, "Strength", strength); self.set(n, "Distance", dist)
        if normal is not None:
            self.set(n, "Normal", normal)
        return n.outputs["Normal"]

    def geom(self):
        return self.N("ShaderNodeNewGeometry")

    def finish(self, base=None, rough=None, normal=None, extra=None):
        b = self.bsdf
        if base is not None:
            self.set(b, "Base Color", base)
        if rough is not None:
            self.set(b, "Roughness", rough)
        if normal is not None:
            self.set(b, "Normal", normal)
        for k, v in (extra or {}).items():
            self.set(b, k, v)
        return self.m


# =========================================================== ROCHE
def rock(name, dark, mid, light, strata=0.0, strata_freq=3.0, crack=0.5, moss=0.0, lichen=0.0, scale=1.0, grain=1.0, wet=0.0, warm=None):
    """Roche : couleurs par grands nuages, strates, fissures (distance à l'arête de Voronoï), grain fin, arêtes claires (pointiness), mousse sur les faces horizontales."""
    m = M(name)
    dark, mid, light = L(dark), L(mid), L(light)
    co = m.texcoord("Object")
    p = m.mapping(co, scale=(scale,) * 3)
    n1 = m.noise(p, 1.3, 6, 0.55)
    n2 = m.noise(p, 7.0, 8, 0.62)
    n3 = m.noise(p, 38.0, 10, 0.6)
    tone = m.ramp(n1, [(0.30, dark), (0.5, mid), (0.72, mid)])
    tone = m.mix(m.ramp(n2, [(0.45, (0, 0, 0)), (0.75, (1, 1, 1))]), tone, light)
    h = m.math("ADD", m.math("MULTIPLY", n3, 0.55 * grain), m.math("MULTIPLY", n2, 0.45))
    if strata > 0:
        _, _, z = m.sep(p)
        warp = m.math("MULTIPLY", n1, 0.9)
        band = m.math("SINE", m.math("MULTIPLY", m.math("ADD", z, warp), strata_freq * 2 * math.pi))
        band2 = m.math("SINE", m.math("MULTIPLY", m.math("ADD", z, m.math("MULTIPLY", n2, 0.25)), strata_freq * 5.3 * math.pi))
        sb = m.ramp(m.math("ADD", m.math("MULTIPLY", band, 0.5), 0.5), [(0.0, (0.0, 0.0, 0.0)), (1.0, (1.0, 1.0, 1.0))])
        tone = m.mix(m.math("MULTIPLY", sb, strata * 0.6), tone, dark)
        tone = m.mix(m.math("MULTIPLY", m.math("MAXIMUM", band2, 0.0), strata * 0.25), tone, light)
        h = m.math("ADD", h, m.math("MULTIPLY", band, 0.22 * strata))
    if crack > 0:
        e = m.voronoi(m.mapping(p, scale=(1, 1, 1)), 2.4, "DISTANCE_TO_EDGE", "Distance")
        line = m.ramp(e, [(0.0, (1, 1, 1)), (0.045, (0, 0, 0))])
        tone = m.mix(m.math("MULTIPLY", line, crack * 0.8), tone, (0.01, 0.01, 0.01))
        h = m.math("SUBTRACT", h, m.math("MULTIPLY", line, 0.5 * crack))
    g = m.geom()
    pt = m.ramp(g.outputs["Pointiness"], [(0.48, (0, 0, 0)), (0.66, (1, 1, 1))])
    tone = m.mix(m.math("MULTIPLY", pt, 0.35), tone, light)
    if lichen > 0:
        ln = m.noise(m.mapping(p, scale=(2.2,) * 3, loc=(9, 3, 1)), 3.0, 6, 0.65)
        lmask = m.ramp(ln, [(0.56, (0, 0, 0)), (0.62, (1, 1, 1))])
        lc = m.mix(m.noise(p, 25, 4), L((0.72, 0.74, 0.46)), L((0.86, 0.83, 0.6)))
        tone = m.mix(m.math("MULTIPLY", lmask, lichen), tone, lc)
    rough = m.math("ADD", 0.72 - 0.35 * wet, m.math("MULTIPLY", n3, 0.18))
    if moss > 0:
        gn = m.N("ShaderNodeNewGeometry")
        # normale en espace monde (z) : faces tournées vers le haut
        vt = m.N("ShaderNodeVectorTransform", props=dict(vector_type="NORMAL", convert_from="OBJECT", convert_to="WORLD"))
        m.set(vt, "Vector", gn.outputs["Normal"])
        _, _, nz = m.sep(vt.outputs["Vector"])
        mn = m.noise(m.mapping(p, scale=(1.6,) * 3, loc=(4, 8, 2)), 2.2, 7, 0.6)
        ms = m.math("ADD", m.math("MULTIPLY", nz, 0.9), m.math("MULTIPLY", mn, 1.1))
        mmask = m.ramp(ms, [(1.95 - moss * 1.15, (0, 0, 0)), (2.3 - moss * 1.15, (1, 1, 1))])
        mcol = m.mix(m.noise(m.mapping(p, scale=(1, 1, 1)), 60, 5), L((0.07, 0.17, 0.03)), L((0.20, 0.34, 0.07)))
        tone = m.mix(mmask, tone, mcol)
        rough = m.math("ADD", rough, m.math("MULTIPLY", mmask, 0.2))
        h = m.math("ADD", h, m.math("MULTIPLY", m.math("MULTIPLY", mmask, m.noise(p, 120, 3)), 0.5))
    nrm = m.bump(h, 0.9, 0.03)
    return m.finish(tone, rough, nrm, {"Specular IOR Level": 0.35})


# =========================================================== ÉCORCES
def bark(name, kind="furrowed", dark=(0.07, 0.05, 0.04), mid=(0.24, 0.18, 0.13), light=(0.42, 0.34, 0.26), around=3.0, along=0.35, moss=0.0, scale=1.0, lichen=0.0):
    """Écorce sur UV cylindriques. kind : furrowed (sillons verticaux), smooth (peau lisse à plis), scaly (écailles), plates (plaques)."""
    m = M(name)
    dark, mid, light = L(dark), L(mid), L(light)
    vec = m.cyl(around, along)
    n1 = m.noise(vec, 3.2 * scale, 6, 0.55, 0.3)
    n2 = m.noise(vec, 16 * scale, 8, 0.6)
    n3 = m.noise(vec, 70 * scale, 8, 0.6)
    if kind == "furrowed":
        r = m.noise(vec, 5 * scale, 4, 0.5, 1.4)
        ridge = m.ramp(r, [(0.30, (0, 0, 0)), (0.62, (1, 1, 1))])
        height = m.math("ADD", m.math("MULTIPLY", ridge, 1.0), m.math("MULTIPLY", n2, 0.35))
        tone = m.mix(ridge, dark, m.mix(n2, mid, light))
    elif kind == "smooth":
        # peau lisse de baobab : plis horizontaux irréguliers + fines crevasses verticales
        hz = m.noise(m.mapping(vec, scale=(0.9, 0.9, 5.0)), 1.1 * scale, 3, 0.5, 0.6)
        hr = m.math("SUBTRACT", 1.0, m.math("ABSOLUTE", m.math("SUBTRACT", m.math("MULTIPLY", hz, 2.0), 1.0)))
        vt = m.noise(m.mapping(vec, scale=(2.4, 2.4, 0.5)), 3.0 * scale, 4, 0.55, 0.6)
        vr = m.math("SUBTRACT", 1.0, m.math("ABSOLUTE", m.math("SUBTRACT", m.math("MULTIPLY", vt, 2.0), 1.0)))
        fh = m.math("ADD", m.math("MULTIPLY", m.math("POWER", hr, 3.5), 0.55), m.math("MULTIPLY", m.math("POWER", vr, 7.0), 0.1))
        height = m.math("ADD", fh, m.math("MULTIPLY", n2, 0.35))
        tone = m.mix(m.math("MULTIPLY", fh, 0.9), m.mix(n1, mid, light), dark)
        tone = m.mix(m.ramp(n3, [(0.5, (0, 0, 0)), (0.72, (0.3, 0.3, 0.3))]), tone, dark)
        ridge = fh
    elif kind == "scaly":
        v = m.voronoi(m.mapping(vec, scale=(1, 1, 0.45)), 14 * scale, "F1", "Distance")
        cell = m.ramp(v, [(0.0, (1, 1, 1)), (0.55, (0, 0, 0))])
        edge = m.voronoi(m.mapping(vec, scale=(1, 1, 0.45)), 14 * scale, "DISTANCE_TO_EDGE", "Distance")
        gap = m.ramp(edge, [(0.0, (0, 0, 0)), (0.07, (1, 1, 1))])
        height = m.math("ADD", m.math("MULTIPLY", gap, 0.8), m.math("MULTIPLY", n2, 0.3))
        tone = m.mix(gap, dark, m.mix(m.math("MULTIPLY", cell, 0.7), mid, light))
        ridge = gap
    else:  # plates
        edge = m.voronoi(m.mapping(vec, scale=(1, 1, 0.3)), 6 * scale, "DISTANCE_TO_EDGE", "Distance")
        gap = m.ramp(edge, [(0.0, (0, 0, 0)), (0.12, (1, 1, 1))])
        height = m.math("ADD", m.math("MULTIPLY", gap, 1.0), m.math("MULTIPLY", n2, 0.4))
        tone = m.mix(gap, dark, m.mix(n1, mid, light))
        ridge = gap
    tone = m.mix(m.ramp(n3, [(0.45, (0, 0, 0)), (0.75, (0.5, 0.5, 0.5))]), tone, light)
    rough = m.math("ADD", 0.78, m.math("MULTIPLY", n3, 0.2))
    if moss > 0:
        gn = m.N("ShaderNodeNewGeometry")
        vt = m.N("ShaderNodeVectorTransform", props=dict(vector_type="NORMAL", convert_from="OBJECT", convert_to="WORLD"))
        m.set(vt, "Vector", gn.outputs["Normal"])
        mn = m.noise(m.N("ShaderNodeTexCoord").outputs["Object"], 2.5, 6, 0.6)
        _, _, nz = m.sep(vt.outputs["Vector"])
        _, _, zz = m.sep(m.N("ShaderNodeTexCoord").outputs["Object"])
        ms = m.math("ADD", m.math("MULTIPLY", mn, 1.5), m.math("SUBTRACT", 0.35, m.math("MULTIPLY", zz, 0.35)))
        ms = m.math("ADD", ms, m.math("MULTIPLY", nz, 0.3))
        mm = m.ramp(ms, [(0.95 - moss * 0.5, (0, 0, 0)), (1.2 - moss * 0.45, (1, 1, 1))])
        mcol = m.mix(m.noise(vec, 80, 5), L((0.06, 0.15, 0.03)), L((0.18, 0.30, 0.06)))
        tone = m.mix(mm, tone, mcol)
        height = m.math("ADD", height, m.math("MULTIPLY", mm, 0.3))
        rough = m.math("ADD", rough, m.math("MULTIPLY", mm, 0.15))
    if lichen > 0:
        ln = m.noise(vec, 9, 6, 0.65)
        lm = m.ramp(ln, [(0.6, (0, 0, 0)), (0.66, (1, 1, 1))])
        tone = m.mix(m.math("MULTIPLY", lm, lichen), tone, L((0.70, 0.74, 0.5)))
    nrm = m.bump(height, 1.0, 0.025)
    return m.finish(tone, rough, nrm, {"Specular IOR Level": 0.25})


def birch_bark(name="BirchBark"):
    """Écorce de bouleau : papier blanc crème, lenticelles = traits noirs HORIZONTAUX de tailles variées, bandes grises, fines rides."""
    m = M(name)
    base_n = m.noise(m.cyl(1.0, 2.0), 2.4, 6, 0.55)
    paper = m.mix(base_n, L((0.76, 0.73, 0.65)), L((0.92, 0.90, 0.83)))
    grey = m.ramp(m.noise(m.cyl(0.7, 1.4), 2.0, 5, 0.55), [(0.55, (0, 0, 0)), (0.8, (0.6, 0.6, 0.6))])
    col = m.mix(grey, paper, L((0.40, 0.37, 0.32)))
    # lenticelles : peu de variation autour (rayon petit), beaucoup le long -> traits horizontaux
    big = m.noise(m.cyl(0.32, 26.0), 2.0, 3, 0.6, 0.7)
    mark = m.ramp(big, [(0.60, (0, 0, 0)), (0.68, (1, 1, 1))])
    small = m.noise(m.cyl(0.55, 70.0), 2.2, 2, 0.5, 0.4)
    mark2 = m.ramp(small, [(0.64, (0, 0, 0)), (0.72, (1, 1, 1))])
    col = m.mix(m.math("MULTIPLY", mark, 0.95), col, L((0.025, 0.02, 0.018)))
    col = m.mix(m.math("MULTIPLY", mark2, 0.8), col, L((0.06, 0.05, 0.045)))
    fine = m.noise(m.cyl(2.0, 60.0), 12, 6, 0.6)
    rid = m.wave(m.comb(0.0, 0.0, m.math("MULTIPLY", m.sep(m.cyl(1.0, 1.0))[2], 1.0)), 9.0, 2.5, 3.0, "BANDS", "Z")
    h = m.math("ADD", m.math("MULTIPLY", fine, 0.6), m.math("MULTIPLY", m.math("ADD", m.math("MULTIPLY", rid, 0.5), 0.5), 0.25))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", mark, 0.7))
    nrm = m.bump(h, 0.9, 0.012)
    rough = m.math("ADD", 0.5, m.math("MULTIPLY", fine, 0.3))
    return m.finish(col, rough, nrm, {"Specular IOR Level": 0.45, "Subsurface Weight": 0.08, "Subsurface Radius": (0.25, 0.18, 0.1)})


def end_grain(name, light=(0.80, 0.66, 0.46), dark=(0.52, 0.36, 0.20), bark_ring=(0.35, 0.28, 0.2), rings=26.0, cracks=0.8):
    """Face coupée d'un rondin : cernes de croissance, rayons, fentes de séchage. Les UV de la face = disque centré en (0.5, 0.5) (voir cap_disc)."""
    m = M(name)
    light, dark = L(light), L(dark)
    uvc = m.uv()
    x, y, _ = m.sep(uvc)
    cx = m.math("SUBTRACT", x, 0.5)
    cy = m.math("SUBTRACT", y, 0.5)
    r = m.math("POWER", m.math("ADD", m.math("MULTIPLY", cx, cx), m.math("MULTIPLY", cy, cy)), 0.5)
    ang = m.math("ARCTAN2", cy, cx)
    dis = m.noise(m.comb(cx, cy, 0.0), 6.0, 4, 0.5)
    rr = m.math("ADD", r, m.math("MULTIPLY", m.math("SUBTRACT", dis, 0.5), 0.05))
    rings_f = m.math("ADD", m.math("MULTIPLY", m.math("SINE", m.math("MULTIPLY", rr, rings * 2 * math.pi)), 0.5), 0.5)
    wood = m.mix(m.ramp(rings_f, [(0.15, (0, 0, 0)), (0.85, (1, 1, 1))]), light, dark)
    # rayons médullaires (étoile fine) et fentes radiales
    rays = m.noise(m.comb(m.math("MULTIPLY", ang, 4.0), 0.0, 0.0), 30.0, 2, 0.5)
    wood = m.mix(m.ramp(rays, [(0.5, (0, 0, 0)), (0.75, (0.18, 0.18, 0.18))]), wood, dark)
    cr = m.noise(m.comb(m.math("MULTIPLY", ang, 1.3), m.math("MULTIPLY", r, 3.0), 0.0), 14.0, 2, 0.5, 0.2)
    crack = m.ramp(cr, [(0.6, (0, 0, 0)), (0.64, (1, 1, 1))])
    cmask = m.math("MULTIPLY", crack, m.map_range(r, 0.04, 0.22))
    wood = m.mix(m.math("MULTIPLY", cmask, cracks), wood, L((0.06, 0.04, 0.03)))
    edge = m.map_range(r, 0.44, 0.49)
    wood = m.mix(edge, wood, L(bark_ring))
    h = m.math("ADD", m.math("MULTIPLY", rings_f, 0.2), m.math("MULTIPLY", crack, -0.6))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", cmask, 0.6))
    nrm = m.bump(h, 0.7, 0.006)
    return m.finish(wood, 0.62, nrm, {"Specular IOR Level": 0.3})


# =========================================================== BOIS
def plank_wood(name, tone=((0.12, 0.085, 0.06), (0.36, 0.26, 0.17), (0.55, 0.43, 0.30)), gray=0.5, cracks=0.8, rough=0.78, grain=1.0):
    """Bois de planche sur UV en mètres (u le long de la fibre). Bois patiné : veinage, pores, fentes, grisaillement."""
    m = M(name)
    d, mid, l = [L(t) for t in tone]
    ux, uy, _ = m.sep(m.uv())
    vec = m.comb(ux, uy, 0.0)
    along = m.mapping(vec, scale=(0.12, 5.0 * grain, 1.0))          # étiré le long de u (la fibre)
    warp = m.noise(m.mapping(vec, scale=(0.4, 1.5, 1.0)), 1.8, 4, 0.5)
    band = m.wave(m.comb(m.math("MULTIPLY", ux, 0.12), m.math("ADD", m.math("MULTIPLY", uy, 1.0), m.math("MULTIPLY", warp, 0.5)), 0.0), 6.0 * grain, 3.0, 3.0, "BANDS", "Y")
    bandn = m.math("ADD", m.math("MULTIPLY", band, 0.5), 0.5)
    n_f = m.noise(along, 14.0, 8, 0.62)
    tone_c = m.mix(bandn, mid, d)
    tone_c = m.mix(m.ramp(n_f, [(0.35, (0, 0, 0)), (0.78, (1, 1, 1))]), tone_c, l)
    cr = m.voronoi(m.mapping(vec, scale=(0.1, 2.4, 1.0)), 4.5, "DISTANCE_TO_EDGE", "Distance")
    crack = m.ramp(cr, [(0.0, (1, 1, 1)), (0.035, (0, 0, 0))])
    crack = m.math("MULTIPLY", crack, m.map_range(m.noise(m.mapping(vec, scale=(0.3, 1.0, 1.0)), 2.0, 2), 0.42, 0.62))
    tone_c = m.mix(m.math("MULTIPLY", crack, cracks), tone_c, L((0.012, 0.01, 0.008)))
    gray_c = m.mix(m.noise(along, 30, 5), L((0.38, 0.36, 0.33)), L((0.55, 0.53, 0.50)))
    gmask = m.ramp(m.noise(vec, 1.2, 3, 0.5), [(0.25, (0, 0, 0)), (0.75, (1, 1, 1))])
    tone_c = m.mix(m.math("MULTIPLY", gmask, gray * 0.85), tone_c, gray_c)
    h = m.math("ADD", m.math("MULTIPLY", n_f, 0.4), m.math("MULTIPLY", bandn, 0.45))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", crack, 0.6 * cracks))
    nrm = m.bump(h, 0.8, 0.008)
    r = m.math("ADD", rough, m.math("MULTIPLY", n_f, 0.15))
    return m.finish(tone_c, r, nrm, {"Specular IOR Level": 0.18})


def moss(name="Moss"):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 90.0, 6, 0.65)
    n2 = m.noise(p, 9.0, 4, 0.5)
    col = m.mix(n, L((0.06, 0.14, 0.03)), L((0.22, 0.36, 0.08)))
    col = m.mix(m.ramp(n2, [(0.4, (0, 0, 0)), (0.7, (1, 1, 1))]), col, L((0.30, 0.42, 0.10)))
    nrm = m.bump(n, 1.0, 0.01)
    return m.finish(col, 0.9, nrm, {"Subsurface Weight": 0.1, "Subsurface Radius": (0.2, 0.3, 0.05)})


def rope(name="Rope", color=(0.62, 0.50, 0.32)):
    m = M(name)
    vec = m.cyl(1.0, 1.0)
    st = m.wave(m.mapping(vec, scale=(1, 1, 1)), 90.0, 2.0, 1.0, "BANDS", "Z", "SAW")
    n = m.noise(vec, 160, 5, 0.6)
    col = m.mix(m.math("ADD", m.math("MULTIPLY", st, 0.6), m.math("MULTIPLY", n, 0.4)), L(tuple(c * 0.45 for c in color)), L(color))
    nrm = m.bump(m.math("ADD", st, n), 0.9, 0.003)
    return m.finish(col, 0.92, nrm)


def iron(name="Iron", color=(0.12, 0.12, 0.13)):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 60, 6)
    col = m.mix(m.ramp(m.noise(p, 12, 5), [(0.4, (0, 0, 0)), (0.7, (1, 1, 1))]), L(color), L((0.3, 0.13, 0.05)))
    nrm = m.bump(n, 0.5, 0.004)
    return m.finish(col, m.math("ADD", 0.45, m.math("MULTIPLY", n, 0.3)), nrm, {"Metallic": 0.85})


# =========================================================== SOLS
def ground(name, kind="grass"):
    m = M(name)
    p = m.texcoord("Object")
    if kind == "grass":
        a = m.noise(p, 0.35, 5)
        b = m.noise(p, 40, 5, 0.6)
        c = m.noise(p, 400, 4)
        col = m.mix(a, L((0.10, 0.17, 0.045)), L((0.24, 0.30, 0.085)))
        col = m.mix(b, col, L((0.30, 0.36, 0.11)))
        col = m.mix(m.ramp(m.noise(p, 3, 4), [(0.6, (0, 0, 0)), (0.78, (0.55, 0.55, 0.55))]), col, L((0.33, 0.27, 0.12)))
        nrm = m.bump(m.math("ADD", b, c), 1.0, 0.03)
        return m.finish(col, 0.95, nrm, {"Specular IOR Level": 0.12})
    if kind == "dirt":
        a = m.noise(p, 1.0, 6)
        b = m.noise(p, 60, 6, 0.6)
        col = m.mix(a, L((0.13, 0.08, 0.05)), L((0.28, 0.20, 0.13)))
        col = m.mix(m.ramp(b, [(0.4, (0, 0, 0)), (0.7, (1, 1, 1))]), col, L((0.4, 0.32, 0.24)))
        nrm = m.bump(m.math("ADD", b, m.noise(p, 300, 3)), 1.0, 0.02)
        return m.finish(col, 0.96, nrm, {"Specular IOR Level": 0.1})
    if kind == "sand":
        a = m.noise(p, 0.7, 4)
        rip = m.wave(m.mapping(p, scale=(1, 0.5, 1)), 14.0, 6.0, 2.0, "BANDS", "X")
        col = m.mix(a, L((0.46, 0.35, 0.21)), L((0.66, 0.52, 0.33)))
        col = m.mix(m.math("MULTIPLY", rip, 0.12), col, L((0.45, 0.35, 0.2)))
        g = m.noise(p, 800, 2)
        nrm = m.bump(m.math("ADD", m.math("MULTIPLY", rip, 0.4), m.math("MULTIPLY", g, 0.2)), 0.8, 0.01)
        return m.finish(col, 0.92, nrm, {"Specular IOR Level": 0.15})
    if kind == "snow":
        a = m.noise(p, 0.5, 4)
        col = m.mix(a, L((0.80, 0.86, 0.95)), L((0.96, 0.98, 1.0)))
        nrm = m.bump(m.noise(p, 90, 5), 0.5, 0.02)
        return m.finish(col, 0.55, nrm, {"Subsurface Weight": 0.35, "Subsurface Radius": (0.9, 0.95, 1.0), "Specular IOR Level": 0.6})
    if kind == "forest":
        a = m.noise(p, 0.6, 5)
        b = m.noise(p, 25, 6, 0.6)
        col = m.mix(a, L((0.17, 0.115, 0.065)), L((0.32, 0.22, 0.12)))
        leaves = m.ramp(m.noise(m.mapping(p, scale=(1, 1, 3)), 18, 5, 0.6), [(0.55, (0, 0, 0)), (0.75, (1, 1, 1))])
        col = m.mix(leaves, col, L((0.42, 0.26, 0.09)))
        col = m.mix(m.ramp(m.noise(p, 1.4, 4), [(0.66, (0, 0, 0)), (0.78, (0.35, 0.35, 0.35))]), col, L((0.12, 0.2, 0.05)))
        nrm = m.bump(m.math("ADD", b, leaves), 1.0, 0.03)
        return m.finish(col, 0.95, nrm, {"Specular IOR Level": 0.1})
    raise KeyError(kind)


# =========================================================== FEUILLAGE
def leaf(name, top=(0.10, 0.25, 0.05), top2=(0.20, 0.38, 0.08), under=(0.22, 0.34, 0.12), vein=(0.55, 0.62, 0.32), translucency=0.35, gloss=0.4, silver=0.0):
    """Feuille : teinte variable par feuille (attribut couleur 'rand'), nervures (UV : u le long, v en travers 0..1), face inférieure plus claire, translucidité."""
    m = M(name)
    uvv = m.uv()
    u, v, _ = m.sep(uvv)
    rnd = m.attr("rand", "GEOMETRY")
    rr = rnd.outputs["Fac"]
    col = m.mix(m.noise(m.comb(u, v, 0.0), 3.5, 4, 0.5), L(top), L(top2))
    col = m.mix(m.math("MULTIPLY", rr, 0.7), col, L((0.28, 0.30, 0.05)))   # certaines feuilles plus jaunes
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    mid = m.ramp(m.map_range(dv, 0.0, 0.03), [(0.0, (1, 1, 1)), (1.0, (0, 0, 0))])
    side = m.wave(m.comb(m.math("ADD", m.math("MULTIPLY", u, 9.0), m.math("MULTIPLY", dv, 7.0)), 0.0, 0.0), 1.0, 0.0, 0.0, "BANDS", "X")
    sv = m.ramp(m.math("ADD", m.math("MULTIPLY", side, 0.5), 0.5), [(0.82, (0, 0, 0)), (0.95, (1, 1, 1))])
    veins = m.math("MAXIMUM", mid, m.math("MULTIPLY", sv, 0.6))
    col = m.mix(m.math("MULTIPLY", veins, 0.55), col, L(vein))
    bf = m.geom().outputs["Backfacing"]
    col = m.mix(bf, col, m.mix(m.math("MULTIPLY", veins, 0.3), L(under), L(vein)))
    if silver > 0:
        col = m.mix(m.math("MULTIPLY", bf, silver), col, L((0.62, 0.68, 0.58)))
    h = m.math("ADD", veins, m.noise(m.comb(u, v, 0.0), 80, 3))
    nrm = m.bump(h, 0.5, 0.004)
    b = m.bsdf
    m.set(b, "Base Color", col); m.set(b, "Roughness", 0.5 - gloss * 0.2); m.set(b, "Normal", nrm)
    m.set(b, "Specular IOR Level", 0.5)
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", m.mix(0.5, col, L((0.6, 0.75, 0.2))))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", translucency)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


# =========================================================== MINÉRAUX
def amethyst(name="Amethyst", deep=(0.72, 0.30, 0.92), light=(0.90, 0.62, 1.0)):
    """Quartz améthyste : transmission réfractive, absorption violette dans la masse, zonage de couleur, légères inclusions."""
    m = M(name)
    p = m.texcoord("Object")
    zone = m.noise(m.mapping(p, scale=(1, 1, 0.35)), 5.0, 3, 0.5)
    tint = m.mix(zone, L(light), L(deep))
    b = m.bsdf
    m.set(b, "Base Color", tint)
    m.set(b, "Roughness", 0.03)
    m.set(b, "IOR", 1.55)
    m.set(b, "Transmission Weight", 1.0)
    m.set(b, "Coat Weight", 0.25)
    m.set(b, "Coat Roughness", 0.02)
    rg = m.noise(p, 40, 4)
    m.set(b, "Normal", m.bump(rg, 0.06, 0.002))
    vol = m.N("ShaderNodeVolumeAbsorption")
    m.set(vol, "Color", m.mix(zone, L((0.97, 0.55, 1.0)), L((0.80, 0.25, 0.97))))
    dens = m.math("ADD", 3.0, m.math("MULTIPLY", zone, 5.0))
    m.set(vol, "Density", dens)
    m.nt.links.new(vol.outputs["Volume"], m.out.inputs["Volume"])
    # astuce ombre : les rayons d'ombre traversent (sinon cristal noir sous le soleil)
    lp = m.N("ShaderNodeLightPath")
    tr = m.N("ShaderNodeBsdfTransparent")
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", lp.outputs["Is Shadow Ray"])
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


# =========================================================== FEU
def charred_wood(name="CharredWood", glow=1.0):
    """Bois carbonisé : croûte noire craquelée (Voronoï) avec braise incandescente dans les fissures, vacillante dans le temps (driver sur 'frame')."""
    m = M(name)
    vec = m.cyl(2.0, 2.0)
    t = m.N("ShaderNodeValue")
    t.outputs[0].default_value = 0.0
    try:
        fc = t.outputs[0].driver_add("default_value")
        fc.driver.type = "SCRIPTED"
        fc.driver.expression = "frame/24.0"
    except Exception:
        pass
    cells = m.voronoi(m.mapping(vec, scale=(1, 1, 0.6)), 9.0, "DISTANCE_TO_EDGE", "Distance")
    crack = m.ramp(cells, [(0.0, (1, 1, 1)), (0.06, (0, 0, 0))])
    n = m.noise(vec, 14, 6, 0.6)
    flick = m.noise(m.comb(m.math("MULTIPLY", t.outputs[0], 0.0), 0.0, 0.0), 2.0, 1, 0.5, 0.0, w=m.math("MULTIPLY", t.outputs[0], 1.8))
    heat = m.math("MULTIPLY", crack, m.math("ADD", 0.55, m.math("MULTIPLY", m.math("ADD", n, m.math("MULTIPLY", flick, 0.6)), 0.8)), clamp=True)
    char = m.mix(m.ramp(n, [(0.3, (0, 0, 0)), (0.7, (1, 1, 1))]), L((0.012, 0.01, 0.009)), L((0.07, 0.06, 0.055)))
    b = m.bsdf
    m.set(b, "Base Color", char)
    m.set(b, "Roughness", 0.85)
    ember = m.ramp(heat, [(0.2, (0.0, 0.0, 0.0)), (0.5, L((0.9, 0.12, 0.01))), (0.85, L((1.0, 0.5, 0.06)))])
    m.set(b, "Emission Color", ember)
    m.set(b, "Emission Strength", m.math("MULTIPLY", heat, 9.0 * glow))
    m.set(b, "Normal", m.bump(m.math("SUBTRACT", n, m.math("MULTIPLY", crack, 0.7)), 1.0, 0.012))
    return m.m


def ash(name="Ash"):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 30, 6)
    col = m.mix(n, L((0.10, 0.10, 0.10)), L((0.34, 0.33, 0.31)))
    nrm = m.bump(m.noise(p, 150, 4), 0.8, 0.01)
    return m.finish(col, 0.98, nrm)


def _time_driver(sock, expr):
    fc = sock.driver_add("default_value")
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    return sock


def burnt_log(name="BuchePartiellementBrulee", radius=(0.10, 0.46), glow=1.0):
    """Bûche : écorce de chêne loin du foyer, carbonisée avec braises vacillantes au cœur (distance au centre du feu, coordonnées Objet)."""
    m = M(name)
    vec = m.cyl(3.0, 0.5)
    n1 = m.noise(vec, 4.0, 6, 0.55, 0.4)
    ridge = m.ramp(m.noise(vec, 6.0, 4, 0.5, 1.4), [(0.3, (0, 0, 0)), (0.62, (1, 1, 1))])
    n2 = m.noise(vec, 22.0, 8, 0.6)
    bark_c = m.mix(ridge, L((0.05, 0.04, 0.03)), m.mix(n2, L((0.20, 0.15, 0.11)), L((0.36, 0.29, 0.22))))
    # carbonisation
    oc = m.texcoord("Object")
    ox, oy, _ = m.sep(oc)
    r = m.math("POWER", m.math("ADD", m.math("MULTIPLY", ox, ox), m.math("MULTIPLY", oy, oy)), 0.5)
    ns = m.noise(vec, 3.0, 4, 0.5)
    rr = m.math("SUBTRACT", r, m.math("MULTIPLY", m.math("SUBTRACT", ns, 0.5), 0.35))
    char = m.map_range(rr, radius[1], radius[0], 0.0, 1.0)
    t = m.N("ShaderNodeValue")
    _time_driver(t.outputs[0], "frame/24.0")
    cv = m.cyl(1.0, 4.0)
    warp = m.noise(cv, 2.2, 4, 0.5)
    vw = m.vmath("ADD", cv, m.vmath("MULTIPLY", m.comb(warp, warp, warp), m.comb(0.55, 0.55, 0.9)).outputs["Vector"]).outputs["Vector"]
    cells = m.voronoi(vw, 2.4, "DISTANCE_TO_EDGE", "Distance")
    crack = m.ramp(cells, [(0.0, (1, 1, 1)), (0.075, (0, 0, 0))])
    hot_zone = m.map_range(m.noise(cv, 1.1, 3, 0.5), 0.35, 0.75)
    flick = m.noise(m.comb(0.0, 0.0, 0.0), 1.0, 1, 0.5, 0.0, w=m.math("MULTIPLY", t.outputs[0], 2.2))
    heat = m.math("MULTIPLY", m.math("MULTIPLY", m.math("MULTIPLY", crack, char), hot_zone), m.math("ADD", 0.6, m.math("MULTIPLY", m.math("ADD", n2, flick), 0.55)), clamp=True)
    char_c = m.mix(m.ramp(n2, [(0.3, (0, 0, 0)), (0.75, (1, 1, 1))]), L((0.006, 0.005, 0.005)), L((0.04, 0.036, 0.032)))
    col = m.mix(char, bark_c, char_c)
    h = m.math("ADD", m.math("MULTIPLY", ridge, 0.8), m.math("MULTIPLY", n2, 0.3))
    h = m.math("SUBTRACT", h, m.math("MULTIPLY", m.math("MULTIPLY", crack, char), 0.9))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.85)
    m.set(b, "Normal", m.bump(h, 1.0, 0.02))
    m.set(b, "Emission Color", m.ramp(heat, [(0.15, (0, 0, 0)), (0.5, L((0.95, 0.14, 0.01))), (0.9, L((1.0, 0.55, 0.08)))]))
    m.set(b, "Emission Strength", m.math("MULTIPLY", heat, 4.5 * glow))
    return m.m


def ember_bed(name="LitDeBraises"):
    """Lit de cendres et braises : cendre grise craquelée, points incandescents qui palpitent."""
    m = M(name)
    p = m.texcoord("Object")
    t = m.N("ShaderNodeValue")
    _time_driver(t.outputs[0], "frame/24.0")
    n = m.noise(p, 25, 6, 0.6)
    cells = m.voronoi(p, 34.0, "F1", "Distance")
    spots = m.ramp(cells, [(0.0, (1, 1, 1)), (0.3, (0, 0, 0))])
    pulse = m.noise(m.mapping(p, scale=(1, 1, 1)), 6.0, 2, 0.5, 0.0, w=m.math("MULTIPLY", t.outputs[0], 1.4))
    mask = m.math("MULTIPLY", m.math("MULTIPLY", spots, m.ramp(m.noise(p, 5.0, 3, 0.5), [(0.4, (0, 0, 0)), (0.65, (1, 1, 1))])), m.math("ADD", 0.5, pulse), clamp=True)
    ash = m.mix(n, L((0.08, 0.075, 0.07)), L((0.38, 0.36, 0.33)))
    b = m.bsdf
    m.set(b, "Base Color", ash)
    m.set(b, "Roughness", 0.95)
    m.set(b, "Normal", m.bump(m.math("ADD", n, m.math("MULTIPLY", spots, 0.4)), 0.8, 0.01))
    m.set(b, "Emission Color", m.ramp(mask, [(0.1, (0, 0, 0)), (0.5, L((0.95, 0.15, 0.01))), (0.95, L((1.0, 0.6, 0.12)))]))
    m.set(b, "Emission Strength", m.math("MULTIPLY", mask, 9.0))
    return m.m


def spark(name="Etincelle"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = L((1.0, 0.45, 0.07))
    em.inputs["Strength"].default_value = 14.0
    nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
    return mat


def _bare(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    m = M.__new__(M)
    m.m, m.nt, m._n = mat, nt, 0
    m.out = nt.nodes.new("ShaderNodeOutputMaterial")
    m.bsdf = None
    return m


def flame_volume(name="Flamme", height=1.0, radius=0.26, intensity=11.0, period=60.0, temp=(900.0, 3300.0)):
    """Flamme réaliste : volume Cycles. Domaine = cube d'origine à la base (z de 0 à `height`, x et y centrés).
    Densité = enveloppe en goutte × langues de flamme (bruit étiré vers le haut, bords déchiquetés) qui MONTENT avec le temps
    (boucle parfaite : 2 couches déphasées d'une demi-période) ; corps noir : cœur jaune clair, pointes orangées puis rouges."""
    m = _bare(name)
    t = m.N("ShaderNodeValue")
    _time_driver(t.outputs[0], "frame")
    ph = m.N("ShaderNodeValue")
    _time_driver(ph.outputs[0], f"fmod(frame,{period})/{period}")
    x, y, z = m.sep(m.texcoord("Object"))
    zn = m.math("MAXIMUM", m.math("MINIMUM", m.math("DIVIDE", z, height), 1.0), 0.0)
    sway = m.math("MULTIPLY", m.math("SINE", m.math("ADD", m.math("MULTIPLY", z, 6.0), m.math("MULTIPLY", t.outputs[0], 0.28))), 0.04)
    sway = m.math("ADD", sway, m.math("MULTIPLY", m.math("SINE", m.math("ADD", m.math("MULTIPLY", z, 3.1), m.math("MULTIPLY", t.outputs[0], 0.17))), 0.03))
    dist = 4.0

    def noise_layer(offset, xs_in):
        p = m.math("FRACT", m.math("ADD", ph.outputs[0], offset))
        rise = m.math("MULTIPLY", p, dist)
        w = m.math("POWER", m.math("SINE", m.math("MULTIPLY", p, math.pi)), 2.0)
        q = m.comb(m.math("MULTIPLY", xs_in, 7.0), m.math("MULTIPLY", y, 7.0), m.math("SUBTRACT", m.math("MULTIPLY", z, 3.2), rise))
        n1 = m.noise(q, 1.0, 6, 0.6, 0.6)
        q2 = m.mapping(q, scale=(2.1, 2.1, 1.4), loc=(5.1, 2.3, 0.0))
        n2 = m.noise(q2, 1.0, 5, 0.6, 0.4)
        q3 = m.mapping(q, scale=(5.0, 5.0, 3.2), loc=(1.7, 9.3, 0.0))
        n3 = m.noise(q3, 1.0, 3, 0.5, 0.2)
        v = m.math("ADD", m.math("ADD", m.math("MULTIPLY", n1, 0.62), m.math("MULTIPLY", n2, 0.34)), m.math("MULTIPLY", n3, 0.18))
        return m.math("MULTIPLY", v, w)

    ragged_raw = m.math("ADD", noise_layer(0.0, x), noise_layer(0.5, x))
    ragged = m.map_range(ragged_raw, 0.30, 0.80, 0.0, 1.0)
    xs = m.math("ADD", x, m.math("ADD", m.math("MULTIPLY", sway, m.math("ADD", zn, 0.3)), m.math("MULTIPLY", m.math("SUBTRACT", ragged, 0.5), m.math("MULTIPLY", zn, 0.35))))
    r = m.math("POWER", m.math("ADD", m.math("MULTIPLY", xs, xs), m.math("MULTIPLY", y, y)), 0.5)
    rad = m.math("MULTIPLY", m.math("POWER", m.math("SUBTRACT", 1.0, zn), 0.62), radius)
    env = m.map_range(m.math("DIVIDE", r, m.math("MAXIMUM", rad, 0.012)), 0.25, 1.0, 1.0, 0.0)
    mix_ = m.math("ADD", m.math("MULTIPLY", ragged, 0.75), m.math("MULTIPLY", env, 0.65))
    tongue = m.map_range(mix_, 0.52, 0.95, 0.0, 1.0)
    dens = m.math("MULTIPLY", m.math("MULTIPLY", tongue, env), m.math("POWER", m.math("SUBTRACT", 1.0, zn), 0.2))
    dens = m.math("MULTIPLY", dens, m.map_range(z, 0.0, 0.05))
    pv = m.N("ShaderNodeVolumePrincipled")
    streak = m.map_range(ragged, 0.1, 0.9, 0.5, 1.0)
    dens_e = m.math("MULTIPLY", dens, streak)
    m.set(pv, "Density", m.math("MULTIPLY", dens, 0.6))
    m.set(pv, "Color", L((0.03, 0.02, 0.012)))
    m.set(pv, "Emission Strength", 0.0)
    m.set(pv, "Blackbody Intensity", m.math("MULTIPLY", dens_e, intensity))
    heat = m.math("MULTIPLY", m.math("MINIMUM", m.math("ADD", m.math("MULTIPLY", dens, 0.8), m.math("MULTIPLY", env, 0.4)), 1.0), m.math("SUBTRACT", 1.15, m.math("MULTIPLY", zn, 1.05)))
    m.set(pv, "Temperature", m.math("ADD", temp[0], m.math("MULTIPLY", m.math("MINIMUM", heat, 1.0), temp[1] - temp[0])))
    m.nt.links.new(pv.outputs["Volume"], m.out.inputs["Volume"])
    return m.m


def smoke_volume(name="Fumee", height=2.2, radius=0.45, period=120.0):
    """Mince fumée grise qui s'élève et s'élargit (volume Cycles, animé par driver sur 'frame')."""
    m = _bare(name)
    ph = m.N("ShaderNodeValue")
    _time_driver(ph.outputs[0], f"fmod(frame,{period})/{period}")
    x, y, z = m.sep(m.texcoord("Object"))
    zn = m.math("MAXIMUM", m.math("MINIMUM", m.math("DIVIDE", z, height), 1.0), 0.0)
    drift = m.math("MULTIPLY", m.math("SINE", m.math("MULTIPLY", z, 2.4)), 0.12)
    r = m.math("POWER", m.math("ADD", m.math("MULTIPLY", m.math("ADD", x, drift), m.math("ADD", x, drift)), m.math("MULTIPLY", y, y)), 0.5)
    rad = m.math("ADD", 0.12, m.math("MULTIPLY", zn, radius))
    shape = m.map_range(m.math("DIVIDE", r, rad), 0.1, 1.0, 1.0, 0.0)
    def layer(offset):
        p = m.math("FRACT", m.math("ADD", ph.outputs[0], offset))
        w = m.math("POWER", m.math("SINE", m.math("MULTIPLY", p, math.pi)), 2.0)
        q = m.comb(x, y, m.math("SUBTRACT", m.math("MULTIPLY", z, 1.6), m.math("MULTIPLY", p, 3.0)))
        return m.math("MULTIPLY", m.noise(q, 2.6, 5, 0.6, 0.8), w)
    turb = m.math("ADD", layer(0.0), layer(0.5))
    dens = m.math("MULTIPLY", m.math("MULTIPLY", shape, m.map_range(turb, 0.3, 0.8)), m.math("MULTIPLY", m.math("SUBTRACT", 1.0, zn), 0.9))
    dens = m.math("MULTIPLY", dens, m.map_range(z, 0.15, 0.5))
    pv = m.N("ShaderNodeVolumePrincipled")
    m.set(pv, "Density", m.math("MULTIPLY", dens, 1.3))
    m.set(pv, "Color", L((0.22, 0.21, 0.20)))
    m.set(pv, "Anisotropy", 0.3)
    m.nt.links.new(pv.outputs["Volume"], m.out.inputs["Volume"])
    return m.m


# =========================================================== FRUITS / CONIFÈRES
def apple(name="Pomme", red=0.75):
    """Pomme : rouge strié sur fond jaune-vert, lenticelles, creux sombre à la queue, brillance. UV sphériques (u = longitude, v = latitude)."""
    m = M(name)
    uu, vv, _ = m.sep(m.uv())
    streak = m.noise(m.comb(m.math("MULTIPLY", uu, 6.0), m.math("MULTIPLY", vv, 0.8), 0.0), 9.0, 6, 0.6, 0.4)
    blush = m.map_range(m.math("ADD", m.math("MULTIPLY", streak, 1.2), red - 0.3), 0.4, 0.8)
    base = m.mix(m.noise(m.comb(uu, vv, 0.0), 4.0, 3), L((0.62, 0.62, 0.14)), L((0.78, 0.74, 0.22)))
    col = m.mix(blush, base, m.mix(streak, L((0.62, 0.05, 0.04)), L((0.85, 0.13, 0.07))))
    dots = m.ramp(m.noise(m.comb(m.math("MULTIPLY", uu, 8), vv, 0), 120.0, 2), [(0.72, (0, 0, 0)), (0.76, (1, 1, 1))])
    col = m.mix(m.math("MULTIPLY", dots, 0.5), col, L((0.85, 0.8, 0.5)))
    top = m.map_range(vv, 0.82, 0.95)
    bot = m.map_range(vv, 0.2, 0.08)
    col = m.mix(m.math("MAXIMUM", top, bot), col, L((0.12, 0.08, 0.03)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", m.math("ADD", 0.28, m.math("MULTIPLY", streak, 0.15)))
    m.set(b, "Specular IOR Level", 0.7)
    m.set(b, "Coat Weight", 0.25)
    m.set(b, "Subsurface Weight", 0.1)
    return m.m


def fruit_simple(name, color, rough=0.4, sss=0.0):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 40, 4)
    col = m.mix(n, L(tuple(c * 0.7 for c in color)), L(color))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", rough)
    m.set(b, "Subsurface Weight", sss)
    return m.m


def velvet_pod(name="FruitBaobab"):
    """Fruit du baobab : coque veloutée gris-brun (peau duveteuse)."""
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 120, 5, 0.6)
    col = m.mix(m.noise(p, 6, 3), L((0.28, 0.23, 0.17)), L((0.52, 0.45, 0.34)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.95)
    m.set(b, "Sheen Weight", 0.8)
    m.set(b, "Sheen Roughness", 0.5)
    m.set(b, "Normal", m.bump(n, 0.6, 0.004))
    return m.m


def needles(name="Aiguilles", snow=0.0):
    """Rameau de sapin : carte (UV : u le long du rameau, v en travers) dont l'alpha dessine des aiguilles en peigne ; neige sur les faces tournées vers le haut."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    # aiguilles : bandes obliques en V de part et d'autre de la tige
    stripes = m.wave(m.comb(m.math("ADD", m.math("MULTIPLY", u, 34.0), m.math("MULTIPLY", dv, -26.0)), 0.0, 0.0), 1.0, 0.0, 0.0, "BANDS", "X")
    comb = m.map_range(m.math("ADD", m.math("MULTIPLY", stripes, 0.5), 0.5), 0.45, 0.62)
    width = m.math("MULTIPLY", m.math("SUBTRACT", 1.0, m.math("MULTIPLY", u, 0.75)), 0.5)
    inside = m.map_range(m.math("SUBTRACT", width, dv), 0.0, 0.03)
    stem = m.map_range(m.math("SUBTRACT", 0.018, dv), 0.0, 0.01)
    alpha = m.math("MAXIMUM", m.math("MULTIPLY", comb, inside), stem)
    rnd = m.attr("rand").outputs["Fac"]
    col = m.mix(m.noise(m.comb(u, v, 0), 6.0, 3), L((0.02, 0.07, 0.04)), L((0.06, 0.16, 0.09)))
    col = m.mix(m.map_range(u, 0.6, 1.0), col, L((0.14, 0.26, 0.12)))
    if snow > 0:
        gn = m.N("ShaderNodeNewGeometry")
        vt = m.N("ShaderNodeVectorTransform", props=dict(vector_type="NORMAL", convert_from="OBJECT", convert_to="WORLD"))
        m.set(vt, "Vector", gn.outputs["Normal"])
        _, _, nz = m.sep(vt.outputs["Vector"])
        nzz = m.math("ABSOLUTE", nz)
        sn = m.map_range(m.math("ADD", m.math("MULTIPLY", nzz, 1.2), m.math("MULTIPLY", rnd, snow * 0.7)), 1.0, 1.65)
        sn = m.math("MULTIPLY", sn, m.map_range(m.noise(m.texcoord("Object"), 3.0, 4), 0.25, 0.55, 0.6, 1.0))
        col = m.mix(sn, col, L((0.93, 0.95, 0.99)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.55)
    m.set(b, "Alpha", alpha)
    m.set(b, "Specular IOR Level", 0.4)
    return m.m


def leaflet_spray(name="RameauFolioles", top=(0.12, 0.24, 0.04), top2=(0.24, 0.38, 0.07), pairs=9.0, thick=0.45, translucency=0.5):
    """Carte de feuille composée (acacia…) : alpha dessiné procéduralement = rachis + paires de petites folioles ovales ; teinte variable par carte."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    # folioles : motif en bandes obliques (V) arrondies par un seuil doux
    ph = m.math("ADD", m.math("MULTIPLY", u, pairs * 2 * math.pi), m.math("MULTIPLY", dv, -3.2))
    wv = m.math("ADD", m.math("MULTIPLY", m.math("SINE", ph), 0.5), 0.5)
    cell = m.map_range(wv, 1.0 - thick, 1.0 - thick + 0.12)
    shape = m.map_range(m.math("SUBTRACT", m.math("MULTIPLY", m.math("SINE", m.math("MULTIPLY", u, math.pi)), 0.5), dv), 0.0, 0.02)
    rach = m.map_range(m.math("SUBTRACT", 0.012, dv), 0.0, 0.006)
    alpha = m.math("MAXIMUM", m.math("MULTIPLY", cell, shape), rach)
    rnd = m.attr("rand").outputs["Fac"]
    col = m.mix(m.noise(m.comb(u, v, 0), 5.0, 3), L(top), L(top2))
    col = m.mix(m.math("MULTIPLY", rnd, 0.5), col, L((0.30, 0.34, 0.06)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.5)
    m.set(b, "Alpha", alpha)
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", m.mix(0.5, col, L((0.55, 0.75, 0.15))))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", translucency)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


def grass_blade(name="BrinHerbe", base=(0.05, 0.13, 0.02), tip=(0.30, 0.42, 0.08), dry=(0.50, 0.42, 0.18), translucency=0.4):
    """Brin d'herbe : dégradé base sombre -> pointe claire (u = longueur), nervure centrale, teinte variable par brin (une part sèche et jaunie)."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    rnd = m.attr("rand").outputs["Fac"]
    col = m.mix(m.map_range(u, 0.0, 1.0), L(base), L(tip))
    col = m.mix(m.math("MULTIPLY", m.map_range(rnd, 0.72, 0.95), 0.85), col, L(dry))
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    mid = m.map_range(dv, 0.06, 0.0)
    col = m.mix(m.math("MULTIPLY", mid, 0.3), col, L((0.5, 0.6, 0.25)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.5)
    m.set(b, "Normal", m.bump(mid, 0.3, 0.002))
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", m.mix(0.5, col, L((0.5, 0.7, 0.12))))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", translucency)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


def dead_leaf(name="FeuilleMorte"):
    """Feuille morte (litière) : brun orangé à ocre, nervures sombres, bords enroulés ternes."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    rnd = m.attr("rand").outputs["Fac"]
    base = m.mix(rnd, L((0.30, 0.15, 0.05)), L((0.55, 0.36, 0.12)))
    n = m.noise(m.comb(u, v, 0), 9.0, 4, 0.55)
    col = m.mix(n, base, L((0.20, 0.10, 0.04)))
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    mid = m.map_range(dv, 0.05, 0.0)
    col = m.mix(m.math("MULTIPLY", mid, 0.7), col, L((0.14, 0.07, 0.03)))
    return m.finish(col, 0.85, m.bump(m.math("ADD", mid, n), 0.4, 0.003))


# =========================================================== PETITES PIÈCES (fleurs, citrouilles, champignons...)
def petal(name, base, tip, vein_strength=0.25, translucency=0.45, edge=None, dark_base=0.0, rough=0.4, sss=0.12):
    """Pétale : dégradé base -> pointe (u = longueur), veinage fin (v = largeur), translucide, tache sombre éventuelle à la base."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    rnd = m.attr("rand").outputs["Fac"]
    col = m.mix(m.map_range(u, 0.0, 1.0), L(base), L(tip))
    col = m.mix(m.math("MULTIPLY", rnd, 0.25), col, L(tuple(min(1.0, c * 1.25) for c in tip)))
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    veins = m.wave(m.comb(m.math("MULTIPLY", v, 1.0), 0.0, 0.0), 26.0, 1.5, 2.0, "BANDS", "X")
    vn = m.math("ADD", m.math("MULTIPLY", veins, 0.5), 0.5)
    col = m.mix(m.math("MULTIPLY", vn, vein_strength), col, L(tuple(c * 0.55 for c in base)))
    if edge:
        col = m.mix(m.map_range(dv, 0.36, 0.5), col, L(edge))
    if dark_base > 0:
        col = m.mix(m.math("MULTIPLY", m.map_range(u, 0.28, 0.0), dark_base), col, L((0.02, 0.01, 0.01)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", rough)
    m.set(b, "Subsurface Weight", sss)
    m.set(b, "Subsurface Radius", (0.4, 0.2, 0.1))
    m.set(b, "Normal", m.bump(vn, 0.3, 0.002))
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", L(tip))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", translucency)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


def seed_disc(name="DisqueGraines", dark=(0.07, 0.04, 0.02), mid=(0.20, 0.11, 0.04), light=(0.38, 0.28, 0.08), scale=70.0):
    """Cœur de tournesol : graines en spirale (Voronoï), anneau clair au centre, bords verts."""
    m = M(name)
    p = m.texcoord("Object")
    v = m.voronoi(p, scale, "F1", "Distance")
    seed = m.ramp(v, [(0.0, (1, 1, 1)), (0.55, (0, 0, 0))])
    col = m.mix(seed, L(dark), m.mix(m.noise(p, scale * 0.6, 3), L(mid), L(light)))
    return m.finish(col, 0.7, m.bump(seed, 0.9, 0.003))


def pumpkin(name="Citrouille", color=(0.80, 0.30, 0.04), lobes=10):
    """Citrouille : orange nervuré (sillons plus foncés), traînées, tache verte vers la queue, bosselage fin ; UV cylindriques (u angle, v hauteur)."""
    m = M(name)
    uu, vv, _ = m.sep(m.uv())
    vec = m.cyl(1.0, 1.0)
    ang = m.math("MULTIPLY", uu, lobes * 2 * math.pi)
    rib = m.math("ADD", m.math("MULTIPLY", m.math("COSINE", ang), 0.5), 0.5)      # 1 sur la côte, 0 dans le sillon
    streak = m.noise(m.comb(m.math("MULTIPLY", uu, 40.0), m.math("MULTIPLY", vv, 1.5), 0.0), 3.0, 5, 0.55)
    base = m.mix(streak, L(tuple(c * 0.85 for c in color)), L(tuple(min(1.0, c * 1.2) for c in color)))
    col = m.mix(m.math("MULTIPLY", m.map_range(rib, 0.4, 0.0), 0.7), base, L(tuple(c * 0.45 for c in color)))
    n = m.noise(vec, 24.0, 6, 0.6)
    col = m.mix(m.ramp(n, [(0.5, (0, 0, 0)), (0.75, (0.25, 0.25, 0.25))]), col, L((0.5, 0.55, 0.1)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", m.math("ADD", 0.45, m.math("MULTIPLY", n, 0.2)))
    m.set(b, "Subsurface Weight", 0.15)
    m.set(b, "Subsurface Radius", (0.6, 0.2, 0.1))
    m.set(b, "Normal", m.bump(m.math("ADD", n, m.math("MULTIPLY", rib, 0.6)), 0.5, 0.01))
    m.set(b, "Specular IOR Level", 0.55)
    return m.m


def stem_green(name="Queue", color=(0.22, 0.30, 0.10)):
    return bark(name, "furrowed", dark=tuple(c * 0.25 for c in color), mid=color, light=tuple(min(1.0, c * 1.6) for c in color), around=2.0, along=1.2)


def mushroom_cap(name="ChapeauAmanite", color=(0.78, 0.04, 0.02)):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 30, 5, 0.6)
    col = m.mix(m.noise(p, 3.0, 3), L(tuple(c * 0.75 for c in color)), L(color))
    col = m.mix(m.ramp(n, [(0.6, (0, 0, 0)), (0.8, (0.3, 0.3, 0.3))]), col, L((0.95, 0.5, 0.2)))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.32)
    m.set(b, "Coat Weight", 0.5)
    m.set(b, "Coat Roughness", 0.15)
    m.set(b, "Subsurface Weight", 0.2)
    m.set(b, "Subsurface Radius", (0.5, 0.15, 0.1))
    m.set(b, "Normal", m.bump(n, 0.25, 0.003))
    return m.m


def mushroom_flesh(name="PiedAmanite", color=(0.88, 0.84, 0.74), gills=False):
    m = M(name)
    uu, vv, _ = m.sep(m.uv())
    p = m.texcoord("Object")
    n = m.noise(p, 40, 5, 0.6)
    col = m.mix(m.noise(p, 4.0, 3), L(tuple(c * 0.8 for c in color)), L(color))
    h = n
    if gills:
        g = m.wave(m.comb(m.math("MULTIPLY", uu, 80.0), 0.0, 0.0), 1.0, 0.0, 0.0, "BANDS", "X")
        gn = m.math("ADD", m.math("MULTIPLY", g, 0.5), 0.5)
        col = m.mix(m.math("MULTIPLY", gn, 0.6), col, L(tuple(c * 0.55 for c in color)))
        h = m.math("ADD", gn, m.math("MULTIPLY", n, 0.2))
    return m.finish(col, 0.7, m.bump(h, 0.6, 0.004), {"Subsurface Weight": 0.15, "Subsurface Radius": (0.6, 0.4, 0.3)})


def wicker(name="Osier", color=(0.62, 0.45, 0.24)):
    """Osier tressé : brins horizontaux / montants alternés (dessus-dessous), UV cylindriques (u angle, v hauteur m)."""
    m = M(name)
    uu, vv, _ = m.sep(m.uv())
    cols = 36.0
    rows = 30.0
    cu = m.math("MULTIPLY", uu, cols)
    cv = m.math("MULTIPLY", vv, rows)
    # tissage : parité de la cellule détermine quel brin passe dessus
    fu = m.math("ADD", m.math("MULTIPLY", m.math("SINE", m.math("MULTIPLY", cu, 2 * math.pi)), 0.5), 0.5)
    fv = m.math("ADD", m.math("MULTIPLY", m.math("SINE", m.math("MULTIPLY", cv, 2 * math.pi)), 0.5), 0.5)
    cell = m.math("ADD", m.math("MULTIPLY", m.math("FLOOR", cu), 1.0), m.math("FLOOR", cv))
    par = m.math("ABSOLUTE", m.math("SUBTRACT", m.math("MODULO", cell, 2.0), 0.0))
    over_h = par
    hh = m.math("ADD", m.math("MULTIPLY", fu, m.math("SUBTRACT", 1.0, over_h)), m.math("MULTIPLY", fv, over_h))
    fib = m.noise(m.comb(m.math("MULTIPLY", uu, 60.0), m.math("MULTIPLY", vv, 4.0), 0.0), 8.0, 5, 0.6)
    fibv = m.noise(m.comb(m.math("MULTIPLY", uu, 4.0), m.math("MULTIPLY", vv, 60.0), 0.0), 8.0, 5, 0.6)
    fiber = m.mix(over_h, L((0.0, 0.0, 0.0)), L((1.0, 1.0, 1.0)))
    f = m.math("ADD", m.math("MULTIPLY", fib, m.math("SUBTRACT", 1.0, over_h)), m.math("MULTIPLY", fibv, over_h))
    tone = m.mix(f, L(tuple(c * 0.55 for c in color)), L(color))
    tone = m.mix(m.math("MULTIPLY", m.map_range(hh, 0.45, 0.0), 0.6), tone, L(tuple(c * 0.25 for c in color)))
    h = m.math("ADD", m.math("MULTIPLY", hh, 1.0), m.math("MULTIPLY", f, 0.25))
    return m.finish(tone, 0.8, m.bump(h, 1.0, 0.006))


def agave_leaf(name="FeuilleAgave"):
    """Agave : feuille charnue vert-bleu cireux, rayures d'empreinte des feuilles voisines, bords plus clairs ; u = longueur, v = largeur."""
    m = M(name)
    u, v, _ = m.sep(m.uv())
    dv = m.math("ABSOLUTE", m.math("SUBTRACT", v, 0.5))
    n = m.noise(m.comb(u, v, 0.0), 9.0, 5, 0.55)
    col = m.mix(n, L((0.20, 0.34, 0.26)), L((0.40, 0.56, 0.44)))
    bands = m.wave(m.comb(m.math("MULTIPLY", u, 1.0), m.math("MULTIPLY", dv, 1.0), 0.0), 18.0, 2.5, 2.0, "BANDS", "X")
    col = m.mix(m.math("MULTIPLY", m.math("ADD", m.math("MULTIPLY", bands, 0.5), 0.5), 0.35), col, L((0.58, 0.72, 0.62)))
    col = m.mix(m.map_range(dv, 0.4, 0.5), col, L((0.62, 0.52, 0.28)))
    col = m.mix(m.map_range(u, 0.9, 1.0), col, L((0.28, 0.12, 0.06)))
    return m.finish(col, 0.45, m.bump(n, 0.35, 0.003), {"Subsurface Weight": 0.1, "Specular IOR Level": 0.6, "Coat Weight": 0.15, "Coat Roughness": 0.3})


def wheat(name="Ble", tone=(0.72, 0.52, 0.16)):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 60, 4, 0.6)
    col = m.mix(n, L(tuple(c * 0.7 for c in tone)), L(tuple(min(1.0, c * 1.2) for c in tone)))
    return m.finish(col, 0.55, m.bump(n, 0.2, 0.002), {"Subsurface Weight": 0.1})


def plume(name="Plumeau", tone=(0.86, 0.80, 0.68)):
    """Plumeau de pampa : fils fins translucides blanc crème, légèrement rosés."""
    m = M(name)
    n = m.noise(m.texcoord("Object"), 40, 3, 0.5)
    col = m.mix(n, L(tuple(c * 0.8 for c in tone)), L(tone))
    b = m.bsdf
    m.set(b, "Base Color", col)
    m.set(b, "Roughness", 0.6)
    tr = m.N("ShaderNodeBsdfTranslucent")
    m.set(tr, "Color", L(tone))
    mx = m.N("ShaderNodeMixShader")
    m.set(mx, "Fac", 0.5)
    m.nt.links.new(b.outputs["BSDF"], mx.inputs[1])
    m.nt.links.new(tr.outputs["BSDF"], mx.inputs[2])
    m.nt.links.new(mx.outputs["Shader"], m.out.inputs["Surface"])
    return m.m


def pine_cone(name="PommeDePin"):
    """Pomme de pin : écailles brun-roux plus claires aux pointes, creux sombres entre elles ; UV cylindriques (u angle, v hauteur)."""
    m = M(name)
    vec = m.cyl(1.0, 6.0)
    n = m.noise(vec, 18.0, 6, 0.6)
    uu, vv, _ = m.sep(m.uv())
    spiral = m.math("ADD", m.math("MULTIPLY", uu, 8 * 2 * math.pi), m.math("MULTIPLY", vv, -80.0))
    sc = m.math("ADD", m.math("MULTIPLY", m.math("SINE", spiral), 0.5), 0.5)
    col = m.mix(m.math("MULTIPLY", sc, 0.9), L((0.06, 0.035, 0.02)), m.mix(n, L((0.30, 0.17, 0.08)), L((0.48, 0.32, 0.17))))
    return m.finish(col, 0.8, m.bump(m.math("ADD", sc, m.math("MULTIPLY", n, 0.3)), 1.0, 0.004))


def pine_scale(name, dark, light):
    m = M(name)
    p = m.texcoord("Object")
    n = m.noise(p, 90, 5, 0.6)
    u, v, _ = m.sep(m.uv())
    col = m.mix(m.map_range(u, 0.0, 1.0), L(dark), L(light))
    col = m.mix(m.math("MULTIPLY", n, 0.5), col, L(tuple(c * 0.5 for c in dark)))
    return m.finish(col, 0.75, m.bump(n, 0.7, 0.002))
