# NaturePack – textures appliquées + 31 nouveaux assets

`nature-pack.blend` = ton pack d'origine (arbres, buissons, fleurs, champignons, rochers, eau, brume, vent…) avec :

1. **L'atlas de textures appliqué** aux trois matériaux (`NaturePackHigh_Atlas`, `NaturePackMedium_Atlas`, `NaturePackLow_Atlas`).
   Les images sont embarquées dans le `.blend` et aussi fournies à côté : `high/nature-atlas-1024.png`, `medium/nature-atlas-1024.png`, `low/nature-atlas-512.png` (la basse est l'atlas réduit à 512 px).
2. **31 nouveaux assets**, tous UV-mappés sur ton atlas (rien d'autre comme texture), en **3 niveaux de détail** (`-high`, `-medium`, `-low`) dans les collections `High`, `Medium`, `Low` de la scène `Pack`, rangés à la suite des rangées existantes.
3. **Rigs de vent** (os `racine`, `tige…`, `tronc1/tronc2/cime`, `branche…`, boucle de 120 images) pour les arbres et les plantes, comme dans le pack d'origine.
4. Une scène **`Extras`** (Cycles, ciel de la forêt) qui montre les nouveautés, avec une caméra par planche.

## Ce qui manquait dans le pack, et ce que j'ai ajouté

| Catégorie | Nouveaux assets |
|---|---|
| Arbres (rangée y = 0, x = 80 → 112) | `arbre-pommier` (pommes rouges), `arbre-olivier` (tronc tordu, olives), `arbre-baobab`, `arbre-acacia` (canopée en parasol), `arbre-sapin-enneige` |
| Plantes (rangée y = −8, x = 19,2 → 38,4) | `fleurs-marguerites`, `fleurs-tournesols`, `fleurs-coquelicots`, `rosier`, `bambou`, `ble`, `agave`, `herbe-pampa`, `mousse` |
| Automne / forêt (y = −26) | `citrouille`, `citrouilles-groupe`, `pomme-de-pin`, `branche`, `buches-empilees`, `tas-de-feuilles`, `amanite` |
| Décor (y = −32) | `pierres-de-gue`, `feu-de-camp`, `cloture`, `panneau`, `pont-bois`, `rocher-cristaux`, `rocher-arche` |
| Textures peu utilisées (y = −38) | `panier-osier` (tuile osier), `buches-bouleau` (tuile bouleau), `motte-herbe` (tuile herbe) |

Idée : le pack avait des forêts tempérées, un désert (cactus, palmier) et des rochers ; il lui manquait le côté **ferme / potager** (citrouilles, blé, tournesols, clôture, pont), le côté **campement** (feu, bûches, panneau), l'**hiver** (sapin enneigé), la **savane / méditerranée** (baobab, acacia, olivier, agave, pampa) et des fleurs courantes (marguerites, coquelicots, rosier).

## Comment l'atlas est utilisé (1024 × 1024)

```
 ┌────────────┬────────────┬────────────┬────────────┐
 │ palette    │ dégradé A  │ dégradé B  │ coupe de   │   ligne du haut
 │ 8 × 6 cases│ 8 colonnes │ 8 colonnes │ tronc      │
 ├────────────┼────────────┼────────────┼────────────┤
 │ bouleau    │ écorce     │ écorce     │ herbe      │
 │            │ sombre     │ orange     │ osier      │   colonnes hautes + 3 carrés
 │            │            │            │ pierre     │
 └────────────┴────────────┴────────────┴────────────┘
```

- Feuillages et plantes : colonnes de **dégradé A/B** (clair en haut → sombre en bas, selon la hauteur de l'objet).
- Fleurs, fruits, champignons, cristaux, flammes : **cases de la palette**.
- Troncs, bûches, clôtures, pont : tuiles **écorce / bouleau / orange**, bouts de bûche avec la **coupe de tronc**.
- Baobab, pierres de gué : tuile **pierre** et dégradé B gris/brun.

## Régénérer

```
python tools/nature/build_pack.py -- <ton-nature-pack-original.blend> [--render]
```

Les primitives (blobs, tubes, tours, boîtes, rigs de vent) sont dans `tools/nature/natlib.py` et les assets dans `tools/nature/assets_*.py`.

## À savoir

- Les scènes `Couverture` / `Couverture désert` n'ont pas été modifiées (elles prennent maintenant l'atlas via les matériaux).
- Les nouveaux assets sont dans `Pack` (haute / moyenne / basse) et dans `Extras` (haute) ; les LOD sont reconstruits à moindre résolution (pas de décimation).
