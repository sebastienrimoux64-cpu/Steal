"""Matériaux procéduraux réalistes (nœuds Blender) : bois, métaux, gemmes, lapis, cuir, corde."""
import bpy


def lin(c):
    """sRGB (ce qu'on voit) -> linéaire (ce que Blender attend)."""
    return tuple((x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4) for x in c[:3])


class MB:
    """Petit constructeur de nœuds."""
    def __init__(self, name):
        self.m = bpy.data.materials.new(name)
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.bsdf = self.nt.nodes.new("ShaderNodeBsdfPrincipled")
        self.nt.links.new(self.bsdf.outputs["BSDF"], self.out.inputs["Surface"])
        self.y = 0

    def n(self, kind, **kw):
        node = self.nt.nodes.new(kind)
        for k, v in kw.items():
            if k.startswith("i_"):
                node.inputs[k[2:].replace("__", " ")].default_value = v
            else:
                setattr(node, k, v)
        return node

    def link(self, a, a_out, b, b_in):
        self.nt.links.new(a.outputs[a_out], b.inputs[b_in])

    def ramp(self, src, stops, src_out="Fac", interp="LINEAR"):
        r = self.n("ShaderNodeValToRGB")
        r.color_ramp.interpolation = interp
        els = r.color_ramp.elements
        while len(els) > len(stops):
            els.remove(els[-1])
        while len(els) < len(stops):
            els.new(0.5)
        for e, (pos, col) in zip(els, stops):
            e.position = pos
            e.color = col if len(col) == 4 else tuple(col) + (1.0,)
        self.link(src, src_out, r, "Fac")
        return r

    def math(self, op, a=None, b=None, clamp=False):
        node = self.n("ShaderNodeMath", operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, tuple):          # (node, sortie)
                self.link(v[0], v[1], node, i)
            else:
                node.inputs[i].default_value = v
        return node

    def mix(self, fac, c1, c2, blend="MIX"):
        node = self.n("ShaderNodeMix", data_type="RGBA", blend_type=blend)
        if isinstance(fac, tuple):
            self.link(fac[0], fac[1], node, "Factor")
        else:
            node.inputs["Factor"].default_value = fac
        for key, v in (("A", c1), ("B", c2)):
            if isinstance(v, tuple) and hasattr(v[0], "outputs"):
                self.link(v[0], v[1], node, key)
            else:
                node.inputs[key].default_value = tuple(v) + (1.0,) if len(v) == 3 else v
        return node


def _coords(mb, scale=(1, 1, 1), rot=(0, 0, 0)):
    tc = mb.n("ShaderNodeTexCoord")
    mp = mb.n("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    mp.inputs["Rotation"].default_value = rot
    mb.link(tc, "Object", mp, "Vector")
    return mp


def _bump(mb, height_node, height_out, strength, dist=0.01):
    b = mb.n("ShaderNodeBump")
    b.inputs["Strength"].default_value = strength
    b.inputs["Distance"].default_value = dist
    mb.link(height_node, height_out, b, "Height")
    mb.link(b, "Normal", mb.bsdf, "Normal")
    return b


def wood(name, dark, mid, light, ring_dir="Z", scale=430, rough=0.5):
    """Bois : cernes concentriques autour de l'axe (veines le long du manche), fibres fines, légère rugosité."""
    dark, mid, light = lin(dark), lin(mid), lin(light)
    mb = MB(name)
    mp = _coords(mb)
    wave = mb.n("ShaderNodeTexWave", wave_type="RINGS", rings_direction=ring_dir, wave_profile="SIN")
    wave.inputs["Scale"].default_value = scale
    wave.inputs["Distortion"].default_value = 3.2
    wave.inputs["Detail"].default_value = 2.0
    wave.inputs["Detail Scale"].default_value = 1.2
    wave.inputs["Detail Roughness"].default_value = 0.6
    mb.link(mp, "Vector", wave, "Vector")
    mp2 = _coords(mb, scale=(900, 900, 26) if ring_dir == "Z" else (26, 900, 900))
    fib = mb.n("ShaderNodeTexNoise")
    fib.inputs["Scale"].default_value = 1.0
    fib.inputs["Detail"].default_value = 6.0
    fib.inputs["Roughness"].default_value = 0.65
    mb.link(mp2, "Vector", fib, "Vector")
    mixv = mb.math("ADD", None, None)
    w_part = mb.math("MULTIPLY", (wave, "Fac"), 0.75)
    f_part = mb.math("MULTIPLY", (fib, "Fac"), 0.45)
    mb.link(w_part, "Value", mixv, 0); mb.link(f_part, "Value", mixv, 1)
    cr = mb.ramp(mixv, [(0.25, dark), (0.62, mid), (0.95, light)], src_out="Value")
    mb.link(cr, "Color", mb.bsdf, "Base Color")
    rg = mb.math("MULTIPLY_ADD", (fib, "Fac"), 0.28)
    rg.inputs[2].default_value = rough - 0.1
    mb.link(rg, "Value", mb.bsdf, "Roughness")
    _bump(mb, mixv, "Value", 0.12, 0.0008)
    mb.bsdf.inputs["Specular IOR Level"].default_value = 0.35
    return mb.m


def metal(name, base, base2, rough=(0.22, 0.42), scratch=0.55, edge=(1, 1, 1), patina=None, rust=None, aniso=0.0):
    """Métal : variation de teinte, rugosité nuageuse, rayures fines étirées, usure claire sur les arêtes, crevasses sombres."""
    base, base2, edge = lin(base), lin(base2), lin(edge)
    if patina:
        patina = dict(patina, color=lin(patina["color"]))
    if rust:
        rust = dict(rust, color=lin(rust["color"]))
    mb = MB(name)
    mp = _coords(mb)
    cloud = mb.n("ShaderNodeTexNoise"); cloud.inputs["Scale"].default_value = 4.0; cloud.inputs["Detail"].default_value = 5.0; cloud.inputs["Roughness"].default_value = 0.6
    mb.link(mp, "Vector", cloud, "Vector")
    col = mb.mix((cloud, "Fac"), base, base2)
    # rayures : bruit très étiré le long de X (sens de la tête) puis seuillé
    mps = _coords(mb, scale=(260, 34, 34))
    sc = mb.n("ShaderNodeTexNoise"); sc.inputs["Scale"].default_value = 1.0; sc.inputs["Detail"].default_value = 3.0; sc.inputs["Roughness"].default_value = 0.7
    mb.link(mps, "Vector", sc, "Vector")
    scr = mb.ramp(sc, [(0.55, (0, 0, 0)), (0.7, (1, 1, 1))])
    mps2 = _coords(mb, scale=(34, 34, 260))
    sc2 = mb.n("ShaderNodeTexNoise"); sc2.inputs["Scale"].default_value = 1.0; sc2.inputs["Detail"].default_value = 3.0
    mb.link(mps2, "Vector", sc2, "Vector")
    scr2 = mb.ramp(sc2, [(0.58, (0, 0, 0)), (0.72, (1, 1, 1))])
    scr_sum = mb.math("ADD", (scr, "Color"), (scr2, "Color"), clamp=True)
    # arêtes (Pointiness) et crevasses (AO)
    geo = mb.n("ShaderNodeNewGeometry")
    pt = mb.ramp(geo, [(0.50, (0, 0, 0)), (0.62, (1, 1, 1))], src_out="Pointiness")
    ao = mb.n("ShaderNodeAmbientOcclusion"); ao.inputs["Distance"].default_value = 0.02; ao.samples = 8
    col = mb.mix((pt, "Color"), (col, "Result"), edge, "MIX")
    col = mb.mix((ao, "AO"), (col, "Result") if False else (col, "Result"), (0, 0, 0), "MULTIPLY") if False else col
    ao_dark = mb.mix((ao, "AO"), (0.25, 0.25, 0.25), (1, 1, 1), "MIX")           # AO=0 -> sombre
    col = mb.mix(1.0, (col, "Result"), (ao_dark, "Result"), "MULTIPLY")
    metallic_out = None
    if patina:      # vert-de-gris dans les creux (cuivre)
        mpp = _coords(mb, scale=(1, 1, 1))
        pn = mb.n("ShaderNodeTexNoise"); pn.inputs["Scale"].default_value = 14.0; pn.inputs["Detail"].default_value = 6.0
        mb.link(mpp, "Vector", pn, "Vector")
        mask_n = mb.ramp(pn, [(0.52, (0, 0, 0)), (0.66, (1, 1, 1))])
        crev = mb.math("SUBTRACT", 1.0, (ao, "AO"))
        crev2 = mb.math("MULTIPLY", (crev, "Value"), 2.2, clamp=True)
        pm = mb.math("MULTIPLY", (mask_n, "Color"), (crev2, "Value"), clamp=True)
        pm = mb.math("MULTIPLY", (pm, "Value"), patina.get("amount", 1.0), clamp=True)
        col = mb.mix((pm, "Value"), (col, "Result"), patina["color"], "MIX")
        metallic_out = mb.math("SUBTRACT", 1.0, (pm, "Value"), clamp=True)
        patina_mask = pm
    if rust:        # taches de rouille (fer)
        mpr = _coords(mb)
        rn = mb.n("ShaderNodeTexNoise"); rn.inputs["Scale"].default_value = 9.0; rn.inputs["Detail"].default_value = 8.0; rn.inputs["Roughness"].default_value = 0.7
        mb.link(mpr, "Vector", rn, "Vector")
        rm = mb.ramp(rn, [(0.60, (0, 0, 0)), (0.74, (1, 1, 1))])
        crev = mb.math("SUBTRACT", 1.0, (ao, "AO"))
        rm2 = mb.math("MULTIPLY", (rm, "Color"), (crev, "Value"))
        rm3 = mb.math("MULTIPLY", (rm2, "Value"), 3.0 * rust.get("amount", 1.0), clamp=True)
        col = mb.mix((rm3, "Value"), (col, "Result"), rust["color"], "MIX")
        metallic_out = mb.math("SUBTRACT", 1.0, (rm3, "Value"), clamp=True)
        patina_mask = rm3
    mb.link(col, "Result", mb.bsdf, "Base Color")
    # rugosité : nuage + rayures
    rn2 = mb.n("ShaderNodeTexNoise"); rn2.inputs["Scale"].default_value = 22.0; rn2.inputs["Detail"].default_value = 6.0
    mb.link(mp, "Vector", rn2, "Vector")
    rmap = mb.n("ShaderNodeMapRange"); rmap.inputs["To Min"].default_value = rough[0]; rmap.inputs["To Max"].default_value = rough[1]
    mb.link(rn2, "Fac", rmap, "Value")
    rsum = mb.math("ADD", (rmap, "Result"), None)
    rscr = mb.math("MULTIPLY", (scr_sum, "Value"), 0.18 * min(1.0, scratch / 0.55))
    mb.link(rscr, "Value", rsum, 1)
    rfinal = rsum
    if patina or rust:
        rfinal = mb.math("ADD", (rsum, "Value"), None)
        rp = mb.math("MULTIPLY", (patina_mask, "Value"), 0.5)
        mb.link(rp, "Value", rfinal, 1)
    mb.link(rfinal, "Value", mb.bsdf, "Roughness")
    mb.bsdf.inputs["Metallic"].default_value = 1.0
    if metallic_out is not None:
        mb.link(metallic_out, "Value", mb.bsdf, "Metallic")
    _bump(mb, scr_sum, "Value", scratch * 0.12, 0.0006)
    if aniso:
        mb.bsdf.inputs["Anisotropic"].default_value = aniso
    return mb.m


def _shadow_trick(mb, surface_node, out_name="BSDF"):
    """Les rayons d'ombre traversent le verre (sinon l'ombre est noire en Cycles)."""
    lp = mb.n("ShaderNodeLightPath")
    tr = mb.n("ShaderNodeBsdfTransparent")
    mx = mb.n("ShaderNodeMixShader")
    mb.link(lp, "Is Shadow Ray", mx, "Fac")
    mb.link(surface_node, out_name, mx, 1)
    mb.link(tr, "BSDF", mx, 2)
    mb.link(mx, "Shader", mb.out, "Surface")


def crystal(name, tint, absorb, emit=0.0, emit_color=None, ior=2.42, rough=0.025, glow_noise=False, transmission=1.0):
    """Gemme taillée : réfraction, absorption de couleur dans la masse, reflets vifs ; option lumineuse (uranium)."""
    tint, absorb = lin(tint), lin(absorb)
    emit_color = lin(emit_color) if emit_color else None
    mb = MB(name)
    b = mb.bsdf
    b.inputs["Base Color"].default_value = tint + (1.0,)
    b.inputs["Metallic"].default_value = 0.0
    b.inputs["Roughness"].default_value = rough
    b.inputs["IOR"].default_value = ior
    b.inputs["Transmission Weight"].default_value = transmission
    b.inputs["Coat Weight"].default_value = 0.3
    b.inputs["Coat Roughness"].default_value = 0.02
    if emit > 0:
        mp = _coords(mb)
        nz = mb.n("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 11.0; nz.inputs["Detail"].default_value = 5.0
        mb.link(mp, "Vector", nz, "Vector")
        er = mb.ramp(nz, [(0.3, (emit_color or tint)), (0.7, tuple(min(1.0, c * 1.5) for c in (emit_color or tint)))])
        mb.link(er, "Color", b, "Emission Color")
        em = mb.math("MULTIPLY_ADD", (nz, "Fac"), emit * 0.8)
        em.inputs[2].default_value = emit * 0.6
        mb.link(em, "Value", b, "Emission Strength")
    vol = mb.n("ShaderNodeVolumeAbsorption")
    vol.inputs["Color"].default_value = absorb + (1.0,)
    vol.inputs["Density"].default_value = 55.0
    mb.link(vol, "Volume", mb.out, "Volume")
    mb.m.surface_render_method = "BLENDED" if False else mb.m.surface_render_method
    _shadow_trick(mb, b)
    return mb.m


def lapis(name):
    """Lapis-lazuli poli : bleu profond marbré, veines de calcite claires, éclats de pyrite dorée."""
    mb = MB(name)
    mp = _coords(mb)
    LP = lambda c: lin(c)
    big = mb.n("ShaderNodeTexNoise"); big.inputs["Scale"].default_value = 5.0; big.inputs["Detail"].default_value = 8.0; big.inputs["Roughness"].default_value = 0.62; big.inputs["Distortion"].default_value = 1.4
    mb.link(mp, "Vector", big, "Vector")
    blue = mb.ramp(big, [(0.30, LP((0.04, 0.07, 0.34))), (0.55, LP((0.09, 0.17, 0.62))), (0.80, LP((0.20, 0.34, 0.86)))])
    # veines claires (calcite)
    mpv = _coords(mb, scale=(1, 1, 1))
    vn = mb.n("ShaderNodeTexNoise"); vn.inputs["Scale"].default_value = 3.0; vn.inputs["Detail"].default_value = 4.0; vn.inputs["Distortion"].default_value = 2.5
    mb.link(mpv, "Vector", vn, "Vector")
    vein = mb.ramp(vn, [(0.495, (0, 0, 0)), (0.51, (1, 1, 1)), (0.525, (0, 0, 0))])
    vmask = mb.math("MULTIPLY", (vein, "Color"), 0.55, clamp=True)
    col = mb.mix((vmask, "Value"), (blue, "Color"), LP((0.78, 0.82, 0.95)))
    # pyrite : points dorés (cellules de Voronoï très petites)
    vor = mb.n("ShaderNodeTexVoronoi"); vor.inputs["Scale"].default_value = 150.0; vor.inputs["Randomness"].default_value = 1.0
    mb.link(mp, "Vector", vor, "Vector")
    fl = mb.ramp(vor, [(0.055, (1, 1, 1)), (0.085, (0, 0, 0))], src_out="Distance")
    # on garde seulement une partie des cellules (bruit de sélection)
    sel = mb.n("ShaderNodeTexNoise"); sel.inputs["Scale"].default_value = 18.0; sel.inputs["Detail"].default_value = 2.0
    mb.link(mp, "Vector", sel, "Vector")
    selr = mb.ramp(sel, [(0.50, (0, 0, 0)), (0.58, (1, 1, 1))])
    fleck = mb.math("MULTIPLY", (fl, "Color"), (selr, "Color"), clamp=True)
    col = mb.mix((fleck, "Value"), (col, "Result"), LP((0.98, 0.80, 0.30)))
    mb.link(col, "Result", mb.bsdf, "Base Color")
    mb.link(fleck, "Value", mb.bsdf, "Metallic")
    rg = mb.math("MULTIPLY_ADD", (big, "Fac"), 0.18)
    rg.inputs[2].default_value = 0.12
    mb.link(rg, "Value", mb.bsdf, "Roughness")
    mb.bsdf.inputs["Coat Weight"].default_value = 0.5
    mb.bsdf.inputs["Coat Roughness"].default_value = 0.05
    _bump(mb, big, "Fac", 0.04, 0.002)
    return mb.m


def leather(name="Leather", color=(0.20, 0.11, 0.06)):
    color = lin(color)
    mb = MB(name)
    mp = _coords(mb, scale=(1, 1, 1))
    nz = mb.n("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 260.0; nz.inputs["Detail"].default_value = 4.0
    mb.link(mp, "Vector", nz, "Vector")
    cl = mb.n("ShaderNodeTexNoise"); cl.inputs["Scale"].default_value = 9.0; cl.inputs["Detail"].default_value = 4.0
    mb.link(mp, "Vector", cl, "Vector")
    col = mb.mix((cl, "Fac"), color, tuple(c * 1.9 for c in color))
    mb.link(col, "Result", mb.bsdf, "Base Color")
    mb.bsdf.inputs["Roughness"].default_value = 0.55
    _bump(mb, nz, "Fac", 0.5, 0.0015)
    return mb.m


def rope(name="Rope", color=(0.70, 0.56, 0.34)):
    color = lin(color)
    mb = MB(name)
    mp = _coords(mb, scale=(1, 1, 1))
    wv = mb.n("ShaderNodeTexWave", wave_type="BANDS", bands_direction="Z", wave_profile="SAW")
    wv.inputs["Scale"].default_value = 520.0; wv.inputs["Distortion"].default_value = 1.5
    mb.link(mp, "Vector", wv, "Vector")
    nz = mb.n("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 90.0; nz.inputs["Detail"].default_value = 4.0
    mb.link(mp, "Vector", nz, "Vector")
    cr = mb.ramp(wv, [(0.2, tuple(c * 0.45 for c in color)), (0.9, color)])
    col = mb.mix((nz, "Fac"), (cr, "Color"), tuple(min(1, c * 1.3) for c in color))
    mb.link(col, "Result", mb.bsdf, "Base Color")
    mb.bsdf.inputs["Roughness"].default_value = 0.9
    _bump(mb, wv, "Fac", 0.8, 0.002)
    return mb.m
