"""
NaturePack RÉALISTE : construit chaque asset (matériaux procéduraux Cycles, géométrie détaillée), un .blend par asset
avec son studio (ciel, sol, caméra), plus un .blend combiné et des aperçus.

    python tools/nature_real/build_real.py [nom ...] [--render] [--combine] [--out DIR]
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rgeo
import studio_real as S
import a_rocks, a_trees, a_wood, a_props, a_flowers, a_fire

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "NaturePackRealiste")

# nom, fonction, sol, caméra (azimut°, élévation°, focale), famille
ASSETS = [
    ("arbre-pommier", a_trees.a_pommier, "grass", (-22, 6, 50), "Arbres"),
    ("arbre-olivier", a_trees.a_olivier, "sand", (-22, 6, 50), "Arbres"),
    ("arbre-baobab", a_trees.a_baobab, "sand", (-22, 5, 50), "Arbres"),
    ("arbre-acacia", a_trees.a_acacia, "sand", (-22, 5, 50), "Arbres"),
    ("arbre-sapin-enneige", a_trees.a_sapin_enneige, "snow", (-22, 4, 50), "Arbres"),
    ("arbre-jungle", a_trees.a_arbre_jungle, "forest", (-22, 4, 50), "Arbres"),
    ("fleurs-marguerites", a_flowers.a_fleurs_marguerites, "grass", (-25, 14, 60), "Plantes"),
    ("fleurs-tournesols", a_flowers.a_tournesols, "grass", (-25, 8, 55), "Plantes"),
    ("fleurs-coquelicots", a_flowers.a_coquelicots, "grass", (-25, 12, 60), "Plantes"),
    ("rosier", a_flowers.a_rosier, "grass", (-25, 10, 55), "Plantes"),
    ("ble", a_flowers.a_ble, "dirt", (-25, 10, 55), "Plantes"),
    ("agave", a_flowers.a_agave, "sand", (-25, 22, 55), "Plantes"),
    ("herbe-pampa", a_flowers.a_herbe_pampa, "grass", (-25, 8, 55), "Plantes"),
    ("mousse", a_props.a_mousse, "forest", (-25, 30, 55), "Plantes"),
    ("motte-herbe", a_props.a_motte_herbe, "grass", (-25, 14, 55), "Plantes"),
    ("citrouille", a_props.a_citrouille, "dirt", (-25, 12, 55), "Accessoires"),
    ("citrouilles-groupe", a_props.a_citrouilles_groupe, "dirt", (-25, 20, 55), "Accessoires"),
    ("pomme-de-pin", a_props.a_pomme_de_pin, "forest", (-25, 35, 60), "Accessoires"),
    ("branche", a_props.a_branche, "forest", (-25, 25, 55), "Accessoires"),
    ("buches-empilees", a_props.a_buches_empilees, "grass", (-25, 10, 55), "Accessoires"),
    ("buches-bouleau", a_wood.a_buches_bouleau, "forest", (-30, 22, 55), "Accessoires", 0.55),
    ("tas-de-feuilles", a_props.a_tas_de_feuilles, "forest", (-25, 25, 55), "Accessoires"),
    ("amanite", a_props.a_amanite, "forest", (-25, 16, 60), "Accessoires"),
    ("panier-osier", a_props.a_panier_osier, "grass", (-25, 20, 55), "Accessoires"),
    ("pierres-de-gue", a_rocks.a_pierres_de_gue, "grass", (-20, 28, 50), "Décor", 0.8),
    ("cloture", a_props.a_cloture, "grass", (-25, 8, 50), "Décor"),
    ("panneau", a_props.a_panneau, "grass", (-25, 6, 50), "Décor"),
    ("pont-bois", a_wood.a_pont_bois, "grass", (-28, 14, 50), "Décor"),
    ("rocher-cristaux", a_rocks.a_cristaux, "dirt", (-28, 22, 55), "Décor"),
    ("rocher-arche", a_rocks.a_arche, "sand", (-20, 8, 50), "Décor"),
    ("feu-de-camp", None, "dirt", (-30, 14, 45), "Décor"),
]
BY_NAME = {a[0]: a for a in ASSETS}


def frame(objs, az=-22, el=8, lens=50, aspect=1.333, fit=1.0):
    """Cadre l'asset en entier : distance déduite de la hauteur ET de la largeur (marge de 12 %)."""
    pts = []
    for o in objs:
        for c in o.bound_box:
            pts.append(o.matrix_world @ Vector(c))
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    ctr = (lo + hi) / 2
    ext = hi - lo
    fov_h = 2 * math.atan(18 / lens)
    fov_v = 2 * math.atan(math.tan(fov_h / 2) / aspect)
    wid = max(ext.x, ext.y)
    d_h = (wid / 2) / math.tan(fov_h / 2)
    d_v = (ext.z / 2) / math.tan(fov_v / 2)
    d = (max(d_h, d_v) * 1.12 + max(ext.x, ext.y) * 0.5) * fit
    a, e = math.radians(az), math.radians(el)
    pos = ctr + Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e))) * d
    tgt = Vector((ctr.x, ctr.y, lo.z + ext.z * 0.47))
    return S.camera(pos, tgt, lens)


def build(name, res=(1400, 1050), samples=48, fire_only_frame=None):
    _, fn, ground, (az, el, lens), fam, *opt = BY_NAME[name]
    fit = opt[0] if opt else 1.0
    S.reset()
    sc = S.cycles(samples, res)
    sc.frame_start, sc.frame_end = 1, 120
    if name == "feu-de-camp":
        S.sky(sun_elev=-3, sun_rot=262, strength=0.9, sun_energy=0.0)
    else:
        S.sky()
    S.ground(ground)
    coll = bpy.data.collections.new(name)
    sc.collection.children.link(coll)
    objs = []
    objs_frame = None
    if name == "feu-de-camp":
        b = rgeo.RB(name, seed=2)
        a_fire.foyer(b)
        obj = b.finish()
        coll.objects.link(obj)
        objs.append(obj)
        eff = a_fire.add_effects(coll)
        sc.cycles.volume_step_rate = 0.6
        objs_frame = [obj] + eff[:5]
    else:
        b = rgeo.RB(name, seed=1)
        fn(b)
        obj = b.finish()
        coll.objects.link(obj)
        objs.append(obj)
    obj["famille"] = fam
    bpy.context.view_layer.update()
    cam = frame(objs_frame or objs, az, el, lens, res[0] / res[1], fit=fit)
    return sc, objs


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    names = [a for a in argv if a in BY_NAME] or [a[0] for a in ASSETS]
    render = "--render" in argv
    out = OUT
    if "--out" in argv:
        out = argv[argv.index("--out") + 1]
    os.makedirs(os.path.join(out, "Apercus"), exist_ok=True)
    for name in names:
        t0 = time.time()
        sc, objs = build(name)
        print(f"{name}: {sum(len(o.data.polygons) for o in objs if o.type == 'MESH')} faces ({time.time() - t0:.1f}s)")
        fam = BY_NAME[name][4]
        os.makedirs(os.path.join(out, fam), exist_ok=True)
        path = os.path.join(out, fam, f"{name}.blend")
        bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
        if render:
            sc.render.filepath = os.path.join(out, "Apercus", f"{name}.png")
            if name == "feu-de-camp":
                sc.frame_set(20)
            bpy.ops.render.render(write_still=True)


if __name__ == "__main__":
    main()
