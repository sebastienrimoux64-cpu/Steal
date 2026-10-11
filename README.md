# Steal — Les 9 bijū en cubes, rigés pour Blender

Les 9 démons à queues de Naruto, **modélisés en cubes** (style blocs) avec un **squelette complet** (armature) et deux animations (`Idle`, `Walk`).

| # | Bijū | Forme | Queues |
|---|------|-------|:-----:|
| 1 | Shukaku | tanuki de sable | 1 |
| 2 | Matatabi | chat à flammes bleues | 2 |
| 3 | Isobu | tortue à carapace piquante | 3 |
| 4 | Son Goku | singe rouge à crinière | 4 |
| 5 | Kokuo | cheval-dauphin à corne | 5 |
| 6 | Saiken | limace | 6 |
| 7 | Chomei | scarabée ailé | 7 |
| 8 | Gyūki | taureau-pieuvre | 8 |
| 9 | Kurama | renard | 9 |

## Fichiers (dossier `models/`)
- `Bijuu_Tous.blend` : les 9 dans une même scène.
- `<Nom>.blend` : un bijū, avec armature et animations (ouvrir directement dans Blender).
- `<Nom>.fbx` / `<Nom>.glb` : même modèle pour d'autres logiciels (Unity, Unreal, Godot...).

Dans Blender : **File > Open** sur un `.blend`, ou **File > Import > FBX / glTF**.

## Le rig
Chaque modèle = un seul maillage (`<Nom>_Mesh`) skinné sur une armature (`<Nom>_Rig`) :
`Root` > `Body` > `Neck` > `Head` > `Jaw`, oreilles `Ear.L/.R`, 4 pattes
(`FrontLeg_Upper.L` > `_Lower.L` > `_Paw.L`), queues segmentées `TailN_K`
(chaque segment est l'os enfant du précédent), plus des os spécifiques
(cornes, ailes `Wing.L/.R`, antennes...).
Conventions : le bijū regarde vers **-Y**, côté gauche = **+X** (`.L`), 1 unité = 1 m.
Pour animer : passez en **Pose Mode**, sélectionnez l'armature, et faites tourner les os.
Actions fournies : `Idle` (respiration, queues, mâchoire) et `Walk` (cycle de marche).

## Régénérer / modifier
Python avec le module `bpy` (`pip install bpy`) :
```
python tools/make_bijuu.py            # les 9 bijū dans models/
python tools/make_bijuu.py Kurama     # un seul
python tools/render_preview.py models/Kurama.blend apercu.png   # rendu d'aperçu
```
Chaque bijū est un dictionnaire dans `tools/make_bijuu.py` (tailles, couleurs, nombre de queues, détails).
