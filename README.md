# Steal — Les 9 bijū en cubes, rigés pour Blender

Les 9 démons à queues de Naruto, **modélisés en voxels haute résolution** (blocs de 25 cm, pelage, dents, marques) avec un **squelette détaillé** (armature à 47–135 os selon le bijū), une déformation douce aux articulations et deux animations (`Idle`, `Walk`). Chaque bijū mesure plusieurs mètres de haut (échelle ×3 par rapport à la première version).

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
- colonne : `Root` > `Spine1` (hanches) > `Spine2` > `Spine3` (poitrail) > `Neck1` > `Neck2` > `Head`
- tête : `Jaw` (mâchoire), `Tongue` (langue), `Eyelid.L/.R` (paupières, clignement), `Ear1/Ear2.L/.R` (oreilles à 2 os)
- 4 pattes : `FrontLeg_Upper.L` > `_Lower.L` > `_Paw.L` > `_Toe1..3.L` (doigts avec griffes)
- queues : `TailN_1` ... `TailN_10` (10 os par queue, déformation progressive le long de la queue)
- os spécifiques : cornes, ailes `Wing.L/.R`, antennes, moustaches...
Conventions : le bijū regarde vers **-Y**, côté gauche = **+X** (`.L`), 1 unité = 1 m.
Pour animer : passez en **Pose Mode**, sélectionnez l'armature, et faites tourner les os.
Actions fournies : `Idle` (respiration, clignement, oreilles, queues, mâchoire) et `Walk` (cycle de marche).

## Régénérer / modifier
Python avec le module `bpy` (`pip install bpy`) :
```
python tools/make_bijuu.py            # les 9 bijū dans models/
python tools/make_bijuu.py Kurama     # un seul
python tools/render_preview.py models/Kurama.blend apercu.png   # rendu d'aperçu
```
Chaque bijū est un dictionnaire dans `tools/make_bijuu.py` (tailles, couleurs, nombre de queues, détails). `Q` (taille d'un voxel) et `STUD` (échelle) en haut du fichier règlent la résolution et la taille.

## Animation « chute » du personnage R6
`models/R6_Chute.blend` : le personnage R6 (style Roblox) tombe d'une falaise de 40 unités (240 images à 60 i/s) : déséquilibre, bascule, chute libre avec culbute, impact sur le dos, rebonds. Caméra latérale qui suit la chute.
- Généré par `python tools/make_chute_r6.py ENTREE.blend SORTIE.blend` (les rigs d'origine sont conservés, leurs contraintes sont mises en sourdine).
- La texture du personnage (`R61Tex.png`) est externe : si elle apparaît en rose, faire **File > External Data > Find Missing Files**.
- Aperçus : `apercu/R6_Chute_planche.png` (planche d'images clés) et `apercu/R6_Chute_image130.png`.
