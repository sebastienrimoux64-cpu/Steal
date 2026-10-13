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

## Salto arrière (backflip) du personnage R6
`models/R6_Salto_Arriere.blend` : 240 images à 60 i/s. Caméra de profil par défaut (`Camera_Profil`) et caméra trois-quarts (`Camera_TroisQuarts`), sol à damier (1 case = 1 u = 35 cm), soleil.
- **Physique simulée** (`tools/make_salto_arriere_r6.py`, `--sim` pour voir les diagnostics) : accroupissement équilibré, poussée avec soulevé des talons, **décollage détecté par la physique** (le sol ne peut plus pousser quand l'accélération du centre de masse atteint -g), **chute libre exactement parabolique** (g = 28 u/s² pour un personnage de 1,75 m), **moment cinétique conservé** (la rotation accélère en position groupée, de 390 à 570 °/s, puis ralentit à l'ouverture), réception amortie.
- Résultat : saut de 0,58 m, 0,71 s de vol, 338° de rotation avant le toucher, pieds sans glissement au contact, aucun morceau qui traverse le sol (vérifié sur la géométrie réelle des 240 images).
- Les jambes R6 sont coupées en deux (cuisse / mollet) pour fléchir les genoux. Les rigs d'origine restent dans le fichier mais sont cachés.
- Aperçus : `apercu/R6_Salto_Arriere.gif`, `apercu/R6_Salto_Arriere_planche.png`, `apercu/R6_Salto_physique.png` (hauteur du centre de masse vs parabole théorique, rotation, vitesse de rotation).

## Shidou Ryusei (Blue Lock) : « Ciseau retourné »
`models/Shidou_Ciseau_Retourne.blend` : 507 images à 60 i/s (8,4 s), caméra animée `Camera_Shidou` (+ `Camera_Profil` fixe), but avec filet, ballon, pelouse avec lignes, soleil bas et flash rouge à la frappe.
- **Scénario** : Shidou guette dans la surface, courbé comme un prédateur (tics de la tête et des mains) ; un centre en cloche arrive ; il s'élance et reprend le ballon en **ciseau retourné** (finition acrobatique, frappe type « Drive Shot ») ; le tir part dans la lucarne **en ralenti dramatique** ; il retombe sur le dos, **rit comme un fou** (le corps tremble), se relève et se fige bras écartés, tête renversée : l'extase du but.
- **Physique simulée** (`tools/make_shidou_r6.py`, option `--sim` pour les diagnostics) : décollage détecté par la physique, centre de masse parabolique (g = 28 u/s²), moment cinétique conservé (la rotation est recalculée à chaque instant), fouetté de jambe qui absorbe une grande partie du moment cinétique, rotation au décollage calculée pour que le pied rencontre le ballon à l'instant de la frappe. Le ballon suit aussi une balistique exacte (centre de 12 m, tir à 70 u/s ≈ 24 m/s résolu pour la lucarne, filet, rebonds).
- Les jambes R6 sont coupées au genou ; Shidou a des cheveux en pointes rouge sombre ajoutés sur la tête. Aucun morceau ne traverse le sol (vérifié sur la géométrie réelle des 507 images).
- Aperçus : `apercu/Shidou_Ciseau_Retourne.gif`, `apercu/Shidou_planche.png`, `apercu/Shidou_rendu_eevee.png`.

## Fruits du démon (One Piece) en cubes
`models/Fruits_du_Demon.blend` : **24 fruits du démon en voxels** (cubes de 18 cm), avec la **peau à spirales en relief** : chaque fruit porte plusieurs tourbillons (un grand face à la caméra), dessinés en cubes recolorés et surélevés d'un cran, plus une tige recourbée et une petite feuille. 6 formes (ronde, ovale, poire, gourde, aplatie, pomme, lobée) et une couleur par fruit. Les fruits sont posés sur des présentoirs en gradins avec leur nom en relief.
- Gomu Gomu, Mera Mera, Hie Hie, Pika Pika, Yami Yami, Magu Magu, Gura Gura, Ope Ope, Goro Goro, Suna Suna, Hana Hana, Bara Bara, Doku Doku, Mochi Mochi, Yomi Yomi, Kage Kage, Hobby Hobby, Neko Neko, Tori Tori, Zou Zou, Bomu Bomu, Horu Horu, Nikyu Nikyu, Hito Hito no Mi (Nika).
- Chaque fruit est un objet séparé (`Fruit_<nom>`, collection « Fruits ») : déplacez-le, copiez-le ou exportez-le. Couleurs en attribut de couleur « Col » (mode Vertex Paint, ou export glTF).
- Caméras : `Camera_Ensemble` (par défaut) et `Camera_GrosPlan`. Scène statique (pas d'animation).
- Régénérer : `python tools/make_fruits_demon.py SORTIE.blend [SORTIE.glb]`. Les couleurs sont inspirées de l'œuvre (elles varient selon l'anime et le manga).
- Aperçus : `apercu/Fruits_du_Demon_vue_ensemble.png`, `apercu/Fruits_du_Demon_gros_plans.png`.
