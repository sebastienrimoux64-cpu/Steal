# Pioches en voxel — 8 matières

| Fichier | Matière | Particularités |
|---|---|---|
| `Pickaxe_Wood.blend` | Bois | tête en planches, grain irrégulier |
| `Pickaxe_Copper.blend` | Cuivre | métal orangé, quelques taches de vert-de-gris |
| `Pickaxe_Iron.blend` | Fer | métal gris clair, reflets |
| `Pickaxe_Gold.blend` | Or | métal doré brillant |
| `Pickaxe_Diamond.blend` | Diamant | cyan translucide-brillant, facettes claires, léger éclat lumineux |
| `Pickaxe_Uranium.blend` | Uranium vert | vert fluo **qui brille** (émission), taches sombres |
| `Pickaxe_Ruby.blend` | Rubis rouge | rouge profond brillant, facettes roses, léger éclat |
| `Pickaxe_Lapis.blend` | Lapis-lazuli bleu | bleu profond **avec des éclats d'or** (pyrite) |

- `Pickaxes_All.blend` : les 8 côte à côte (caméra, lumières et sol d'aperçu inclus).
- Chaque pioche existe aussi en `.fbx` et `.glb`.
- `previews/` : images d'aperçu.

## Détails
- **Style voxel** : 20 × 20 voxels, 1 voxel = 4 cm (pioche d'environ 80 cm), manche en diagonale + tête en croissant.
  Épaisseur de 2 à 4 voxels : bords amincis, centre plus épais (relief). Manche en bois, ligature sombre, pommeau de la couleur du matériau.
- **Un seul maillage par pioche**, uniquement les faces visibles (≈ 470 faces), un matériau par couleur (PBR : couleur, métal, rugosité, émission).
- **Repère** : la pioche est dans le plan X (droite) / Z (haut), épaisseur sur Y. **L'origine est la poignée** (point de prise) : on peut la parenter à une main.
- Chaque objet est marqué comme **Asset** (visible dans l'Asset Browser de Blender).

## Régénérer / modifier
```
python tools/pickaxes/make_pickaxes.py                       # tout régénérer dans Pickaxes/
python tools/pickaxes/render_pickaxes.py Pickaxes/Pickaxes_All.blend apercu.png front   # aperçu (vue : front ou q)
```
La forme est dans `tools/pickaxes/shape.py` (paramètres `R`, `HALF`, épaisseur...), les couleurs et matériaux dans `tools/pickaxes/make_pickaxes.py`
(un dictionnaire par matière : ramp de 4 teintes, métal, rugosité, émission, bruit, éclats). Ajouter une matière = ajouter une entrée.
