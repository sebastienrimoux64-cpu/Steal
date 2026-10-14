# Arbres en voxel

6 arbres en cubes (1 voxel = 12,5 cm), couleurs par voxel (plusieurs verts, écorces, pommes, olives, neige…), sans feuilles réalistes :
`arbre-pommier` (pommes rouges), `arbre-olivier` (tronc tordu, olives), `arbre-baobab` (tronc en bouteille bagué, fruits), `arbre-acacia` (parasol),
`arbre-sapin-enneige` (étages couverts de neige), `arbre-jungle` (contreforts, lianes, bromélias).

- `arbre-<nom>.blend` / `.fbx` / `.glb` : un arbre par fichier (origine = pied du tronc, Z vers le haut). Matériaux simples (une couleur unie par voxel), donc FBX / GLB corrects.
- `TreesVoxel_All.blend` : les 6 alignés (+ ciel, sol, caméra). `Apercus/` : rendus.

Régénérer : `python tools/trees_voxel/make_voxel_trees.py -- [noms…] --render`.
