# NaturePack réaliste

Refonte **réaliste** des éléments du NaturePack (arbres, plantes, accessoires, décor), faite pour **Blender 4.x / 5.x avec Cycles**.
Rien n'utilise d'image : toutes les textures sont **fabriquées par nœuds** (procédurales), donc nettes à n'importe quelle distance :
roche stratifiée (grès, granite), écorces (sillonnée, lisse du baobab, écailleuse, bouleau à lenticelles, plaques), bois patiné (veinage, fentes,
clous), mousse, lichen, herbe, feuilles (nervures, translucidité), pétales, bois brûlé à braises, améthyste translucide (réfraction + absorption)…

## Contenu (31 assets)

| Famille | Assets |
|---|---|
| **Arbres** | `arbre-pommier`, `arbre-olivier`, `arbre-baobab`, `arbre-acacia`, `arbre-sapin-enneige`, `arbre-jungle` (kapokier à contreforts, lianes, broméliacées) |
| **Plantes** | `fleurs-marguerites`, `fleurs-tournesols`, `fleurs-coquelicots`, `rosier`, `ble`, `agave`, `herbe-pampa`, `mousse`, `motte-herbe` |
| **Accessoires** | `citrouille`, `citrouilles-groupe`, `pomme-de-pin`, `branche`, `buches-empilees`, `buches-bouleau`, `tas-de-feuilles`, `amanite`, `panier-osier` |
| **Décor** | `pierres-de-gue`, `cloture`, `panneau`, `pont-bois`, `rocher-cristaux` (géode d'améthyste), `rocher-arche` (arche de grès), **`feu-de-camp` animé** |

Le **bambou** du pack d'origine est conservé tel quel (il n'a pas été refait).

## Fichiers

- `NaturePack_Realiste.blend` : **tout dans un seul fichier**, une rangée par famille, ciel + soleil, une caméra par famille (le feu de camp est animé).
- `Arbres/`, `Plantes/`, `Accessoires/`, `Décor/` : **un .blend par asset** (asset + sol + ciel + soleil + caméra prêts à rendre).
- `Apercus/` : un rendu par asset, `feu-de-camp.gif` / `feu-de-camp.mp4` : le feu en boucle.

## Le feu de camp

Foyer de pierres, bûches carbonisées (croûte noire craquelée avec **braises qui palpitent**), lit de cendres incandescent, **flammes volumétriques**
(Cycles : bruit turbulent qui monte avec le temps, boucle parfaite de 60 images, couleur par corps noir : cœur jaune-blanc, pointes orangées),
fumée, étincelles qui s'élèvent et **lumière orangée qui vacille** (elle éclaire les pierres et le sol). Tout est animé par pilotes sur le numéro d'image (images 1 → 120, 24 i/s),
sans cache à calculer : il suffit de lire la timeline.

## Comment c'est fait / limites

- Rendu : **Cycles** (les matériaux, les volumes de flamme et le verre d'améthyste n'ont pas d'équivalent Eevee exact).
- Les arbres sont **modélisés feuille par feuille** (pommier ≈ 23 000 feuilles, olivier ≈ 22 000…) : fichiers lourds, viewport plus lent. Les feuillages d'acacia et de sapin utilisent des
  cartes à transparence procédurale.
- Les matériaux procéduraux ne s'exportent pas tels quels en FBX/GLB (il faudrait les « baker »).
- Pas de LOD ni de rig de vent sur cette version réaliste (le pack à textures de l'atlas garde les siens).

## Régénérer

```
python tools/nature_real/build_real.py -- [noms…] --render      # un .blend + un aperçu par asset
python tools/nature_real/combine_real.py                        # le .blend combiné
python tools/nature_real/render_fire.py -- NaturePackRealiste/Décor/feu-de-camp.blend NaturePackRealiste/Apercus/feu_frames
```
