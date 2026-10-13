# Animations « idle » R6 — une par personnage

Chaque fichier est **votre rig R6IKFIX, inchangé** (mêmes objets, mêmes contraintes, mêmes parties du corps entières),
avec **une seule action** ajoutée sur l'armature de contrôle `Armature`. L'armature `__Rig` suit par ses contraintes,
comme d'habitude. Rien n'est coupé : seuls les os de contrôle bougent.

| Fichier | Personnage | Durée | Esprit |
|---|---|---|---|
| `Idle_Tanjiro.blend` | Tanjiro | 6 s | **Modeste** : posture droite, mains jointes devant, tête légèrement baissée, petite révérence polie, regard attentif sur le côté |
| `Idle_Nezuko.blend`  | Nezuko  | 4 s | **Timide** : épaules rentrées, bras serrés contre la poitrine, tête baissée et penchée, genoux qui se touchent, coups d'œil furtifs puis regard détourné, un pied qui se frotte |
| `Idle_Inosuke.blend` | Inosuke | 2 s | **Excité, sauvage** : rebond permanent, torse penché en avant façon bête, tête qui claque d'un côté à l'autre, bras écartés en griffes, coups de poing dans le vide, piétinements |
| `Idle_Muzan.blend`   | Muzan   | 8 s | **Froid, arrogant** : presque immobile, menton levé, épaules en arrière, une main devant à la taille, respiration très lente, regard qui balaie, puis inclinaison de tête menaçante |

Aperçus (vue 3/4 + vue de côté, couleurs de test seulement) : `previews/Idle_<Nom>.gif`.

## Détails techniques
- 60 images/seconde (comme votre fichier), image de début 0. Les animations **bouclent parfaitement** (dernière image = première).
- Os animés : `Torso`, `Head`, `LeftUpperArm`, `RightUpperArm`, `LeftLeg-IKTarget`, `RightLeg-IKTarget`.
  Les pieds restent posés grâce à l'IK (on ne déplace que les cibles). `MasterControl` n'est pas touché.
- Dans votre rig, `Head` copie la rotation de `MasterControl` : la tête garde donc son orientation quand le torse penche.
  Les rotations de tête sont réglées en tenant compte de ça.
- Action : `Idle_<Nom>` (sur `Armature`). Pour l'exporter vers Roblox, utilisez votre exporteur habituel comme pour une action normale.

## Ajouter un personnage
Tout est dans `tools/anim/r6_idles.py` : une fonction `pose(t)` par personnage (posture, rythme, tics), puis une ligne dans
le registre `CHARACTERS`. Ensuite :
```
python tools/anim/r6_idles.py tools/anim/source/R6IKFIX.blend animations           # tous
python tools/anim/r6_idles.py tools/anim/source/R6IKFIX.blend animations Tanjiro   # un seul
python tools/anim/preview.py animations/Idle_Tanjiro.blend animations/previews/Idle_Tanjiro.gif 10 260   # aperçu GIF
```
(nécessite le module Python `bpy` : `pip install bpy`.)
