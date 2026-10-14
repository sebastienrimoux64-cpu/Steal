"""
Complète le NaturePack : applique l'atlas de textures aux matériaux et ajoute de nouveaux assets (3 LOD + vent).

    python tools/nature/build_pack.py <nature-pack-source.blend>      # -> NaturePack/nature-pack.blend + Previews/
"""
import math
import os
import sys

import bpy
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import natlib as N
import assets_trees as T
import assets_plants as PL
import assets_props as PR

ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "NaturePack")
LODS = (("high", 0), ("medium", 1), ("low", 2))
MATS = {"high": "NaturePackHigh_Atlas", "medium": "NaturePackMedium_Atlas", "low": "NaturePackLow_Atlas"}
IMGS = {"high": ("nature-atlas.002", "high/nature-atlas-1024.png"), "medium": ("nature-atlas.001", "medium/nature-atlas-1024.png"), "low": ("nature-atlas", "low/nature-atlas-512.png")}

# nom, fonction, (x, y), vent
ASSETS = [
    # arbres (suite de la rangée y = 0)
    ("arbre-pommier", T.a_pommier, (80, 0), 1.0), ("arbre-olivier", T.a_olivier, (88, 0), 1.0), ("arbre-baobab", T.a_baobab, (96, 0), 1.0),
    ("arbre-acacia", T.a_acacia, (104, 0), 1.0), ("arbre-sapin-enneige", T.a_sapin_enneige, (112, 0), 1.0),
    # plantes (suite de la rangée y = -8)
    ("fleurs-marguerites", PL.a_fleurs_marguerites, (19.2, -8), 1.0), ("fleurs-tournesols", PL.a_tournesols, (21.6, -8), 1.0),
    ("fleurs-coquelicots", PL.a_coquelicots, (24.0, -8), 1.0), ("rosier", PL.a_rosier, (26.4, -8), 1.0), ("bambou", PL.a_bambou, (28.8, -8), 1.0),
    ("ble", PL.a_ble, (31.2, -8), 1.0), ("agave", PL.a_agave, (33.6, -8), 0.0), ("herbe-pampa", PL.a_herbe_pampa, (36.0, -8), 1.0), ("mousse", PL.a_mousse, (38.4, -8), 0.0),
    # accessoires (nouvelles rangées y = -26, -32, -38)
    ("citrouille", PR.a_citrouille, (0, -26), 0.0), ("citrouilles-groupe", PR.a_citrouilles_groupe, (5, -26), 0.0),
    ("pomme-de-pin", PR.a_pomme_de_pin, (10, -26), 0.0), ("branche", PR.a_branche, (15, -26), 0.0), ("buches-empilees", PR.a_buches_empilees, (20, -26), 0.0),
    ("tas-de-feuilles", PR.a_tas_de_feuilles, (25, -26), 0.0), ("amanite", PR.a_amanite, (30, -26), 0.0),
    ("pierres-de-gue", PR.a_pierres_de_gue, (0, -32), 0.0), ("feu-de-camp", PR.a_feu_de_camp, (6, -32), 0.0), ("cloture", PR.a_cloture, (12, -32), 0.0),
    ("panneau", PR.a_panneau, (18, -32), 0.0), ("pont-bois", PR.a_pont_bois, (25, -32), 0.0), ("rocher-cristaux", PR.a_rocher_cristaux, (32, -32), 0.0),
    ("rocher-arche", PR.a_rocher_arche, (40, -32), 0.0),
    ("panier-osier", PR.a_panier_osier, (0, -38), 0.0), ("buches-bouleau", PR.a_buches_bouleau, (5, -38), 0.0), ("motte-herbe", PR.a_motte_herbe, (10, -38), 0.0),
]


def apply_atlas():
    """Charge l'atlas fourni dans les 3 matériaux (haute 1024, moyenne 1024, basse 512) et l'embarque dans le .blend."""
    for lod, (img_name, rel) in IMGS.items():
        img = bpy.data.images[img_name]
        img.filepath = os.path.join(OUT, rel)
        img.reload()
        img.colorspace_settings.name = "sRGB"
        img.pack()
        img.filepath = "//" + rel      # chemin relatif au .blend (l'image est aussi embarquée)
        print("atlas", lod, tuple(img.size))


def build_all():
    scn = bpy.data.scenes["Pack"]
    colls = {lod: bpy.data.collections[lod.capitalize()] for lod, _ in LODS}
    made = {}
    for name, fn, (x, y), wind in ASSETS:
        for lod, q in LODS:
            b = N.B(f"{name}-{lod}", q=q, seed=7)
            fn(b)
            obj = b.finish(bpy.data.materials[MATS[lod]])
            colls[lod].objects.link(obj)
            rig = None
            if b.parts and wind > 0:
                rig = b.make_rig(obj, f"{name}-rig-{lod}", colls[lod], wind=wind)
                rig.location = (x, y, 0)
                obj.location = (0, 0, 0)
            else:
                obj.location = (x, y, 0)
            made.setdefault(name, {})[lod] = (obj, rig)
        print(name, [len(made[name][l][0].data.polygons) for l, _ in LODS])
    return made


ROWS = {  # planche : (centre x, centre y, largeur, hauteur utile, assets)
    "Arbres": (96, 0, 41, 8.0, ["arbre-pommier", "arbre-olivier", "arbre-baobab", "arbre-acacia", "arbre-sapin-enneige"]),
    "Plantes-1": (24, -8, 12, 3.4, ["fleurs-marguerites", "fleurs-tournesols", "fleurs-coquelicots", "rosier", "bambou"]),
    "Plantes-2": (34.8, -8, 9, 2.4, ["ble", "agave", "herbe-pampa", "mousse"]),
    "Accessoires-1": (15, -26, 33, 2.2, ["citrouille", "citrouilles-groupe", "pomme-de-pin", "branche", "buches-empilees", "tas-de-feuilles", "amanite"]),
    "Accessoires-2": (9, -32, 21, 2.6, ["pierres-de-gue", "feu-de-camp", "cloture", "panneau"]),
    "Accessoires-3": (33, -32, 22, 3.4, ["pont-bois", "rocher-cristaux", "rocher-arche"]),
    "Accessoires-4": (5, -38, 13, 1.8, ["panier-osier", "buches-bouleau", "motte-herbe"]),
}


def build_extras(made):
    """Scène « Extras » (Cycles) : les nouveaux assets en haute qualité, sol, soleil, ciel de la forêt et une caméra par planche."""
    cov = bpy.data.scenes["Couverture"]
    sc = bpy.data.scenes.new("Extras")
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = 1920, 960
    sc.view_settings.view_transform = cov.view_settings.view_transform
    sc.view_settings.look = cov.view_settings.look
    w2 = cov.world.copy(); w2.name = "ciel-extras"
    for n in w2.node_tree.nodes:
        if n.type == "BACKGROUND" and n.inputs["Strength"].default_value > 1:
            n.inputs["Strength"].default_value *= 0.5
    sc.world = w2
    sc.frame_start, sc.frame_end = 0, 120
    coll = bpy.data.collections.new("Extras")
    sc.collection.children.link(coll)
    for name, d in made.items():
        obj, rig = d["high"]
        coll.objects.link(obj) if obj.name not in coll.objects else None
        if rig is not None:
            coll.objects.link(rig)
    # sol : plan vert (la couleur vient de la palette de l'atlas)
    g = bpy.data.objects.new("sol-extras", bpy.data.meshes.new("sol-extras"))
    g.data.from_pydata([(-60, -80, -0.01), (170, -80, -0.01), (170, 40, -0.01), (-60, 40, -0.01)], [], [(0, 1, 2, 3)])
    gm = bpy.data.materials.new("sol-extras"); gm.use_nodes = True
    gb = gm.node_tree.nodes["Principled BSDF"]
    gb.inputs["Base Color"].default_value = (0.035, 0.09, 0.015, 1); gb.inputs["Roughness"].default_value = 0.95
    g.data.materials.append(gm)
    coll.objects.link(g)
    sun = bpy.data.objects.new("Soleil", bpy.data.objects["Light"].data.copy())
    sun.data.energy = 3.0
    sun.location = (0, 0, 0); sun.rotation_euler = bpy.data.objects["Light"].rotation_euler.copy()
    coll.objects.link(sun)
    cams = {}
    for nm, (cx, cy, w, h, _) in ROWS.items():
        cam = bpy.data.objects.new(f"Camera-{nm}", bpy.data.cameras.new(f"Camera-{nm}"))
        cam.data.lens = 35
        dist = w * 0.5 / math.tan(math.atan(18 / 35)) * 1.0
        cam.location = (cx, cy - dist, h * 0.75)
        tgt = Vector((cx, cy, h * 0.42))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        coll.objects.link(cam)
        cams[nm] = cam
    sc.camera = cams["Arbres"]
    return sc, cams


def render_previews(sc, cams, made):
    os.makedirs(os.path.join(OUT, "Previews"), exist_ok=True)
    for nm, cam in cams.items():
        if os.environ.get("ONLY") and nm != os.environ["ONLY"]:
            continue
        keep = set(ROWS[nm][4])
        for name, d in made.items():
            obj, rig = d["high"]
            for o in (obj, rig):
                if o is not None:
                    o.hide_render = name not in keep
        sc.camera = cam
        sc.render.filepath = os.path.join(OUT, "Previews", f"Nouveautes_{nm}.png")
        bpy.context.window.scene = sc
        bpy.ops.render.render(write_still=True, scene=sc.name)
    for name, d in made.items():
        for o in d["high"]:
            if o is not None:
                o.hide_render = False
    sc.camera = cams["Arbres"]


def main():
    src = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else sys.argv[-1]
    bpy.ops.wm.open_mainfile(filepath=src)
    apply_atlas()
    made = build_all()
    sc, cams = build_extras(made)
    return made, sc, cams


if __name__ == "__main__":
    made, sc, cams = main()
    sc.cycles.samples = 48
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "nature-pack.blend"), relative_remap=True)
    if "--render" in sys.argv:
        render_previews(sc, cams, made)
